# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 本目录是什么

这是 **`cw-testbench-analyze` skill** 的源目录：分析 UVM Testbench 源码或 Run log 的 Topology 打印信息，输出 JSON 格式的架构描述，再交由 **archify** skill 渲染为 HTML 架构图。

注意：本目录所在 git 仓库的根目录是 **`.claude/skills/`**（worktree 根），其中还有兄弟 skill `cw-hdl-module-analyze`、`cw-testbench-create`。本 skill 独立于外层的 UVM 验证工程（`cw_ddr3_phy_tb`），修改 skill 时不要把外层工程的内容混进来。

## 目录结构

```
cw-testbench-analyze/
├── SKILL.md                 # skill 入口：frontmatter + Workflow（Phase 0/1/2）
├── references/
│   └── testbench_architecture_json_spec.md   # JSON 输出格式规范
├── examples/archify-repo/
│   ├── archify-repo.architecture.json        # 示例 JSON（输入）
│   └── archify-repo.html                     # 示例渲染结果（输出）
└── Readme.md                # 目前仅一行标题，暂未展开
```

## 关键约定

- **SKILL.md frontmatter 格式**：`name` / `description`（触发条件写进 description）/ `metadata`（author=ChipWeaver、version、tags）。修改行为时同步更新 `version`。
- **Workflow 契约**（见 SKILL.md）：
  - Phase 0：明确 TB 源码路径与 `output_dir`（未指定则 `./testbench-analyze.out`）；检查 archify skill 是否存在，不存在则跳过渲染阶段。
  - Phase 1：解析 TB 层级（components 实例、object、接口、config_db 连接），输出 `$output_dir/<tb_name>_architecture.json`，格式必须遵循 `references/testbench_architecture_json_spec.md`。
  - Phase 2：调用 archify skill 生成 `$output_dir/<tb_name>_architecture.html`。
- **文档语言为中文**；skill 描述/正文中用户可见文本保持中文。
- **源码与 log 冲突时以源码为准**（规范中的优先级规则）。

## 已知的不一致（修改前必读）

- `references/testbench_architecture_json_spec.md` 与 `examples/archify-repo/archify-repo.architecture.json` 目前**格式不一致**：
  - 规范描述的是嵌套 `diagram/component/connection` 结构（含 style 色值约定）；
  - 示例 JSON 是 archify 的 JSON IR 格式（`schema_version` / `diagram_type` / `meta` / `components[]`，带 `pos`/`size` 绝对坐标）。
- 修改任一侧时需与 archify skill 的实际输入格式核对（archify 才是真正的渲染方），避免 spec、示例、渲染器三方漂移。skill 尚未实测（git 历史标注 untested / 未测试），改动后应找一个小 TB 工程完整跑一遍 Phase 0→2 验证。
- 旧版 `references/mermaid_block-diagram_syntax.md` 与 `testbench_architecture-diagram_spec.md` 已删除（工作区未提交），不要在新建文档中引用它们。

## 提交

- git 仓库根为 `.claude/skills/`，提交前在仓库根执行 `git status`，确认只提交本 skill 相关文件。
