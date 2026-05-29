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
    timing["postprocess"] = round(time.time() - t3, 2)

    timing["total"] = round(time.time() - t0, 2)
    result.metadata["timing"] = timing

    return pr, files, result
