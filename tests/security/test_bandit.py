import pytest
from unittest.mock import patch, MagicMock
from src.security.bandit_runner import BanditFinding, run_bandit, _parse_output


SAMPLE_BANDIT_JSON = """
{
  "results": [
    {
      "test_id": "B301",
      "test_name": "blacklist",
      "issue_severity": "MEDIUM",
      "issue_confidence": "HIGH",
      "issue_text": "Pickle appears to be used",
      "filename": "src/app.py",
      "line_number": 42,
      "more_info": "https://bandit.readthedocs.io/en/latest/"
    }
  ]
}
"""


class TestBanditRunner:
    def test_returns_empty_when_bandit_not_installed(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            findings, _ = run_bandit(["test.py"])
            assert findings == []

    def test_parses_json_output(self):
        findings = _parse_output(SAMPLE_BANDIT_JSON)
        assert len(findings) == 1
        f = findings[0]
        assert f.issue_id == "B301"
        assert f.severity == "MEDIUM"
        assert f.file == "src/app.py"
        assert f.line == 42

    def test_empty_results(self):
        findings = _parse_output('{"results": []}')
        assert findings == []

    def test_invalid_json(self):
        findings = _parse_output("not json")
        assert findings == []

    def test_filename_filter(self):
        findings = _parse_output(SAMPLE_BANDIT_JSON)
        matching = [f for f in findings if f.file == "src/app.py"]
        assert len(matching) == 1
