# Evaluation Guide

评估框架用于量化 AI PR Reviewer 的评审质量。

## 指标说明

| 指标 | 公式 | 含义 |
|------|------|------|
| **Precision** | TP / (TP + FP) | 报告的 Finding 中有多少是真实的 |
| **Recall** | TP / (TP + FN) | 应该发现的 Issue 中实际发现了多少 |
| **F1 Score** | 2 × P × R / (P + R) | 精确率和召回率的调和平均 |

## 评估案例

3 个标注测试用例（`tests/eval/` 目录），分别覆盖三类典型场景：

| 案例 | PR | 类别 | 期望发现数 |
|------|-----|------|-----------|
| `sec_demo.json` | [#68](https://github.com/yxd-xxl/ai-pr-reviewer/pull/68) | Security | 6（SQL 注入、硬编码密钥、命令注入、路径遍历、不安全的 pickle、弱哈希 MD5） |
| `bug_demo.json` | [#69](https://github.com/yxd-xxl/ai-pr-reviewer/pull/69) | Bug | 10（None 引用、AttributeError、off-by-one、裸 except、可变默认参数、竞态条件、未关闭资源、除零、运算符优先级） |
| `perf_demo.json` | [#70](https://github.com/yxd-xxl/ai-pr-reviewer/pull/70) | Performance | 8（N+1 查询、O(n²) 嵌套循环、无界增长、缓存缺失、串行化、重复计算、内存泄露） |

## 运行评估

```bash
# CLI
python -m src.cli.main evaluate

# Web UI（Evaluation Center）
# 设置 LLM Provider 为 Mock → 点击 "Run Evaluation"
```

Mock 模式下直接生成模拟结果，无需 LLM API key。真实评估需配置 LLM provider。

## 最新基线

| 类别 | Precision | Recall | F1 | 状态 |
|------|-----------|--------|-----|------|
| Security | 83.3% | 83.3% | 0.833 | Good |
| Bug | 87.5% | 70.0% | 0.778 | Good |
| Performance | 85.7% | 75.0% | 0.800 | Good |
| **Overall** | **85.7%** | **75.0%** | **0.800** | **Good** |

基线基于 3 个标注案例的 mock 模拟评估。评估历史记录存储在 `.ai-pr-reviewer/eval_history.json`。
