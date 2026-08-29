# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 本目录是什么

这是 **`cw-testbench-analyze` skill** 的源目录：分析 UVM Testbench 源码或 Run log 的 Topology 打印信息，输出自有格式的中间 JSON，再按映射规范转换为 **archify** IR 并渲染为 HTML 架构图。

注意：本目录所在 git 仓库的根目录是 **`.claude/skills/`**（worktree 根），其中还有兄弟 skill `cw-hdl-module-analyze`、`cw-testbench-create`。本 skill 独立于外层的 UVM 验证工程（`cw_ddr3_phy_tb`），修改 skill 时不要把外层工程的内容混进来。

## 目录结构

```
cw-testbench-analyze/
├── SKILL.md                 # skill 入口：frontmatter + Workflow（Phase 1/2/3）
├── references/
│   ├── testbench_architecture_json_spec.md              # Phase 2 中间 JSON 格式规范
│   └── testbench_architecture_json_to_archify_ir_spec.md # Phase 3 → archify IR 映射与校验规范
├── examples/archify-repo/
│   ├── archify-repo.architecture.json        # archify IR 示例（Phase 3 目标格式参考）
│   └── archify-repo.html                     # 示例渲染结果
└── Readme.md
```

## 关键约定

- **SKILL.md frontmatter 格式**：`name` / `description`（触发条件写进 description）/ `metadata`（author=ChipWeaver、version、tags）。修改行为时同步更新 `version`（当前 0.2.1）。
- **Workflow 契约**（见 SKILL.md）：
  - Phase 1：明确 TB 来源（源码或 log，冲突以源码为准）、`tb_name`、`output_dir`（默认 `./testbench-analyze.out`）；检查 archify skill（`~/.claude/skills/archify/` 或工程 `.claude/skills/archify/`），不存在则只执行到 Phase 2。
  - Phase 2：解析 TB 层级，输出 `$output_dir/<tb_name>_architecture.json`，格式必须遵循 `testbench_architecture_json_spec.md`。
  - Phase 3：按 `testbench_architecture_json_to_archify_ir_spec.md` 转为 archify IR（`<tb_name>_archify.architecture.json`），经 `archify.mjs validate`（showcase 全过）后 `deliver` 生成 `$output_dir/<tb_name>_architecture.html`。例外：用户明确要求时，可改为把中间 Json 直接交给 archify skill 全流程渲染。
- **文档语言为中文**；skill 描述/正文中用户可见文本保持中文。
- **config_db 不建模为节点**，只作为 `config-db` 连接类型表达（中间格式规范 2.3/2.4）。

## 格式链路与已定的设计决策（修改前必读）

- 三方链路已对齐：中间 JSON（自有嵌套格式）→ 映射规范 → archify IR（`schema_version=1` / `components[]` / `boundaries[]` / `connections[]`）。`examples/archify-repo/` 是 archify IR 格式的参考示例，**与中间 JSON 格式不同是预期的**。
- 中间 JSON 的结构性决策（用户 2026-08-29 拍板）：`name` 必填、key 层级内唯一；`diagram` 是抽象图表概念；connection 可写在任一祖先层级描述本级及子级的连接；不合并 diagram/component 为统一 node schema。
- 遗留未定：connection 键名中组件名按局部名还是全路径解析、同一对组件多条连接的重键消歧、中间格式 `text` 含 `\n` 时 archify 能否渲染。
- skill 尚未实测；改动后应找一个小 TB 工程完整跑一遍 Phase 1→3 验证。
- 旧版 `references/mermaid_block-diagram_syntax.md` 与 `testbench_architecture-diagram_spec.md` 已删除（工作区未提交），不要在新建文档中引用它们。

## 提交

- git 仓库根为 `.claude/skills/`，提交前在仓库根执行 `git status`，确认只提交本 skill 相关文件。
