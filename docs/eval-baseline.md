# Evaluation Baseline

> 此文件记录评估框架的基准配置和测试案例。

## 活跃案例（3 个）

| # | 文件 | 类别 | PR |
|---|------|------|-----|
| 1 | `sec_demo.json` | security | [#68](https://github.com/yxd-xxl/ai-pr-reviewer/pull/68) |
| 2 | `bug_demo.json` | bug | [#69](https://github.com/yxd-xxl/ai-pr-reviewer/pull/69) |
| 3 | `perf_demo.json` | performance | [#70](https://github.com/yxd-xxl/ai-pr-reviewer/pull/70) |

## 历史案例（11 个，已归档）

以下案例指向 `ai-pr-reviewer-legacy` 仓库的 PR，在 `integration` 分支中已禁用（`.disabled` 后缀）：

| # | 文件 | 类别 |
|---|------|------|
| 1 | `sec_bandit.json` | security |
| 2 | `bug_postprocess.json` | bug |
| 3 | `bug_streamlit.json` | bug |
| 4 | `perf_parallel.json` | performance |
| 5 | `quality_refactor.json` | quality |
| 6 | `failure_robustness.json` | failure |
| 7 | `design_config.json` | design |
| 8 | `fp_import.json` | bug |
| 9 | `pr7_postprocess.json` | bug |
| 10 | `pr13_streamlit.json` | bug |
| 11 | `pr3_fetch.json` | design |

## 案例格式

每个评估案例文件（JSON）包含：

```json
{
  "pr_url": "GitHub PR URL",
  "category": "security | bug | performance | style | architecture | failure",
  "expected_titles": ["应被检测到的问题关键词"],
  "forbidden_titles": ["不应被标记的关键词"]
}
```

## 更新基线

```bash
# 运行评估
python -m pytest tests/eval/ -v

# 或在 Web UI 中点击 Evaluation Center → Run Evaluation
```
