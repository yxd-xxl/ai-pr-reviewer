"""Review router — submit, query, history (RBAC-enforced)."""

import os
import time
from fastapi import APIRouter, Depends, HTTPException, Query
from backend.dependencies import get_token, get_current_user
from backend.middleware import require_permission
from backend.models import ReviewRequest, ReviewResponse, FeedbackRequest

router = APIRouter(prefix="/api/v1", tags=["review"])


@router.post("/review", response_model=ReviewResponse)
def create_review(req: ReviewRequest, token: str = Depends(get_token),
                  _user=Depends(require_permission("create_review"))):
    """Submit a PR for AI review."""
    from src.pipeline import run_review
    from src.delivery.checklist import risk_score as calc_risk

    try:
        t0 = time.time()
        pr, files, result = run_review(req.pr_url, token, categories=req.categories)

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
