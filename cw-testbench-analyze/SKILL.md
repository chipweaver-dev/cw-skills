---
name: cw-testbench-analyze
description: >
  根据 Testbench 源码创建架构框图  
  当用户说 “创建 Testbench/TB 框图” 时触发  
metadata: 
  author: ChipWeaver
  version: "0.1.0"
  tags: Testbench
---

# cw-testbench-analyze

分析 Testbench 源码或 Run log 的 Topology 打印信息，输出 Json 格式的架构描述，用于 Archify Skill 或其他工具生成架构图  

## Workflow

### Phase 1: 明确输入输出

- 检查依赖的 archify skill 是否存在，如果不存在则不运行 `Parse 2`
- 从用户提问或当前工程环境分析 Testbench 源码路径是否明确，如果不明确则询问
- 从用户提问或当前工程环境分析输出文件路径 **output_dir** 是否明确，如果不明确则 `output_dir=./testbench-analyze.out`

### Phase 1: 解析 Testbench 架构到 Json 文件

- 按 Testbench 层级解析各组件的 Components 实例、Object 实例、接口、config_db 连接关系
- Json 文件路径：`$output_dir/<tb_name>_architecture.json`
- Json 文件规范：`references\testbench_architecture_json_spec.md`

### Phase 2: 调用 archify skill 将 Json 描述转换为 html 格式架构图

- html 文件路径：`$output_dir/<tb_name>_architecture.html`
