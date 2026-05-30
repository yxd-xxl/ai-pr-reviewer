# AI PR Reviewer

AI 驱动的 GitHub Pull Request 代码评审工具。输入 PR URL，自动获取变更，通过 **SAST + LLM** 多阶段流水线生成结构化代码评审，支持 GitHub Inline Comment 回写。

> **七牛云 XEngineer 暑期实训营 第二批次 · 选题三**

## Demo 视频

> [待录制] 上传至 B 站/云盘后替换此链接

---

## 快速开始

```bash
git clone https://github.com/yxd-xxl/ai-pr-reviewer.git
cd ai-pr-reviewer
pip install -r requirements.txt
cp .env.example .env  # 编辑填入 GITHUB_TOKEN

# CLI（mock 模式，无需 LLM Key）
python -m src.cli.main review https://github.com/owner/repo/pull/42

# Streamlit Dashboard
pip install -r requirements-ui.txt
streamlit run app.py
```

开启真实 AI 分析：编辑 `.env` 设置 `LLM_PROVIDER=deepseek` + `LLM_API_KEY`。

---

## 功能

| 功能 | 说明 |
|------|------|
| **PR 变更分析** | 获取 diff、解析 hunk、多阶段 LLM 流水线 |
| **SAST + LLM** | Bandit 安全扫描 → LLM 二次判断真假 |
| **安全专项 (CWE)** | OWASP Top 10 + CWE 分类，自动标注 CWE-ID |
| **GitHub Inline Comment** | Finding 回写到 PR 对应代码行（dry-run/publish） |
| **项目规范感知** | 加载 `.claude/CLAUDE.md` 作为 Review 上下文 |
| **增量 Review** | 同 PR 同 commit 自动跳过，不重复刷评论 |
| **配置化** | `.ai-pr-reviewer.yml` 控制置信度、评论数、类别 |
| **Risk Score + Checklist** | 0-100 风险评分 + Reviewer Checklist |
| **评估框架** | Precision/Recall/F1 量化 Review 质量 |
| **GitHub Action** | PR opened/synchronize 自动触发 |
| **多语言** | Python / JavaScript / TypeScript / Go |
| **ESLint + staticcheck** | JS/TS/Go SAST 工具集成，多语言统一调度 |
| **自动 Fix PR** | 生成 fix patch → 安全检查 → 创建 Fix PR |
| **批量 Review** | `batch review` CLI + Bulk Review Center UI |
| **Feedback 系统** | FP/TP/WontFix/Duplicate 等 10 种状态标记 |
| **SQLite 持久化** | Review 历史、Finding、Feedback 持久存储 |
| **多维 Risk Score** | 6 维风险分解：基础/安全/变更/测试/上下文/证据 |
| **GitHub App** | Installation token 认证，团队级部署 |
| **Webhook Server** | 零依赖 HTTP server，PR 事件自动触发 |
| **Streamlit Dashboard** | 浏览器 UI，mock 模式零配置体验 |

---

## 架构

```
app.py (Streamlit UI)
src/cli/main.py (CLI)
        │
        ▼
src/pipeline.py          ←── 编排层
        │
   ┌────┼────────┬──────────┬───────────┐
   ▼    ▼        ▼          ▼           ▼
context  analysis  postprocess  delivery  security
   │      │          │           │          │
   │   ┌──┴──┐     filter    markdown   bandit
   │   │     │               github      │
   │   llm  prompts          checklist   │
   │   │                                 │
   ▼   ▼                                 ▼
core/types.py  ←── 全系统通信语言（零外部依赖）
```

### 模块职责

| 模块 | 职责 | 接口 |
|------|------|------|
| `core/` | 领域类型 + 配置 | `PullRequest`, `Finding`, `ReviewConfig` |
| `context/` | GitHub 数据获取 | `GitHubClient`, `parse_pr_url` |
| `analysis/` | 分析引擎 | `Analyzer` ABC → `LLMAnalyzer`, `SecurityAnalyzer` |
| `llm/` | LLM 适配器 | `LLMAdapter` ABC → `MockLLMAdapter`, `DeepSeekAdapter` |
| `postprocess/` | 后处理 | `PostProcessor` (去重/过滤/排序) |
| `delivery/` | 结果交付 | `Delivery` ABC → `GitHubDelivery`, `render_markdown` |
| `security/` | SAST 集成 | `BanditFinding`, `run_bandit` |
| `langs/` | 语言支持 | `LanguageSupport` 插件注册表 |
| `eval/` | 质量评估 | `EvalCase`, `compute_metrics` |

---

## 测试

```bash
python -m pytest tests/ -v    # 107 tests
```

---

## 依赖

| 依赖 | 用途 |
|------|------|
| PyGithub | GitHub REST API |
| PyYAML | 配置解析 |
| click | CLI 框架 |
| streamlit | Web Dashboard（可选） |
| bandit | Python SAST（可选） |

---

## PR 记录（25 PR）

v1 (PR 1-9): 核心流水线 — 数据模型、GitHub 集成、LLM 分析、后处理、README
v2 (PR 10-13): 增强 — Prompt 优化、Inline Comment、规范加载、Streamlit
Phase 1 (PR 15-18): 产品化 — 配置系统、GitHub Action、增量 Review、评估框架
Phase 2 (PR 19-21): 安全 — Bandit SAST、CWE 分类、Checklist + Risk
Phase 3 (PR 22-25): 深度 — 工程重构、多语言、文档

---

## 原创说明

本项目代码均为独立编写。

### 架构设计参考

| 参考 | 借鉴 |
|------|------|
| PRSense | 六边形架构 |
| Uber uReview | 多阶段 prompt-chaining |
| Smart PR Review | 6 层分析 |
| cubic | 微 Agent + SAST 组合 |

---

## 扩展方向

- GitLab / Gitee 平台支持
- 团队编码规范 RAG
- GitHub Code Scanning SARIF 集成
- 调用链分析 (Trailmark)
## 开发脚本

```bash
bash scripts/start.sh   # 启动（自动停旧进程）
bash scripts/stop.sh    # 停止
```
