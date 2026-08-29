---
name: cw-testbench-analyze
description: >
  分析 UVM/SystemVerilog Testbench 源码或 Run log 的 Topology 打印信息，生成 Json 架构描述，
  再经 archify 渲染为 HTML 架构图。
  当用户说「分析 TB 架构」「创建 Testbench/TB 框图」「画 UVM 环境架构图」「解析 print_topology」
  「TB 架构图」等时触发。
metadata:
  author: ChipWeaver
  version: "0.2.1"
  tags: Testbench
---

# cw-testbench-analyze

分析 TB 源码或 Run log 的 Topology 信息 → 输出中间 Json 架构描述 → 转换为 archify IR → 渲染 HTML 架构图。

## Workflow

### Phase 1: 明确输入与输出

- **TB 来源**：用户指定路径；未指定则在当前工程搜索（`tb_top` / `run_test` 所在文件、`uvm_config_db` 集中处）。输入若为 Run log，取 `print_topology()` 等层级打印。**源码与 log 冲突时以源码为准**
- **tb_name**：默认取 TB 顶层 module 名或 `run_test("<test_name>")` 的 test 名；用户指定则从之
- **output_dir**：用户指定；未指定则 `./testbench-analyze.out`
- **archify 依赖**：检查 `~/.claude/skills/archify/` 或工程 `.claude/skills/archify/` 是否存在；不存在则只执行到 Phase 2，并告知用户无法渲染

### Phase 2: 解析 Testbench 架构到 Json 文件

解析要点（按优先级）：

1. **组件树**：从 `tb_top` 的 `run_test()` 与 env/agent 的 `build_phase` 例化关系还原层级；agent 内部展开到 sqr/drv/mon
2. **TLM 连接**：port / export / analysis port 的 `connect_phase` 连接
3. **接口与 config_db**：virtual interface 的 `config_db::set/get`、config object 传递
4. **RAL / object**：寄存器模型、sequence/config 等 uvm_object 的归属

- Json 文件路径：`$output_dir/<tb_name>_architecture.json`
- Json 文件规范：`references/testbench_architecture_json_spec.md`
- 自检：所有 connection 引用的组件都存在于组件树中；层级与源码一致

### Phase 3: 转换为 archify IR 并渲染

- 按映射规范 `references/testbench_architecture_json_to_archify_ir_spec.md` 将中间 Json 转换为 archify architecture IR，写入 `$output_dir/<tb_name>_archify.architecture.json`
- 执行 `archify.mjs validate`：showcase 全过（9 checks、0 error、0 warning）后冻结候选，再执行 `archify.mjs deliver` 生成 html
- **例外**：用户明确要求时，可改为把中间 Json 直接交给 archify skill 全流程渲染（见映射规范头部说明）
- html 文件路径：`$output_dir/<tb_name>_architecture.html`
- validate/deliver 失败按诊断定点修复重跑，连续两轮无改善则如实报告
