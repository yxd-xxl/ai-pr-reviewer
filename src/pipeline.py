import src.env
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.context.pr_url import parse_pr_url
from src.context.github_client import GitHubClient
from src.context.conventions import load_conventions, fetch_file_content
from src.core.types import PullRequest, ReviewContext, ReviewResult, FileChange
from src.core.config import ReviewConfig, load_config
from src.analysis.mode import AnalysisMode
from src.analysis.composite import CompositeAnalyzer
from src.llm import create_adapter
from src.postprocess.filter import PostProcessor


def run_review(pr_url: str, token: str,
               config: ReviewConfig | None = None,
               llm_config: dict | None = None,
               categories: str = "all") -> tuple[PullRequest, list[FileChange], ReviewResult]:

    t0 = time.time()
    timing: dict[str, float] = {}

    if config is None:
        config = load_config()

    if llm_config:
        for key, env_key in [("provider", "LLM_PROVIDER"),
                             ("api_key", "LLM_API_KEY"),
                             ("base_url", "LLM_BASE_URL"),
                             ("model", "LLM_MODEL")]:
            if llm_config.get(key):
                os.environ[env_key] = llm_config[key]

    t1 = time.time()
    parsed = parse_pr_url(pr_url)
    client = GitHubClient(token=token)

    pr = None
    files = []
    conventions = []

    with ThreadPoolExecutor(max_workers=4) as pool:
        f_pr = pool.submit(client.fetch_pr, parsed.owner, parsed.repo, parsed.number)
        f_files = pool.submit(client.fetch_files, parsed.owner, parsed.repo, parsed.number)
        f_conv = pool.submit(load_conventions, token, parsed.owner, parsed.repo, "main")

        for f in as_completed([f_pr, f_files, f_conv]):
            try:
                if f == f_pr:      pr = f.result()
                elif f == f_files: files = f.result()
                else:              conventions = f.result()
            except Exception:
                pass

        # Stage 1b: fetch full file contents (after we have pr.head_sha)
        if files and pr:
            content_futures = {
                pool.submit(fetch_file_content, token, parsed.owner, parsed.repo,
                           fc.path, pr.head_sha): fc
                for fc in files if fc.status != "removed" and not fc.is_binary
            }
            for cf in as_completed(list(content_futures.keys())):
                fc = content_futures[cf]
                try:
                    fc.full_content = cf.result()
                except Exception:
                    pass

    if pr is None:
        raise RuntimeError("Failed to fetch PR metadata")
    timing["fetch"] = round(time.time() - t1, 2)

    t2 = time.time()
    ctx = ReviewContext(pr=pr, files=files, conventions=conventions)
    adapter = create_adapter()
    # Mode-based strategy
    if config.mode == "fast":
        categories = "security,bug" if categories == "all" else categories
    verify_all = config.mode == "deep"
    if config.permission == "review-only":
        config.auto_fix_categories = []  # disable fix generation
    analysis_mode = AnalysisMode.from_categories(categories, adapter, verify_all=verify_all,
                                                  fix_categories=config.auto_fix_categories)
    plan = analysis_mode.build_plan()
    analyzer = CompositeAnalyzer(plan) if len(plan) > 1 else plan[0]
    result = analyzer.analyze(ctx)
    timing["analyze"] = round(time.time() - t2, 2)

    t3 = time.time()
    max_f = {"fast": 5, "balanced": config.max_inline_comments, "deep": 20}.get(config.mode, config.max_inline_comments)
    pp = PostProcessor(
        min_confidence=config.min_confidence,
        max_findings=max_f,
    )
    result = pp.process(result)

    # Save to local DB
    try:
        from src.store.db import ReviewRepo
        from src.delivery.checklist import risk_score
        repo = f"{pr.owner}/{pr.repo}"
        llm_provider = (llm_config or {}).get("provider", os.getenv("LLM_PROVIDER", "mock"))
        llm_model = (llm_config or {}).get("model", os.getenv("LLM_MODEL", ""))
        ReviewRepo().save_review(
            pr.url, pr.title, repo, result.findings,
            risk_score=risk_score(result),
            mode=config.mode, categories=categories,
            llm_provider=llm_provider, llm_model=llm_model,
        )
    except Exception:
        pass

    timing["postprocess"] = round(time.time() - t3, 2)

    timing["total"] = round(time.time() - t0, 2)
    result.metadata["timing"] = timing

    return pr, files, result


