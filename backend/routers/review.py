"""Review router — submit, query, history (RBAC-enforced)."""

import os
import time
from fastapi import APIRouter, Depends, HTTPException, Query
from backend.dependencies import get_token, get_current_user, get_github_token
from backend.middleware import require_permission
from backend.models import ReviewRequest, ReviewResponse, FeedbackRequest

router = APIRouter(prefix="/api/v1", tags=["review"])


@router.post("/review", response_model=ReviewResponse)
def create_review(req: ReviewRequest, token: str = Depends(get_github_token),
                  _user=Depends(require_permission("create_review"))):
    """Submit a PR for AI review."""
    from src.pipeline import run_review
    from src.delivery.checklist import risk_score as calc_risk

    try:
        t0 = time.time()
        provider = req.llm_provider or os.getenv("LLM_PROVIDER", "mock")
        llm_cfg = {
            "provider": provider,
            "api_key": req.llm_api_key or os.getenv("LLM_API_KEY", ""),
            "base_url": os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
            "model": req.llm_model or os.getenv("LLM_MODEL", "deepseek-chat"),
        }
        from src.core.config import ReviewConfig
        config = ReviewConfig(
            mode=req.mode or "balanced",
            min_confidence=req.min_confidence if req.min_confidence > 0 else 0.65,
            max_inline_comments=req.max_inline_comments if req.max_inline_comments > 0 else 10,
        )
        pr, files, result = run_review(req.pr_url, token, config=config,
                                       llm_config=llm_cfg, categories=req.categories)

        score = calc_risk(result)
        if score < 15: level = "low"
        elif score < 40: level = "medium"
        elif score < 70: level = "high"
        else: level = "critical"

        return ReviewResponse(
            status="ok",
            pr={"title": pr.title, "url": pr.url, "author": pr.author, "number": pr.number},
            files_count=len(files),
            findings=[
                {
                    "severity": f.severity, "category": f.category,
                    "title": f.title, "description": f.description,
                    "suggestion": f.suggestion, "confidence": f.confidence,
                    "location": {"file": f.location.file, "line": f.location.line},
                    "evidence": f.evidence, "fix_patch": f.fix_patch,
                    "fix_verified": f.fix_verified, "analyzer": f.analyzer,
                    "lifecycle_state": f.lifecycle_state,
                }
                for f in result.findings
            ],
            summary=result.summary,
            warnings=result.warnings,
            risk_score=score,
            risk_level=level,
            timing=result.metadata.get("timing", {}),
        )
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/feedback")
def submit_feedback(req: FeedbackRequest):
    """Submit user feedback on a finding."""
    from src.feedback.tracker import FeedbackTracker, FeedbackState
    tracker = FeedbackTracker()
    try:
        state = FeedbackState(req.state)
    except ValueError:
        raise HTTPException(400, f"Invalid state: {req.state}")
    tracker._data.setdefault("entries", {})
    tracker._data["entries"][req.fingerprint] = {
        "state": state.value, "reason": req.reason,
        "marked_by": "api", "title": "", "file": "", "category": "",
        "count": tracker._data["entries"].get(req.fingerprint, {}).get("count", 0) + 1,
    }
    tracker._save()
    return {"status": "ok", "fingerprint": req.fingerprint, "state": state.value}


@router.get("/reviews")
def list_reviews(repo: str = "", limit: int = Query(20, ge=1, le=100)):
    """List review history."""
    from src.store.db import ReviewRepo
    db = ReviewRepo()
    try:
        rows = db.get_history(repo=repo, limit=limit)
        return {"status": "ok", "reviews": rows}
    finally:
        db.close()


@router.get("/review/{review_id}")
def get_review(review_id: int):
    """Get a specific review by ID."""
    from src.store.db import ReviewRepo
    db = ReviewRepo()
    try:
        findings = db.get_findings(review_id)
        return {"status": "ok", "review_id": review_id, "findings": findings}
    finally:
        db.close()


@router.post("/check-changes")
def check_changes_endpoint(owner: str, repo: str, token: str = Depends(get_github_token)):
    """Check for unreviewed commits in a repository."""
    from src.pipeline import check_changes
    result = check_changes(owner, repo, token)
    return {"status": "ok", **result}


@router.post("/generate-proposal")
def generate_proposal(owner: str, repo: str, token: str = Depends(get_github_token)):
    """Generate a PR title and description from unreviewed changes."""
    from src.pipeline import check_changes, generate_pr_proposal
    changes = check_changes(owner, repo, token)
    if not changes.get("has_changes"):
        return {"status": "ok", "has_changes": False, "proposal": None}
    proposal = generate_pr_proposal(owner, repo, token, changes["diff_text"], changes["commit_count"])
    return {"status": "ok", "has_changes": True, "proposal": proposal, "changes": changes}


@router.post("/create-pr")
def create_pr_endpoint(owner: str, repo: str, title: str, description: str = "",
                       token: str = Depends(get_github_token)):
    """Create a PR from detected changes."""
    from src.pipeline import check_changes, create_pr_from_changes
    changes = check_changes(owner, repo, token)
    if not changes.get("has_changes"):
        return {"status": "error", "message": "No unreviewed changes"}
    result = create_pr_from_changes(owner, repo, token, title, description, changes["head_sha"])
    return {"status": "ok" if result.get("url") else "error", **result}


@router.post("/post-comments")
def post_comments(pr_url: str, token: str = Depends(get_github_token),
                  dry_run: bool = True):
    """Post review findings as inline comments on a PR."""
    from src.pipeline import run_review
    from src.delivery.github_delivery import GitHubDelivery

    try:
        pr, files, result = run_review(pr_url, token)
        delivery = GitHubDelivery(token=token, dry_run=dry_run)
        actions = delivery.deliver(result, pr)
        return {"status": "ok", "actions": actions, "findings_count": len(result.findings),
                "mode": "dry_run" if dry_run else "published"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/batch-review")
def batch_review(pr_urls: list[str], categories: str = "all", mode: str = "balanced",
                 llm_provider: str = "", llm_api_key: str = "", llm_model: str = "",
                 token: str = Depends(get_github_token)):
    """Run analysis on multiple PRs and return aggregate results."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from src.pipeline import run_review
    from src.core.config import ReviewConfig

    provider = llm_provider or os.getenv("LLM_PROVIDER", "mock")
    llm_cfg = {"provider": provider, "api_key": llm_api_key or os.getenv("LLM_API_KEY", ""),
               "base_url": os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
               "model": llm_model or os.getenv("LLM_MODEL", "deepseek-chat")}
    config = ReviewConfig(mode=mode or "balanced")

    results = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(run_review, url, token, config=config, llm_config=llm_cfg, categories=categories): url for url in pr_urls}
        for fut in as_completed(futures):
            url = futures[fut]
            try:
                pr, files, result = fut.result()
                results.append({
                    "url": url, "status": "ok",
                    "title": pr.title, "findings": len(result.findings),
                    "risk_score": sum(
                        {"critical": 60, "high": 30, "medium": 12, "low": 3}.get(f.severity, 1)
                        for f in result.findings
                    ),
                })
            except Exception as e:
                results.append({"url": url, "status": "error", "message": str(e)})
    return {"status": "ok", "results": results}
