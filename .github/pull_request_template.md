## 功能描述

<!-- 一句话说明本 PR 新增 / 修改了什么 -->

## 实现思路

<!-- 简要说明技术选型或核心实现逻辑 -->

## 测试方式

<!-- 如何验证本 PR 功能正常运行 -->

- [ ] `python -m pytest tests/` 全绿
- [ ] mock 模式（`LLM_PROVIDER=mock`）可运行
- [ ] 新增功能可通过以下步骤验证：

## 闸门检查

- [ ] 分支名符合 `pr-<NN>-<slug>` 格式
- [ ] 无 `*.tmp.*` 或 `__pycache__` 文件进入仓库
- [ ] 所有 Finding 包含 severity / category / analyzer / confidence / evidence / location
- [ ] 无 evidence 的 Finding 已降级或过滤

## 依赖与引用说明

- **新增第三方依赖：** <!-- 是 / 否；如是请列出 -->
- **复用过往代码：** <!-- 是 / 否；如是请注明来源 PR 或 commit -->
- **引用外部代码/设计：** <!-- 是 / 否；如是请注明来源 -->
