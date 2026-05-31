# AI PR Reviewer

<br>
<div align="center">

**AI 驱动的 GitHub Pull Request 代码评审工具**

SAST + LLM 多阶段流水线 · 6 维独立分析器 · React SPA 前端 · FastAPI 后端

[![Tests](https://img.shields.io/badge/tests-304%20passed-brightgreen)]()
[![PRs](https://img.shields.io/badge/PRs-32%20merged-blue)]()
[![Python](https://img.shields.io/badge/python-3.11+-blue)]()
[![TypeScript](https://img.shields.io/badge/typescript-5.7+-3178c6)]()
[![React](https://img.shields.io/badge/react-18-61dafb)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

</div>

> **七牛云 XEngineer 暑期实训营 第二批次（2026-05-29 ~ 2026-05-31）· 选题三**

---

## Demo

> **B 站 Demo 视频**：[七牛云 第二批 AI PRReview](https://www.bilibili.com/video/BV1YTVQ6iEPa/) — 完整演示连接 GitHub → 选择仓库 → 评审 PR → 查看 Finding → 批量评审 → Fix PR 全流程

---

## 快速开始

```bash
git clone https://github.com/yxd-xxl/ai-pr-reviewer.git
cd ai-pr-reviewer
pip install -r requirements.txt
cp .env.example .env          # 编辑填入 GITHUB_TOKEN

# CLI（mock 模式，无需 LLM API Key）
python -m src.cli.main review https://github.com/owner/repo/pull/42

# React SPA 前端（主 UI）
cd frontend && npm install && npm run dev   # → http://localhost:5174

# FastAPI 后端
python -m uvicorn backend.main:app --port 8000   # → http://localhost:8000
```

开启真实 AI 分析：编辑 `.env` 设置 `LLM_PROVIDER=deepseek` + `LLM_API_KEY`。

---

## 功能矩阵

### 核心评审引擎

| 功能 | 说明 |
|------|------|
| **PR Diff 解析** | 自动获取变更、解析 hunk、提取文件上下文 |
| **6 维独立分析器** | Security / Bug / Performance / Style / Architecture / Failure，各自独立 prompt |
| **SAST + LLM 融合** | Bandit / ESLint / staticcheck / Semgrep 静态扫描 → LLM 二次判断 |
| **安全专项 (CWE)** | OWASP Top 10 + CWE 分类，自动标注 CWE-ID |
| **独立验证** | Critical / High finding 经第二 LLM 独立验证，过滤误报 |
| **多阶段 Prompt Chaining** | 变更摘要 → 风险分类 → 逐文件分析 → 建议生成 |
| **项目规范感知** | 自动加载 `.claude/CLAUDE.md` 作为评审上下文 |
| **Fix Patch 生成** | 为每个 Finding 生成可应用的代码补丁（unified diff 格式） |

### 交付与集成

| 功能 | 说明 |
|------|------|
| **GitHub Inline Comment** | Finding 回写到 PR 对应代码行（dry-run / publish 双模） |
| **Suggested Changes** | 一键将 Fix Patch 以 GitHub 建议修改格式应用到 PR |
| **Risk Score + Checklist** | 0-100 六维风险评分 + Reviewer Checklist |
| **9 段完整报告** | Overview / Risk / Coverage / Priority / Details / Test Impact / Checklist / Delivery / Limitations |
| **批量评审** | 并行 ThreadPoolExecutor，一次评审多个 PR |
| **增量 Review** | 同 PR 同 commit 自动跳过，不重复刷评论 |
| **GitHub App** | Installation token 认证，团队级一键部署 |
| **Webhook Server** | PR opened / synchronize 事件自动触发评审 |
| **GitHub Action** | 开箱即用的 CI 集成，自动加 risk label |

### Web 应用（React + FastAPI）

| 功能 | 说明 |
|------|------|
| **GitHub OAuth 登录** | 像 VS Code 一样的 GitHub 授权体验 |
| **仓库选择器** | 搜索 / 过滤 / 语言筛选，公开和私有仓库 |
| **Review Queue** | 真实 PR 列表，批量选择 + 并行评审 |
| **Analyze Workspace** | 三栏布局（配置 / Findings / 详情），实时进度 |
| **Finding Inspector** | 详情 / 证据 / 建议 / Fix Patch / 反馈 / 追问 |
| **Dashboard** | 统计卡片 / 风险分布 / 评审历史 / 快速操作 |
| **Evaluation Center** | F1 分数 / 分类指标 / 运行历史 / 趋势对比 |
| **Settings** | LLM 配置 / 评审规则 / 置信度 / GitHub Token 持久化 |
| **i18n 国际化** | 中英文一键切换，覆盖所有页面标签 |
| **暗色模式** | Light / Dark 主题切换 |

### 质量保障

| 功能 | 说明 |
|------|------|
| **评估框架** | Precision / Recall / F1 量化评审质量，支持模拟评估 |
| **Feedback 系统** | 10 种状态标记（TP / FP / Won't Fix / Duplicate / Fixed 等） |
| **分析预算系统** | max_files / max_llm_calls / large_pr_threshold 成本控制 |
| **RBAC 权限** | Viewer → Member → Admin → Owner 四级权限模型 |
| **审计日志** | 所有操作自动记录，支持合规审计 |

---

## 架构

```
┌─────────────────────────────────────────────────┐
│                React SPA (TypeScript)            │
│   Connect → ReviewQueue → ReviewWorkspace        │
│   Dashboard → EvaluationCenter → Settings        │
└────────────────────┬────────────────────────────┘
                     │ REST + WebSocket
┌────────────────────▼────────────────────────────┐
│              FastAPI Backend (Python)            │
│   auth / repos / review / settings / eval        │
└────────────────────┬────────────────────────────┘
                     │
        ┌────────────┼──────────────┐
        ▼            ▼              ▼
   ┌─────────┐ ┌──────────┐ ┌──────────┐
   │ GitHub  │ │   LLM    │ │  SQLite  │
   │  API    │ │ Adapters │ │   DB     │
   └─────────┘ └──────────┘ └──────────┘
        │            │
   ┌────┴────┐ ┌────┴──────────────┐
   │ OAuth   │ │ DeepSeek / Claude │
   │ REST    │ │ GPT-4o / Mock     │
   └─────────┘ └───────────────────┘
```

### 模块职责

| 模块 | 职责 | 核心类型 |
|------|------|----------|
| `src/core/` | 领域类型 + 配置 | `PullRequest`, `Finding`, `ReviewConfig` |
| `src/context/` | GitHub 数据获取 + 用户画像 | `GitHubClient`, `parse_pr_url` |
| `src/analysis/` | 6 维分析引擎 | `Analyzer` ABC → `LLMAnalyzer` … |
| `src/llm/` | LLM 适配器（可插拔） | `LLMAdapter` ABC → DeepSeek / Anthropic / OpenAI / Mock |
| `src/postprocess/` | 去重 · 过滤 · 置信度 · 排序 | `PostProcessor` |
| `src/delivery/` | 结果交付 | `Delivery` ABC → GitHub / CLI / Markdown |
| `src/eval/` | 质量评估 | `EvalCase`, `compute_metrics` |
| `src/store/` | SQLite 持久化 | `ReviewRepo`, `FeedbackRepo`, `UserRepo` |
| `backend/` | FastAPI REST API | 5 routers, JWT auth, RBAC middleware |
| `frontend/` | React 18 SPA | 9 页面, i18n, 暗色模式 |

---

## 测试

```bash
python -m pytest tests/ -v    # 304 tests passed（mock mode）
                                # 3 eval cases（demo PRs with intentional bugs）
```

---

## 项目规模

| 指标 | 数值 |
|------|------|
| 合并 PR 数 | 32（GitHub 正式 PR） + 28（分支 PR → integration） |
| 总 Commits | 203（2026-05-29 ~ 2026-05-31） |
| 测试用例 | 304 |
| 前端页面 | 9（Connect / Register / Onboarding / Dashboard / ReviewQueue / ReviewWorkspace / ReviewReport / EvaluationCenter / Settings） |
| 后端 Router | 5（auth / repos / review / settings / eval） |
| 分析器 | 6（Security / Bug / Performance / Style / Architecture / Failure） |
| LLM 适配器 | 4（DeepSeek / Anthropic Claude / OpenAI GPT-4o / Mock） |

---

## 依赖

### Python（后端）

| 依赖 | 用途 | 必需 |
|------|------|------|
| FastAPI + Uvicorn | REST API Server | ✅ |
| PyGithub | GitHub REST API | ✅ |
| PyYAML | 配置解析 | ✅ |
| click | CLI 框架 | ✅ |
| anthropic | Claude API | 可选 |
| bandit | Python SAST | 可选 |
| python-dotenv | 环境变量管理 | ✅ |
| pytest + pytest-mock | 测试框架 | 开发 |

### TypeScript（前端）

| 依赖 | 用途 |
|------|------|
| React 18 + react-router-dom v7 | SPA 框架 |
| Vite 8 | 构建工具 |
| TypeScript 5.7 | 类型系统 |

零第三方 UI 组件库——所有组件自行实现。

---

## PR 提交记录

PR 遵循 `一个 PR = 一个功能/模块` 原则，按阶段组织：

| 阶段 | PR | 内容 |
|------|-----|------|
| **Foundation** | #1–#9 | Fix Patch 生成、验证、评估基线、评审模式、变更检测、GitHub App、权限模型、反馈闭环 |
| **Enhancement** | #10–#18 | 自动 PR、Finding 追问、Action Plan、SQLite 持久化、历史查询、Streamlit 趋势、用户画像、仓库策略、GitLab 适配器 |
| **SAST & Delivery** | #19–#21 | 分析器插件、SARIF 输出、JSON API |
| **Full-stack** | #70–#80 | Connect 页、Review Queue、Analyze Workspace、History + Settings、DB Schema、JWT Auth、RBAC、GitHub App Setup、Notifications、暗色模式 |
| **Integration** | — | 全线集成到 `integration` 分支，前后端打通、i18n、端到端配置流 |

全部 203 commits 时间戳落在 2026-05-29 ~ 2026-05-31 之内，无临尾突击提交。

---

## 原创说明

本项目所有代码均为独立编写，未复制他人代码。

### 架构设计参考（已注明来源）

| 参考项目 | 借鉴思路 |
|----------|----------|
| [PRSense](https://github.com/navxio/PRSense) | 六边形架构（端口-适配器模式） |
| [Uber uReview](https://github.com/uber/uReview) | 多阶段 prompt-chaining 流水线 |
| [Smart PR Review](https://github.com/fullstackcrew-alpha/skill-smart-pr-review) | 6 层分析 + 独立验证思路 |
| [Microsoft Sphinx](https://github.com/microsoft/sphinx) | 结构化数据生成 + checklist 评估 |
| [cubic](https://github.com/cubic) | 微 Agent 架构 + 显式推理日志 |

### AI 辅助声明

本项目的开发过程中使用了 AI 编程助手（Claude Code）辅助代码生成、测试编写和文档撰写。所有 AI 生成的代码均经过人工审查和测试验证，确保质量和安全性。

---

## 开发脚本

```bash
bash scripts/start.sh   # 启动（自动停旧进程）
bash scripts/stop.sh    # 停止

# 单独启动前后端
cd frontend && npm run dev              # React Dev Server → :5174
python -m uvicorn backend.main:app --reload  # FastAPI → :8000
```

## Docker 部署

```bash
docker-compose up -d   # 启动 app + api + worker（可选）
```
