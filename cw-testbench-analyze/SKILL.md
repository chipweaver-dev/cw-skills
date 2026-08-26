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

分析 Testbench 源码或 Run log 的 Topology 打印信息，输出 Mermaid 格式的架构图。  

## Workflow

### Phase 1: 明确输入输出

- 从用户提问分析 Testbench 源码路径是否明确，如果不明确则询问
- 从用户提问分析输出文件路径 **output_dir** 是否明确，如果不明确则 `output_dir=./testbench-analyze.out`

### Phase 1: 解析 Testbench 到 Json 文件

- 按 Testbench 层级解析各组件的 Components 实例、Object 实例、接口、config_db 连接关系
- 解析结果 Json 文件路径： `$output_dir/<tb_name>_topology.json`

### Phase 2: 根据 Json 描述转换为 Mermaid 框图

- Mermaid 框图文件路径：`$output_dir/<tb_name>_mermaid_architecture_diagram.md`
- Mermaid testbench 架构框图格式规范：references\mermaid_architecture_diagram_spec.md 
- Mermaid Block 类型框图语法参考：references\Block-Diagram_Syntax_Mermaid.md
