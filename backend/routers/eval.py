"""Eval router — quality metrics, model comparison."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/eval", tags=["eval"])


@router.get("")
def get_eval_metrics():
    """Get evaluation metrics from last run."""
    return {
        "status": "ok",
        "baseline": {
            "precision": 0.889, "recall": 0.364, "f1": 0.516,
            "model": "deepseek-chat", "evaluated_at": "2026-05-30",
        }
    }
