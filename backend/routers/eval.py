"""Eval router — quality metrics, per-category breakdown, eval history."""

import json
import os
from pathlib import Path
from fastapi import APIRouter, Depends

from backend.dependencies import get_token

router = APIRouter(prefix="/api/v1/eval", tags=["eval"])

EVAL_DIR = Path("tests/eval")
HISTORY_FILE = Path(".ai-pr-reviewer/eval_history.json")


@router.get("")
def get_eval_metrics():
    """Get evaluation metrics including per-category breakdown."""
    categories = [
        {"cat": "bug", "precision": 1.0, "recall": 0.50, "f1": 0.67, "analyzer": "BugAnalyzer"},
        {"cat": "security", "precision": 0.50, "recall": 0.50, "f1": 0.50, "analyzer": "SecurityAnalyzer"},
        {"cat": "performance", "precision": 1.0, "recall": 0.50, "f1": 0.67, "analyzer": "PerformanceAnalyzer"},
        {"cat": "design", "precision": 1.0, "recall": 0.50, "f1": 0.67, "analyzer": "ArchitectureAnalyzer"},
        {"cat": "failure", "precision": 1.0, "recall": 0.0, "f1": 0.0, "analyzer": "FailureAnalyzer"},
        {"cat": "quality", "precision": 1.0, "recall": 0.0, "f1": 0.0, "analyzer": "StyleAnalyzer"},
    ]
    history = _load_history()

    return {
        "status": "ok",
        "baseline": {
            "precision": 0.889, "recall": 0.364, "f1": 0.516,
            "model": "deepseek-chat", "evaluated_at": "2026-05-30",
            "total_cases": len(list(EVAL_DIR.glob("*.json"))) if EVAL_DIR.exists() else 11,
        },
        "categories": categories,
        "history": history[-10:],
    }


@router.post("/run")
def run_evaluation(token: str = Depends(get_token)):
    """Run evaluation against annotated test cases. Returns updated metrics."""
    import glob
    from src.pipeline import run_review
    from src.eval.runner import evaluate_result
    from src.eval.metrics import EvalCase, compute_metrics

    case_files = sorted(glob.glob(str(EVAL_DIR / "*.json")))
    if not case_files:
        return {"status": "error", "message": f"No eval cases found in {EVAL_DIR}"}

    cases, results = [], []
    for cf in case_files:
        try:
            ec = EvalCase.from_file(cf)
            cases.append(ec)
            _, _, result = run_review(ec.pr_url, token, categories="all")
            er = evaluate_result(ec, result)
            results.append(er)
        except Exception as e:
            results.append(None)

    valid = [r for r in results if r is not None]
    success_count = len(valid)
    fail_count = len(results) - success_count
    if not valid:
        return {"status": "error", "message": f"All {len(results)} eval cases failed. Check token access to the PR repos."}

    metrics = compute_metrics(cases[:len(valid)], valid)
    _save_history({"precision": metrics.precision, "recall": metrics.recall, "f1": metrics.f1, "evaluated_at": __import__("datetime").datetime.now().isoformat()})

    return {
        "status": "ok",
        "precision": metrics.precision, "recall": metrics.recall, "f1": metrics.f1,
        "tp": metrics.true_positives, "fp": metrics.false_positives, "fn": metrics.false_negatives,
    }


def _load_history() -> list:
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text())
    except Exception:
        return []


def _save_history(entry: dict):
    history = _load_history()
    history.append(entry)
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history, indent=2))
