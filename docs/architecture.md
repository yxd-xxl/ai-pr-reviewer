# Architecture

## Hexagonal (Ports & Adapters)

```
UI Layer:     Streamlit (app.py) | CLI (src/cli/) | GitHub Actions | Webhook
                  │                      │                │            │
Service Layer:    └──────────────────────┴────────────────┴────────────┘
                                       │
                          src/service/review_service.py
                          src/service/batch_service.py
                                       │
                  ┌────────────────────┼────────────────────┐
Orchestration:    src/pipeline.py (run_review, check_changes, etc.)
                  └────────────────────┬────────────────────┘
                                       │
     ┌─────────┬──────────┬───────────┼───────────┬──────────┬──────────┐
     ▼         ▼          ▼           ▼           ▼          ▼          ▼
  context/  analysis/  postprocess/  delivery/  security/   store/   feedback/
     │         │           │            │          │          │         │
 GitHub   Analyzer    PostProcessor  Markdown   Bandit    SQLite    Tracker
 GitLab   LLMAnalyzer  (7 steps)     SARIF      ESLint    ReviewRepo
 Diff     BugAnalyzer                GitHub     staticcheck
 Parser   SecurityAna                Checklist
 Convent  PerfAnalyzer               Fix PR
 ions     StyleAnalyzer              Webhook
 Change   Composite                  Report
 Detector  │                         Risk Score
           ▼
        prompts/ (8 files: summary, analysis, security, bug,
                  performance, style, verify, fix, verify_fix, followup)
```

## Core Domain Types (src/core/types.py)

Zero I/O dependencies — pure dataclasses:
- `PullRequest`, `FileChange`, `DiffHunk`, `Location`
- `Finding`, `ReviewResult`, `ReviewContext`, `ProjectConvention`
- `FixProposal`, `FixRun`
- `ReviewConfig`, `DeliveryConfig`, `AnalysisBudget`

## Analyzer Registry

| Category | Analyzer Class | Own Prompt? | Verification? |
|----------|---------------|-------------|---------------|
| security | SecurityAnalyzer | security.py | No |
| bug | LLMAnalyzer | analysis.py (6-perspective) | critical+high |
| performance | LLMAnalyzer | analysis.py | critical+high |
| style | LLMAnalyzer | analysis.py | No |
| architecture | LLMAnalyzer | analysis.py | critical+high |

## LLM Pipeline (5-stage)

```
Stage 1: PR Summary (1 LLM call)
Stage 2: Per-file Multi-Perspective Analysis (N files × 4 threads)
Stage 3: Independent Verification (critical/high findings × 4 threads)
Stage 4: Fix Patch Generation (fixable findings × 4 threads)
Stage 5: Fix Verification (patched findings, sequential)
```

## SAST Integration

| Language | Tool | Runner | Status |
|----------|------|--------|--------|
| Python | Bandit | bandit_runner.py | Production |
| JavaScript | ESLint | eslint_runner.py | Production |
| TypeScript | ESLint | eslint_runner.py | Production |
| Go | staticcheck | staticcheck_runner.py | Production |

Unified dispatch: `src/security/runner.py` → `run_sast(file_paths)`

## Post-Processing Pipeline (7 steps)

```
1. Low confidence filter (< min_confidence)
2. Severity sort (critical > high > medium > low)
3. Evidence gate (no evidence → -0.3 confidence)
4. Feedback gate (known FP → -0.4, duplicate → -0.3, wont_fix → -0.2)
5. Deduplication (same file + category + title similarity > 80%)
6. Re-filter post evidence/feedback
7. Count limit (fast=5, balanced=10, deep=20)
```

## Configuration

Priority: CLI args > `.ai-pr-reviewer/{owner}_{repo}.yml` > `.ai-pr-reviewer.yml` > env vars > defaults

Key env vars: `GITHUB_TOKEN`, `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`
