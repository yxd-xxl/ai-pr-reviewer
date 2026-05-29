import os
import sys
import click

from src.context.pr_url import parse_pr_url
from src.context.github_client import GitHubClient
from src.context.review_state import ReviewState
from src.context.change_detector import ChangeDetector
from src.core.config import DEFAULT_CONFIG
from src.pipeline import run_review
from src.eval.metrics import EvalCase, compute_metrics, per_category_summary
from src.eval.runner import evaluate_result
from src.delivery.markdown import render_markdown
from src.delivery.github_delivery import GitHubDelivery
from src.delivery.pr_generator import generate_fix_pr
from src.store.db import ReviewRepo
from src.context.user_profile import get_user_profile, list_user_repos
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

@cli.command()
@click.argument("owner_repo")
def auto(owner_repo: str):
    """Auto-detect changes and review if threshold met"""
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        click.echo("Error: GITHUB_TOKEN not set", err=True)
        sys.exit(1)

    parts = owner_repo.split("/")
    if len(parts) != 2:
        click.echo("Error: use format owner/repo", err=True)
        sys.exit(1)

    detector = ChangeDetector()
    should, sha, commits = detector.check(parts[0], parts[1], token)
    click.echo(f"Repository: {owner_repo}")
    click.echo(f"HEAD: {sha[:7] if sha else 'unknown'}")
    click.echo(f"Commits since last review: {commits}")

    if should:
        click.echo("Threshold met — triggering review.")
        # Find open PRs and review them
        from src.context.github_client import GitHubClient
        client = GitHubClient(token=token)
        # For MVP, review the first open PR
        try:
            import urllib.request, json
            url = f"https://api.github.com/repos/{parts[0]}/{parts[1]}/pulls?state=open&per_page=3"
            req = urllib.request.Request(url, headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "ai-pr-reviewer",
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                prs = json.loads(resp.read())
            if prs:
                pr_url = prs[0]["html_url"]
                click.echo(f"Reviewing: {pr_url}")
                pr, files, result = run_review(pr_url, token)
                click.echo(f"  {len(result.findings)} finding(s)")
            else:
                click.echo("No open PRs found.")
        except Exception as e:
            click.echo(f"Failed to fetch PRs: {e}")
    else:
        click.echo(f"Below threshold ({commits} commits, need {3}+). Skipping.")

@cli.command()
@click.argument("pr_url")
@click.option("--findings", default=None, help="Comma-separated finding indices to fix")
@click.option("--publish", is_flag=True, default=False, help="Actually create the fix PR")
def fix(pr_url: str, findings: str | None, publish: bool):
    """Generate a fix PR from reviewed findings"""
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        click.echo("Error: GITHUB_TOKEN not set", err=True)
        sys.exit(1)

    indices = None
    if findings:
        indices = [int(x.strip()) for x in findings.split(",")]

    click.echo(f"Reviewing: {pr_url} ...")
    pr, files, result = run_review(pr_url, token)
    click.echo(f"  {len(result.findings)} finding(s), "
               f"{sum(1 for f in result.findings if f.fix_patch)} with fix patch")

    actions = generate_fix_pr(result, pr, token, finding_indices=indices, dry_run=not publish)
    mode = "DRY-RUN" if not publish else "PUBLISH"
    click.echo(f"  Mode: {mode}")
    for a in actions:
        click.echo(f"    {a}")

@cli.command()
@click.argument("pr_url")
@click.option("--finding", type=int, required=True, help="Finding index to ask about")
@click.option("--question", required=True, help="Question to ask")
def ask(pr_url: str, finding: int, question: str):
    """Ask a follow-up question about a finding"""
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        click.echo("Error: GITHUB_TOKEN not set", err=True)
        sys.exit(1)

    click.echo(f"Reviewing: {pr_url} ...")
    pr, files, result = run_review(pr_url, token)

    if finding < 1 or finding > len(result.findings):
        click.echo(f"Error: finding {finding} out of range (1-{len(result.findings)})", err=True)
        sys.exit(1)

    f = result.findings[finding - 1]
    ctx = __import__('src.core.types', fromlist=['ReviewContext']).ReviewContext(pr=pr, files=files)

    from src.llm import create_adapter
    adapter = create_adapter()
    from src.analysis.llm_analyzer import LLMAnalyzer
    analyzer = LLMAnalyzer(adapter)

    click.echo(f"Asking about: {f.title}")
    click.echo(f"Question: {question}")
    click.echo()

    resp = analyzer.followup(f, question, ctx)
    click.echo(f"Answer: {resp.get('answer', 'No answer')}")
    if resp.get('alternative_fixes'):
        click.echo("Alternatives:")
        for alt in resp['alternative_fixes']:
            click.echo(f"  - {alt}")

@cli.command()
@click.option("--repo", default="", help="Filter by repo (e.g. owner/repo)")
@click.option("--limit", default=20, help="Number of entries")
def history(repo: str, limit: int):
    """Show review history"""
    db = ReviewRepo()
    rows = db.get_history(repo=repo, limit=limit)
    if not rows:
        click.echo("No review history yet.")
        return
    click.echo(f"{'ID':<5} {'Date':<20} {'Repo':<25} {'PR':<40} {'F':>3} {'Risk':>4}")
    click.echo("-" * 100)
    for r in rows:
        click.echo(f"{r['id']:<5} {r['created_at'][:19]:<20} {r['repo']:<25} {r['pr_title'][:38]:<40} {r['findings_count']:>3} {r['risk_score']:>4}")
    db.close()

@cli.command()
@click.option("--repo", default="", help="Filter by repo")
@click.option("--days", default=30, help="Days to look back")
def trends(repo: str, days: int):
    """Show review quality trends"""
    db = ReviewRepo()
    rows = db.get_history(repo=repo, limit=100)
    if not rows:
        click.echo("No data.")
        return

    total = len(rows)
    total_findings = sum(r["findings_count"] for r in rows)
    avg_risk = sum(r["risk_score"] for r in rows) / total if total else 0

    click.echo(f"Reviews: {total}")
    click.echo(f"Total findings: {total_findings}")
    click.echo(f"Avg risk score: {avg_risk:.0f}/100")
    click.echo(f"Avg findings/review: {total_findings/total:.1f}" if total else "")
    db.close()

@cli.command()
def profile():
    """Show GitHub user profile"""
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        click.echo("Error: GITHUB_TOKEN not set", err=True)
        sys.exit(1)
    user = get_user_profile(token)
    if user:
        click.echo(f"Login: {user.get('login')}")
        click.echo(f"Name:  {user.get('name', 'N/A')}")
        click.echo(f"Email: {user.get('email', 'N/A')}")
        click.echo(f"Repos: {user.get('public_repos', 0)} public, {user.get('total_private_repos', 0)} private")

@cli.command()
@click.option("--limit", default=10, help="Number of repos to show")
def repos(limit: int):
    """List accessible GitHub repos"""
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        click.echo("Error: GITHUB_TOKEN not set", err=True)
        sys.exit(1)
    repos_list = list_user_repos(token, per_page=limit)
    if not repos_list:
        click.echo("No repos found.")
        return
    for r in repos_list:
        priv = "private" if r.get("private") else "public"
        click.echo(f"  {r['full_name']:<35} {priv:<8} {r.get('language', ''):<10} {r.get('open_issues_count', 0)} issues")


if __name__ == "__main__":
    cli()
