"""A/B testing framework — compare prompt/model variants on eval cases."""

from dataclasses import dataclass, field


@dataclass
class ABTest:
    name: str
    control_prompt: str      # prompt version name
    treatment_prompt: str    # prompt version name
    control_model: str = "deepseek-chat"
    treatment_model: str = "deepseek-chat"
    eval_cases: list[str] = field(default_factory=list)  # list of case file paths


@dataclass
class ABTestResult:
    test_name: str
    control_precision: float
    control_recall: float
    control_f1: float
    treatment_precision: float
    treatment_recall: float
    treatment_f1: float
    winner: str = ""         # "control" | "treatment" | "tie"
    confidence: float = 0.0  # how confident we are in the result

    def summary(self) -> str:
        return (
            f"AB Test: {self.test_name}\n"
            f"  Control ({self.control_precision:.0%}P {self.control_recall:.0%}R F1={self.control_f1:.2f})\n"
            f"  Treatment ({self.treatment_precision:.0%}P {self.treatment_recall:.0%}R F1={self.treatment_f1:.2f})\n"
            f"  Winner: {self.winner or 'tie'}"
        )


def compare_metrics(control_p: float, control_r: float,
                    treatment_p: float, treatment_r: float) -> ABTestResult:
    """Compare two sets of metrics and determine a winner."""
    control_f1 = (2 * control_p * control_r / (control_p + control_r)) if (control_p + control_r) > 0 else 0
    treatment_f1 = (2 * treatment_p * treatment_r / (treatment_p + treatment_r)) if (treatment_p + treatment_r) > 0 else 0

    result = ABTestResult(
        test_name="comparison",
        control_precision=control_p, control_recall=control_r, control_f1=round(control_f1, 3),
        treatment_precision=treatment_p, treatment_recall=treatment_r, treatment_f1=round(treatment_f1, 3),
    )

    f1_diff = treatment_f1 - control_f1
    if abs(f1_diff) < 0.02:
        result.winner = "tie"
        result.confidence = 0.0
    elif f1_diff > 0:
        result.winner = "treatment"
        result.confidence = min(f1_diff * 2, 1.0)
    else:
        result.winner = "control"
        result.confidence = min(abs(f1_diff) * 2, 1.0)

    return result
