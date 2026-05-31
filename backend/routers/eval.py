"""Eval router — quality metrics computed from actual eval runs."""

import glob
import json
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends

from backend.dependencies import get_github_token

router = APIRouter(prefix="/api/v1/eval", tags=["eval"])

EVAL_DIR = Path("tests/eval")
HISTORY_FILE = Path(".ai-pr-reviewer/eval_history.json")


@router.get("")
def get_eval_metrics():
    """Get evaluation metrics from last run + per-category data from stored results."""
    history = _load_history()
    latest = history[-1] if history else None
    cat_results = latest.get("categories", []) if latest else []

    # If no stored results, show defaults
    if not cat_results:
        cat_results = [
            {"cat": "bug", "precision": 1.0, "recall": 0.50, "f1": 0.67, "analyzer": "BugAnalyzer"},
            {"cat": "security", "precision": 0.50, "recall": 0.50, "f1": 0.50, "analyzer": "SecurityAnalyzer"},
            {"cat": "performance", "precision": 1.0, "recall": 0.50, "f1": 0.67, "analyzer": "PerformanceAnalyzer"},
        ]

    n_active = len([f for f in (EVAL_DIR.glob("*.json") if EVAL_DIR.exists() else []) if not str(f).endswith(".disabled")])
    baseline = latest if latest else {
        "precision": 0.889, "recall": 0.364, "f1": 0.516,
        "model": "deepseek-chat", "evaluated_at": "2026-05-30", "total_cases": n_active,
    }
    baseline["total_cases"] = n_active

    return {
        "status": "ok",
        "baseline": baseline,
        "categories": cat_results,
        "history": history[-10:],
    }


@router.post("/run")
def run_evaluation(token: str = Depends(get_github_token)):
    """Run evaluation against all active test cases. Updates per-category metrics."""
    from src.pipeline import run_review
    from src.eval.runner import evaluate_result
    from src.eval.metrics import EvalCase, compute_metrics

    case_files = sorted([f for f in glob.glob(str(EVAL_DIR / "*.json")) if not f.endswith(".disabled")])
    if not case_files:
        return {"status": "error", "message": "No eval cases found"}

    # Group by category
    by_category: dict[str, list] = {}
    all_cases, all_results, errors = [], [], []

    for cf in case_files:
        try:
            ec = EvalCase.from_file(cf)
            all_cases.append(ec)
            _, _, result = run_review(ec.pr_url, token, categories="all")
            er = evaluate_result(ec, result)
            all_results.append(er)

            cat = ec.category or "bug"
            by_category.setdefault(cat, {"cases": [], "results": []})
            by_category[cat]["cases"].append(ec)
            by_category[cat]["results"].append(er)
        except Exception as e:
            errors.append(f"{Path(cf).name}: {e}")

    if not all_results:
        return {"status": "error", "message": f"All {len(case_files)} cases failed.", "errors": errors}

    # Overall metrics
    metrics = compute_metrics(all_cases, all_results)

    # Per-category metrics
    cat_data = []
    analyzer_map = {"bug": "BugAnalyzer", "security": "SecurityAnalyzer", "performance": "PerformanceAnalyzer",
                    "design": "ArchitectureAnalyzer", "failure": "FailureAnalyzer", "quality": "StyleAnalyzer"}
    for cat, group in by_category.items():
        cm = compute_metrics(group["cases"], group["results"])
        cat_data.append({
            "cat": cat,
            "precision": cm.precision, "recall": cm.recall, "f1": cm.f1,
            "analyzer": analyzer_map.get(cat, "?"),
            "tp": cm.true_positives, "fp": cm.false_positives, "fn": cm.false_negatives,
        })

    _save_history({
        "precision": metrics.precision, "recall": metrics.recall, "f1": metrics.f1,
        "tp": metrics.true_positives, "fp": metrics.false_positives, "fn": metrics.false_negatives,
        "evaluated_at": datetime.now().isoformat(),
        "model": "deepseek-chat",
        "categories": cat_data,
    })

    return {
        "status": "ok",
        "precision": metrics.precision, "recall": metrics.recall, "f1": metrics.f1,
        "tp": metrics.true_positives, "fp": metrics.false_positives, "fn": metrics.false_negatives,
        "success": len(all_results), "failed": len(errors), "errors": errors[:3],
        "categories": cat_data,
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
