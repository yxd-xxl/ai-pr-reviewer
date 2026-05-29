# AI PR Review 助手 — 项目开发规范

## 项目背景

七牛云 XEngineer 暑期实训营 第二批次（2026-05-29 ~ 2026-05-31），选题三。
单人开发，目标：获得实训营名额。

## 核心原则

### A. 架构约束（六边形架构 / 端口-适配器）

1. **核心领域层零 IO 依赖** — `src/core/` 只含纯 Python dataclass，不导入任何框架或外部服务
2. **可插拔 LLM backend** — `src/llm/` 通过 adapter 接口调用，不硬编码某个模型供应商
3. **分析流水线各阶段独立** — 上下文获取 / 分析引擎 / 后处理 / 交付 四个阶段各自独立模块
4. **模块间仅通过明确接口通信** — 禁止跨模块直接 import 内部实现
5. **每个模块可独立测试** — 依赖通过注入，测试可 mock 任何外部依赖

### B. PR 提交规范（强制）

6. **分支命名**：`pr-<NN>-<slug>`（如 `pr-41-fix-patch-generation`），禁止其他格式
7. **提交信息**：`type(scope): description`（如 `feat(analysis): add fix patch generation`）
8. **一个 PR = 一个功能/模块** — 粒度尽可能小
9. **PR 描述必须包含**：功能描述 + 实现思路 + 测试方式 + 闸门检查
10. **主分支时刻可运行** — 每个 PR 合并后 main 必须能跑通
11. **严禁**：直接 commit 到 main、temp 文件进入仓库（*.tmp.*）、跳号 PR、空描述 PR

### C. 提交前闸门

12. `python -m pytest` 全绿
13. `git diff --staged` 中无 `*.tmp.*` 或 `__pycache__` 文件
14. 分支名符合 `pr-<NN>-<slug>`
15. PR 描述完整（功能/思路/测试/闸门）

### C. 代码质量

11. **TDD — 每个模块先写测试，后写实现**（superpowers:test-driven-development 已开启）
12. **验证后再声称完成**（superpowers:verification-before-completion 已开启）
13. **遇到 bug 走系统化调试流程**（superpowers:systematic-debugging 已开启）
14. **引用外部代码/设计必须在 PR 描述中注明来源**（对齐学术诚信要求）
15. **代码重复率 < 50%**（硬性要求，否则取消资格）

### D. 范围约束

16. **MVP 优先** — 先做完核心流水线，再做 UI 和扩展
17. **首版仅支持 Python 语言 PR 分析** — 聚焦深度而非广度
18. **YAGNI** — 不过度设计，不需要的功能不加

## 目录结构

```
ai-pr-reviewer/
├── .claude/
│   └── CLAUDE.md
├── src/
│   ├── core/            # 领域类型：ReviewSignal, ReviewContext, Finding 等纯 dataclass
│   ├── llm/             # LLM adapter 接口 + DeepSeek/Anthropic/OpenAI 实现
│   ├── context/         # 上下文获取：PR diff 解析、文件上下文、项目规范
│   ├── analysis/        # 分析引擎：多阶段流水线（变更摘要→风险分类→逐文件→建议生成）
│   ├── postprocess/     # 后处理：去重、置信度评分、低价值类别抑制
│   ├── delivery/        # 交付层：GitHub Review Comment、CLI 输出
│   └── cli/             # CLI 入口
├── tests/               # 每个 src/ 子目录对应一个 tests/ 子目录
├── requirements.txt
└── README.md
```

## 技术选型

| 层 | 选型 | 说明 |
|------|------|------|
| GitHub API | PyGithub | Python 官方推荐库 |
| LLM | DeepSeek V4 (已有) + 可插拔 adapter | 默认用 DeepSeek，可通过接口切换到其他模型 |
| 数据持久化 | SQLite | 缓存分析结果，支持增量 review |
| Web 前端 | 单 HTML + 原生 JS（零构建步骤） | 后期可选 |
| Python 静态分析 | Ruff subprocess | 辅助减少 LLM 误报 |

## 工程规范

### E. 模块边界

19. **一个文件只做一件事** — 类型定义、接口、实现、工厂函数分属不同文件
20. **跨模块通信只通过 `src/core/` 中的类型** — 不允许模块间直接 import 内部实现
21. **每个包必须有明确的公共 API（`__init__.py` 导出）** — 其他模块不应绕过 `__init__.py` 直接 import 子模块
22. **实现类必须继承 ABC 接口** — 方便替换（如 `GitHubDelivery(Delivery)`）
23. **prompt 模板按分析类型独立文件** — `prompts/summary.py | analysis.py | security.py`
24. **LLM adapter 按供应商独立文件** — `llm/mock.py | deepseek.py | anthropic.py`

### F. 状态管理

25. **os.environ 只在 `src/` 内部使用** — UI 层通过参数传递配置，不直接操作环境变量
26. **持久化状态通过专用类管理** — 如 `ReviewState`，不散落在各模块中
27. **状态文件放在 `.ai-pr-reviewer/` 目录** — 已加入 `.gitignore`

### G. 接口设计

28. **所有数据流通过 `src/core/types.py` 中定义的 dataclass 传递**
29. **新增分析器实现 `Analyzer` ABC**
30. **新增交付方式实现 `Delivery` ABC**
31. **新增 LLM backend 实现 `LLMAdapter` ABC**
32. **外部边界（API 响应、LLM 输出）需单独校验** — 不信任外部数据直接符合内部类型

### H. 测试规范

33. **TDD：先写测试，后写实现**
34. **每个 `src/` 子包在 `tests/` 有对应目录**
35. **外部依赖（GitHub API、LLM）在测试中必须 mock**
36. **固定样例（fixtures）用于回归测试**

## 合并前质量闸门

每个 PR 合并到 main 前必须全部满足：

1. `python -m pytest` 全部通过
2. `python -m src.cli.main review <PR_URL>` 仍可运行（不因新增功能崩溃）
3. mock 模式（无 LLM_API_KEY）仍可运行
4. Markdown 报告 + GitHub dry-run/publish 不被破坏
5. 新增 analyzer/category 必须有 fixture 或最小验证样例
6. 每条 Finding 必须有 `severity, category, analyzer, confidence, evidence, location`
7. 无 evidence 的 Finding 必须被降级（confidence 降低）或过滤
8. README 或 `docs/evaluation.md` 记录如何验证该 PR

## 参考项目（需在 README 中注明）

- PRSense (`navxio/PRSense`) — 六边形架构设计
- Smart PR Review (`fullstackcrew-alpha/skill-smart-pr-review`) — 6 层分析流水线思路
- Uber uReview — 多阶段 prompt-chaining + 二级评分过滤
- Sphinx (Microsoft) — 结构化数据生成 + checklist 评估
- Workstream — 本地优先 + 零配置设计哲学
- cubic — 微 Agent 架构 + 显式推理日志
