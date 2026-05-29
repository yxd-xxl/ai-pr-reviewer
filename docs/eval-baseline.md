# Evaluation Baseline

12 annotated test cases across 6 perspectives.
Run `python -m src.cli.main evaluate` to check for regressions.

## Cases

| # | Name | Category | PR |
|---|------|------|-----|
| 1 | sec_bandit | security | #19 |
| 2 | bug_postprocess | bug | #7 |
| 3 | bug_streamlit | bug | #13 |
| 4 | perf_parallel | performance | #33 |
| 5 | quality_refactor | quality | #23 |
| 6 | failure_robustness | failure | #30 |
| 7 | design_config | design | #15 |
| 8 | fp_import | bug | #39 |
| 9 | pr7_postprocess | bug | #7 |
| 10 | pr13_streamlit | bug | #13 |
| 11 | pr3_fetch | design | #3 |
| 12 | (reserved) | - | - |

## How to Update Baseline

```bash
python -m src.cli.main evaluate
# Copy output to this doc
```

## Current Baseline (recorded PR 3)

(Will be filled after first real LLM evaluation run)
