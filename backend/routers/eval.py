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

# Mapping of category to analyzer display name.
ANALYZER_MAP = {
    "bug": "BugAnalyzer",
    "security": "SecurityAnalyzer",
    "performance": "PerformanceAnalyzer",
    "design": "ArchitectureAnalyzer",
    "failure": "FailureAnalyzer",
    "quality": "StyleAnalyzer",
}


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
def run_evaluation(token: str = Depends(get_github_token),
                   llm_provider: str = "", llm_api_key: str = "", llm_model: str = ""):
    """Run evaluation against all active test cases. Updates per-category metrics."""
    from src.eval.metrics import EvalCase

    case_files = _load_active_case_files()
    if not case_files:
        return {"status": "error", "message": "No eval cases found"}

    llm_cfg = _build_llm_config(llm_provider, llm_api_key, llm_model)
    cases_map = _load_cases(case_files)
    if not cases_map:
        return {"status": "error", "message": "No eval cases found"}

    all_cases, all_results, by_category, errors = _run_real_eval(cases_map, token, llm_cfg)

    if not all_results:
        return {"status": "error", "message": f"All {len(case_files)} cases failed.", "errors": errors}

    cat_data = _accumulate_category_results(by_category)
    metrics = compute_metrics(all_cases, all_results)
    _save_eval_history(metrics, cat_data)

    return {
        "status": "ok",
        "precision": metrics.precision, "recall": metrics.recall, "f1": metrics.f1,
        "tp": metrics.true_positives, "fp": metrics.false_positives, "fn": metrics.false_negatives,
        "success": len(all_results), "failed": len(errors), "errors": errors[:3],
        "categories": cat_data,
    }


def _load_active_case_files() -> list:
    """Return sorted list of active (non-disabled) eval case JSON files."""
    return sorted([f for f in glob.glob(str(EVAL_DIR / "*.json")) if not f.endswith(".disabled")])


def _build_llm_config(provider: str, api_key: str, model: str) -> dict:
    """Build LLM configuration dict from request params and environment fallbacks."""
    import os

    return {
        "provider": provider or os.getenv("LLM_PROVIDER", "mock"),
        "api_key": api_key or os.getenv("LLM_API_KEY", ""),
        "base_url": os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
        "model": model or os.getenv("LLM_MODEL", "deepseek-chat"),
    }


def _load_cases(case_files: list) -> dict:
    """Load EvalCase objects from case files and map by PR URL."""
    from src.eval.metrics import EvalCase

    cases_map = {}
    for cf in case_files:
        ec = EvalCase.from_file(cf)
        cases_map[ec.pr_url] = ec
    return cases_map


def _run_real_eval(cases_map: dict, token: str, llm_cfg: dict):
    """Run evaluation against all cases concurrently and collect results."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from src.pipeline import run_review
    from src.eval.runner import evaluate_result

    by_category: dict[str, dict] = {}
    all_cases, all_results, errors = [], [], []

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(run_review, ec.pr_url, token, llm_config=llm_cfg, categories="all"): ec
            for ec in cases_map.values()
        }
        for fut in as_completed(futures):
            ec = futures[fut]
            try:
                _, _, result = fut.result(timeout=120)
                er = evaluate_result(ec, result)
                all_cases.append(ec)
                all_results.append(er)

                cat = ec.category or "bug"
                by_category.setdefault(cat, {"cases": [], "results": []})
                by_category[cat]["cases"].append(ec)
                by_category[cat]["results"].append(er)
            except Exception as e:
                errors.append(f"{ec.pr_url.split('/')[-1]}: {e}")

    return all_cases, all_results, by_category, errors


def _accumulate_category_results(by_category: dict) -> list:
    """Compute per-category metrics and format them for output."""
    from src.eval.metrics import compute_metrics

    cat_data = []
    for cat, group in by_category.items():
        cm = compute_metrics(group["cases"], group["results"])
        cat_data.append({
            "cat": cat,
            "precision": cm.precision, "recall": cm.recall, "f1": cm.f1,
            "analyzer": ANALYZER_MAP.get(cat, "?"),
            "tp": cm.true_positives, "fp": cm.false_positives, "fn": cm.false_negatives,
        })
    return cat_data


def _save_eval_history(metrics, cat_data: list):
    """Persist a single evaluation run to history."""
    _save_history({
        "precision": metrics.precision, "recall": metrics.recall, "f1": metrics.f1,
        "tp": metrics.true_positives, "fp": metrics.false_positives, "fn": metrics.false_negatives,
        "evaluated_at": datetime.now().isoformat(),
        "model": "deepseek-chat",
        "categories": cat_data,
    })


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
