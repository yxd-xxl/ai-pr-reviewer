from src.eval.metrics import compute_metrics, EvalCase, EvalResult


class TestComputeMetrics:
    def test_perfect_score(self):
        cases = [
            EvalCase(pr_url="p1", expected_files=["a.py"],
                     expected_titles=["Null check"],
                     forbidden_titles=[]),
        ]
        results = [
            EvalResult(pr_url="p1", matched_expected={"Null check"},
                       false_positives=[], false_negatives=[]),
        ]
        m = compute_metrics(cases, results)
        assert m.precision == 1.0
        assert m.recall == 1.0

    def test_false_positive_reduces_precision(self):
        cases = [
            EvalCase(pr_url="p1", expected_files=[], expected_titles=[],
                     forbidden_titles=["Missing import"]),
        ]
        results = [
            EvalResult(pr_url="p1", matched_expected=set(),
                       false_positives=["Missing import"],
                       false_negatives=[]),
        ]
        m = compute_metrics(cases, results)
        assert m.precision == 0.0

    def test_false_negative_reduces_recall(self):
        cases = [
            EvalCase(pr_url="p1", expected_files=["a.py"],
                     expected_titles=["Bug A", "Bug B"],
                     forbidden_titles=[]),
        ]
        results = [
            EvalResult(pr_url="p1", matched_expected={"Bug A"},
                       false_positives=[], false_negatives=["Bug B"]),
        ]
        m = compute_metrics(cases, results)
        assert m.recall == 0.5

    def test_empty_cases(self):
        m = compute_metrics([], [])
        assert m.precision == 1.0
        assert m.recall == 1.0
        assert m.total_expected == 0

    def test_multiple_prs(self):
        cases = [
            EvalCase(pr_url="p1", expected_files=[], expected_titles=["A"], forbidden_titles=[]),
            EvalCase(pr_url="p2", expected_files=[], expected_titles=["B"], forbidden_titles=[]),
        ]
        results = [
            EvalResult(pr_url="p1", matched_expected={"A"}, false_positives=[], false_negatives=[]),
            EvalResult(pr_url="p2", matched_expected={"B"}, false_positives=["X"], false_negatives=[]),
        ]
        m = compute_metrics(cases, results)
        assert m.precision == 2 / 3  # 2 TP / (2 TP + 1 FP)
        assert m.recall == 1.0
