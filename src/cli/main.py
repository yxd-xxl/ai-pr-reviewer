import os
import sys
import click

from src.context.pr_url import parse_pr_url
from src.context.github_client import GitHubClient
from src.context.review_state import ReviewState
from src.core.config import DEFAULT_CONFIG
from src.pipeline import run_review
from src.eval.metrics import EvalCase, compute_metrics, per_category_summary
from src.eval.runner import evaluate_result
from src.delivery.markdown import render_markdown
from src.delivery.github_delivery import GitHubDelivery
import yaml


@click.group()
def cli():
    """AI PR Reviewer — AI-driven GitHub PR code review tool"""
    pass


@cli.command()
@click.option("-f", "--force", is_flag=True, help="Overwrite existing config")
def init(force: bool):
    """Generate default .ai-pr-reviewer.yml config file"""
    path = ".ai-pr-reviewer.yml"
    if os.path.exists(path) and not force:
        click.echo(f"{path} already exists. Use --force to overwrite.")
        return

    config_yaml = yaml.dump({
        "review": {
            "min_confidence": DEFAULT_CONFIG.min_confidence,
            "max_inline_comments": DEFAULT_CONFIG.max_inline_comments,
            "categories": DEFAULT_CONFIG.categories,
        },
        "conventions": DEFAULT_CONFIG.conventions,
        "delivery": {
            "mode": DEFAULT_CONFIG.delivery.mode,
            "inline_comments": DEFAULT_CONFIG.delivery.inline_comments,
            "summary_comment": DEFAULT_CONFIG.delivery.summary_comment,
        },
    }, default_flow_style=False, sort_keys=False)

    with open(path, "w", encoding="utf-8") as f:
        f.write(config_yaml)
    click.echo(f"Created {path}")


@cli.command()
@click.argument("pr_url")
def inspect(pr_url: str):
    """Get PR metadata"""
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        click.echo("Error: GITHUB_TOKEN not set", err=True)
        sys.exit(1)

    parsed = parse_pr_url(pr_url)
    client = GitHubClient(token=token)
    pr = client.fetch_pr(parsed.owner, parsed.repo, parsed.number)

    click.echo(f"owner:       {pr.owner}")
    click.echo(f"repo:        {pr.repo}")
    click.echo(f"number:      {pr.number}")
    click.echo(f"title:       {pr.title}")
    click.echo(f"author:      {pr.author}")
    click.echo(f"base_branch: {pr.base_branch}")
    click.echo(f"head_branch: {pr.head_branch}")
    click.echo(f"base_sha:    {pr.base_sha}")
    click.echo(f"head_sha:    {pr.head_sha}")


@cli.command()
@click.argument("pr_url")
@click.option("-o", "--output", default=None, help="Output file (for markdown delivery)")
@click.option("--delivery", "delivery_mode", default="markdown",
              type=click.Choice(["markdown", "github"]),
              help="Delivery mode (default: markdown)")
@click.option("--publish", is_flag=True, default=False,
              help="Actually post comments to GitHub (requires --yes)")
@click.option("--yes", "confirm", is_flag=True, default=False,
              help="Confirm publish action")
@click.option("--categories", default="all", help="Analysis categories: all, security, bug, performance, style (comma-separated)")
@click.option("--force", "force_review", is_flag=True, default=False,
              help="Re-review even if already reviewed")
def review(pr_url: str, output: str | None, delivery_mode: str, categories: str,
           publish: bool, confirm: bool, force_review: bool):
    """Review a GitHub PR"""
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        click.echo("Error: GITHUB_TOKEN not set", err=True)
        sys.exit(1)

    if delivery_mode == "github" and publish and not confirm:
        click.echo("Error: --publish requires --yes for confirmation", err=True)
        sys.exit(1)

    parsed = parse_pr_url(pr_url)

    # Check if already reviewed (incremental)
    state = ReviewState()
    # Quick fetch just for head_sha
    temp_client = GitHubClient(token=token)
    temp_pr = temp_client.fetch_pr(parsed.owner, parsed.repo, parsed.number)
    if not force_review and state.is_reviewed(parsed.number, temp_pr.head_sha):
        click.echo(f"  PR #{parsed.number}@{temp_pr.head_sha[:7]} already reviewed. Use --force to re-review.")
        return

    click.echo(f"Fetching PR: {pr_url} ...")
    try:
        pr, files, result = run_review(pr_url, token, categories=categories)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    state.mark_reviewed(pr.number, pr.head_sha, len(result.findings))
    click.echo(f"  {pr.title} ({len(files)} files changed)")
    timing = result.metadata.get("timing", {})
    click.echo(f"  {len(result.findings)} finding(s)  "
               f'(fetch={timing.get("fetch","?")}s '
               f'analyze={timing.get("analyze","?")}s '
               f'total={timing.get("total","?")}s)')

    if delivery_mode == "github":
        dry_run = not publish
        delivery = GitHubDelivery(token=token, dry_run=dry_run)
        actions = delivery.deliver(result, pr)
        click.echo(f"  Delivery mode: {'DRY-RUN' if dry_run else 'PUBLISH'}")
        for a in actions:
            click.echo(f"    {a}")
    else:
        md = render_markdown(result)
        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(md)
            click.echo(f"Report saved to {output}")
        else:
            click.echo(md)


@cli.command()
@click.argument("eval_dir", default="tests/eval")
def evaluate(eval_dir: str):
    """Run evaluation against annotated test cases"""
    import glob

    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        click.echo("Error: GITHUB_TOKEN not set", err=True)
        sys.exit(1)

    case_files = sorted(glob.glob(f"{eval_dir}/*.json"))
    if not case_files:
        click.echo(f"No eval cases found in {eval_dir}")
        return

    cases: list[EvalCase] = []
    results = []

    for cf in case_files:
        ec = EvalCase.from_file(cf)
        cases.append(ec)
        click.echo(f"\nEvaluating: {ec.pr_url}")

        try:
            _, _, result = run_review(ec.pr_url, token)
            er = evaluate_result(ec, result)
            results.append(er)
            click.echo(f"  Found: {len(result.findings)} findings")
            click.echo(f"  Matched: {len(er.matched_expected)} expected")
            if er.false_positives:
                click.echo(f"  False positives: {er.false_positives}")
            if er.false_negatives:
                click.echo(f"  False negatives: {er.false_negatives}")
        except Exception as e:
            click.echo(f"  Error: {e}")

    metrics = compute_metrics(cases, results)
    click.echo(f"\n{'='*50}")
    click.echo(metrics.summary())
    click.echo()
    click.echo(per_category_summary(cases, results))


if __name__ == "__main__":
    cli()
