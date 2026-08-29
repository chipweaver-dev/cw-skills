# cw-testbench-analyze

分析 UVM/SystemVerilog Testbench 源码或 Run log 的 Topology 打印信息，生成 HTML 架构图。

## 用法

对 Claude 说：

- 「分析 TB 架构」「创建 Testbench/TB 框图」
- 「画 UVM 环境架构图」「解析 print_topology 输出」

## 处理流程

```text
TB 源码 / Run log
  → Phase 2 解析 → <tb_name>_architecture.json        （本 skill 自有的中间 Json 格式）
  → Phase 3 转换  → <tb_name>_archify.architecture.json（archify IR）
  → archify 渲染 → <tb_name>_architecture.html        （最终交付）
```

输出目录默认 `./testbench-analyze.out`，可在对话中指定。依赖 archify skill 完成渲染（用户级 `~/.claude/skills/archify/` 或工程级安装均可）。

## 文件说明

| 文件 | 说明 |
| --- | --- |
| `SKILL.md` | skill 入口：frontmatter + Workflow（Phase 1/2/3） |
| `references/testbench_architecture_json_spec.md` | Phase 2 中间 Json 的输出格式规范 |
| `references/testbench_architecture_json_to_archify_ir_spec.md` | Phase 3 中间 Json → archify IR 的映射与校验规范 |
| `examples/archify-repo/` | archify IR 输入与其渲染结果的示例（Phase 3 目标格式参考） |

## 已知限制

- skill 尚未做过端到端实测；首次使用建议选一个小 TB 工程完整跑一遍 Phase 1→3 验证。