def check_changes(owner: str, repo: str, token: str) -> dict:
    """Check for unreviewed commits. Returns dict with has_changes, head_sha, etc."""
    from src.context.change_detector import ChangeDetector
    from src.context.review_state import ReviewState
    from src.context.diff_parser import parse_unified_diff
    import urllib.request as _ur

    detector = ChangeDetector()
    should_review, head_sha, commit_count = detector.check(owner, repo, token)
    if not head_sha:
        return {"has_changes": False, "head_sha": "", "commit_count": 0, "diff_text": "", "files": [], "base_sha": ""}

    state = ReviewState()
    last_sha = state.last_reviewed_sha(0) or ""
    diff_text = ""
    try:
        if last_sha:
            u = f"https://api.github.com/repos/{owner}/{repo}/compare/{last_sha}...{head_sha}"
        else:
            u = f"https://api.github.com/repos/{owner}/{repo}/commits/{head_sha}"
        req = _ur.Request(u, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.diff", "User-Agent": "ai-pr-reviewer"})
        with _ur.urlopen(req, timeout=15) as resp:
            diff_text = resp.read().decode("utf-8", errors="replace")
    except Exception:
        diff_text = ""
    has_changes = should_review and bool(diff_text.strip())
    files = parse_unified_diff(diff_text) if diff_text.strip() else []
    return {"has_changes": has_changes, "head_sha": head_sha, "commit_count": commit_count, "diff_text": diff_text, "files": files, "base_sha": last_sha}


def generate_pr_proposal(owner: str, repo: str, token: str, diff_text: str, commit_count: int) -> dict:
    """Generate PR title/description from changes using LLM."""
    from src.llm import create_adapter
    adapter = create_adapter()
    diff_preview = diff_text[:4000] if len(diff_text) > 4000 else diff_text
    try:
        data = adapter.complete_json(
            system="You are a technical PR author. Output JSON with title and description.",
            user=f"Repo: {owner}/{repo}\nCommits: {commit_count}\nDiff:\n{diff_preview}\nGenerate PR title (conventional commits) and description. JSON: {{\"title\":\"...\",\"description\":\"...\"}}")
        return {"suggested_title": data.get("title", f"Auto PR: {commit_count} commits"), "suggested_description": data.get("description", "")}
    except Exception:
        return {"suggested_title": f"Auto PR: {commit_count} new commit(s)", "suggested_description": f"## Changes\n\n{commit_count} new commit(s)."}


def create_pr_from_changes(owner: str, repo: str, token: str, title: str, description: str, head_sha: str, base_branch: str = "main") -> dict:
    """Create a real GitHub PR from detected changes."""
    import json as _json
    import urllib.request as _ur
    branch_name = f"ai-auto-pr-{head_sha[:7]}"
    ref_data = _json.dumps({"ref": f"refs/heads/{branch_name}", "sha": head_sha}).encode()
    try:
        ref_req = _ur.Request(f"https://api.github.com/repos/{owner}/{repo}/git/refs", data=ref_data, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/vnd.github+json", "User-Agent": "ai-pr-reviewer"})
        with _ur.urlopen(ref_req, timeout=15) as resp: resp.read()
    except Exception:
        pass
    pr_data = _json.dumps({"title": title, "body": description, "head": branch_name, "base": base_branch}).encode()
    try:
        pr_req = _ur.Request(f"https://api.github.com/repos/{owner}/{repo}/pulls", data=pr_data, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/vnd.github+json", "User-Agent": "ai-pr-reviewer"})
        with _ur.urlopen(pr_req, timeout=15) as resp:
            result = _json.loads(resp.read())
        from src.context.review_state import ReviewState
        ReviewState().mark_reviewed(0, head_sha, 0)
        return {"url": result.get("html_url", ""), "number": result.get("number", 0), "branch": branch_name}
    except Exception as e:
        return {"url": "", "number": 0, "error": str(e)}
