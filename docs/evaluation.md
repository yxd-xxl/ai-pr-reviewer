# PR 27 Verification

## Gate 1: pytest

```bash
python -m pytest tests/ -v
# Expected: all passed
```

## Gate 2: Default behavior unchanged

```bash
python -m src.cli.main review https://github.com/yxd-xxl/ai-pr-reviewer/pull/7
# Expected: same output as before (4 files, N findings)
```

## Gate 3: Mock mode

```bash
LLM_PROVIDER=mock GITHUB_TOKEN=xxx python -m src.cli.main review <URL>
# Expected: mock findings generated
```

## Gate 4: Deliver not broken

```bash
python -m src.cli.main review <URL> --delivery github
# Expected: dry-run output
```

## Gate 5: --categories security

```bash
python -m src.cli.main review <URL> --categories security
# Expected: only security findings (category="security")
```

## Gate 6: --categories bug,style

```bash
python -m src.cli.main review <URL> --categories bug,style
# Expected: LLMAnalyzer covers both
```

## Gate 7: Invalid category

```bash
python -m src.cli.main review <URL> --categories invalid
# Expected: error message with valid options
```

## Gate 8: Finding fields

Every finding must have: severity, category, analyzer, confidence, evidence, location
