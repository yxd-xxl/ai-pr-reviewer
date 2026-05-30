"""AI PR Reviewer — FastAPI REST API server."""

import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="AI PR Reviewer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)


class ReviewRequest(BaseModel):
    pr_url: str
    categories: str = "all"
    mode: str = "balanced"


class FeedbackRequest(BaseModel):
    fingerprint: str
    state: str
    reason: str = ""


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.post("/api/v1/review")
def create_review(req: ReviewRequest):
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        raise HTTPException(400, "GITHUB_TOKEN not set")

    from src.pipeline import run_review
    try:
        pr, files, result = run_review(req.pr_url, token, categories=req.categories)
        return {
            "status": "ok",
            "pr": {"title": pr.title, "url": pr.url, "author": pr.author},
            "files_count": len(files),
            "findings": [
                {
                    "severity": f.severity, "category": f.category,
                    "title": f.title, "description": f.description,
                    "suggestion": f.suggestion, "confidence": f.confidence,
                    "location": {"file": f.location.file, "line": f.location.line},
                    "evidence": f.evidence, "fix_patch": f.fix_patch,
                    "analyzer": f.analyzer,
                }
                for f in result.findings
            ],
            "warnings": result.warnings,
            "timing": result.metadata.get("timing", {}),
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/v1/feedback")
def submit_feedback(req: FeedbackRequest):
    from src.feedback.tracker import FeedbackTracker
    tracker = FeedbackTracker()
    # For API, we use fingerprint directly
    try:
        # Record feedback event
        tracker._data.setdefault("entries", {})
        tracker._data["entries"][req.fingerprint] = {
            "state": req.state,
            "reason": req.reason,
            "marked_by": "api",
            "count": tracker._data["entries"].get(req.fingerprint, {}).get("count", 0) + 1,
        }
        tracker._save()
        return {"status": "ok", "fingerprint": req.fingerprint, "state": req.state}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/v1/reviews")
def list_reviews(repo: str = "", limit: int = Query(20, ge=1, le=100)):
    from src.store.db import ReviewRepo
    db = ReviewRepo()
    try:
        rows = db.get_history(repo=repo, limit=limit)
        return {"status": "ok", "reviews": rows}
    finally:
        db.close()


@app.get("/api/v1/eval")
def get_eval_metrics():
    return {
        "status": "ok",
        "baseline": {"precision": 0.889, "recall": 0.364, "f1": 0.516},
        "evaluated_at": "2026-05-30",
        "model": "deepseek-chat",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
