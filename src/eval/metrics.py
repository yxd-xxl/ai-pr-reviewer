from dataclasses import dataclass, field
import json
from pathlib import Path


@dataclass
class EvalCase:
    pr_url: str
    expected_files: list[str] = field(default_factory=list)
    expected_titles: list[str] = field(default_factory=list)
    forbidden_titles: list[str] = field(default_factory=list)
    category: str = "bug"

    @classmethod
    def from_file(cls, path: str) -> "EvalCase":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            pr_url=data["pr_url"],
            expected_files=data.get("expected_files", []),
            expected_titles=data.get("expected_titles", []),
            forbidden_titles=data.get("forbidden_titles", []),
            category=data.get("category", "bug"),
        )


@dataclass
class EvalResult:
    pr_url: str
    matched_expected: set[str] = field(default_factory=set)
    false_positives: list[str] = field(default_factory=list)
    false_negatives: list[str] = field(default_factory=list)


@dataclass
class EvalMetrics:
    precision: float
    recall: float
    f1: float
    total_expected: int
    total_found: int
    true_positives: int
    false_positives: int
    false_negatives: int

    def summary(self) -> str:
        return (
            f"Precision: {self.precision:.1%}  "
            f"Recall: {self.recall:.1%}  "
            f"F1: {self.f1:.3f}  "
            f"(TP={self.true_positives} FP={self.false_positives} "
            f"FN={self.false_negatives})"
        )


def compute_metrics(cases: list[EvalCase],
                    results: list[EvalResult]) -> EvalMetrics:
    if not cases:
        return EvalMetrics(1.0, 1.0, 1.0, 0, 0, 0, 0, 0)

    tp = sum(len(r.matched_expected) for r in results)
    fp = sum(len(r.false_positives) for r in results)
    fn = sum(len(r.false_negatives) for r in results)
    total_expected = tp + fn
    total_found = tp + fp

    precision = tp / total_found if total_found > 0 else 1.0
    recall = tp / total_expected if total_expected > 0 else 1.0
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) > 0 else 0.0)

    return EvalMetrics(
        precision=precision, recall=recall, f1=f1,
        total_expected=total_expected, total_found=total_found,
        true_positives=tp, false_positives=fp, false_negatives=fn,
    )


def per_category_summary(cases: list[EvalCase],
                         results: list[EvalResult]) -> str:
    by_cat: dict[str, dict] = {}
    for ec, er in zip(cases, results):
        cat = ec.category
        if cat not in by_cat:
            by_cat[cat] = {"tp": 0, "fp": 0, "fn": 0}
        by_cat[cat]["tp"] += len(er.matched_expected)
        by_cat[cat]["fp"] += len(er.false_positives)
        by_cat[cat]["fn"] += len(er.false_negatives)

    lines = ["Per-category:", ""]
    for cat, counts in sorted(by_cat.items()):
        tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
        p = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        r = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        lines.append(f"  {cat}: P={p:.0%} R={r:.0%} (TP={tp} FP={fp} FN={fn})")
    return "\n".join(lines)
