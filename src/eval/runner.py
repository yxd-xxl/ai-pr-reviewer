from src.core.types import ReviewResult
from src.eval.metrics import EvalCase, EvalResult


def evaluate_result(eval_case: EvalCase,
                    result: ReviewResult) -> EvalResult:
    """Compare actual review result against expected annotations."""
    actual_titles = {f.title for f in result.findings}
    actual_titles_lower = {t.lower() for t in actual_titles}

    matched = set()
    false_negatives = []

    for exp_title in eval_case.expected_titles:
        found = False
        for at in actual_titles:
            if exp_title.lower() in at.lower():
                matched.add(exp_title)
                found = True
                break
        if not found:
            false_negatives.append(exp_title)

    false_positives = []
    for ft in eval_case.forbidden_titles:
        for at in actual_titles:
            if ft.lower() in at.lower():
                false_positives.append(at)

    return EvalResult(
        pr_url=eval_case.pr_url,
        matched_expected=matched,
        false_positives=false_positives,
        false_negatives=false_negatives,
    )
