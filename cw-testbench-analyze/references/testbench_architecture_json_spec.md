# Testbench Architecture JSON Specification

> 本文件是 **cw-testbench-analyze Skill** Phase 1 的输出格式规范：一种**分析中间格式**，用于承载从 TB 源码 / Run log 解析出的架构信息。Phase 2 按 `testbench_architecture_json_to_archify_ir_spec.md` 将其转换为 archify IR 后渲染。
>
> Agent 在生成任何架构 Json 描述时，**必须严格遵循本规范**，以保证输出的一致性、可转换性和可 diff 性。

---

## 1. 目标与适用范围

- **输入**：UVM Testbench 源码（SystemVerilog）或仿真 Run Log（如 `uvm_top.print_topology()` 输出、`uvm_report` 层级打印）
- **输出**：一（或多）个符合本规范的架构 Json 描述文件，描述 TB/组件 的层级、TLM 连接、Virtual Interface 绑定和 config_db 依赖关系
- **优先级**：源码与 log 信息冲突时，以源码为准

## 2. Json 文件格式

### 2.1 顶层 object

```Json
{
    "version"     : "<string>",      // 从 testbench 总结的版本号
    "type"        : "architecture",  // 固定值
    "name"        : "<string>",      // 文件名称
    "description" : "<string>",      // 一句总结
    "diagram"     : { ... }          // 各 diagram 的内容，见 2.2
}
```

### 2.2 diagram / component / connection

`diagram` 是抽象的"图表"概念，不绑定 tb_top；其 `component` 可递归嵌套，结构与 TB 组件层级一致。

```Json
{
    "diagram": {
        "<diagram_name>": {
            "name": "<name>",
            "description": "<description>",
            "layout": "<可选。见 2.5，仅写需覆盖的键>",
            "component": {
                "<component_key>": {
                    "name": "<name>",
                    "class": "<组件的类名>",
                    "type": "<组件类型，见 2.3，决定默认 style>",
                    "hierarchy": "自顶向下层级路径，如 tb_top.env.u_apb_agt",
                    "description": "<description>",
                    "text": "<可选。默认由 name\n(class) 生成，仅在与默认不同时写>",
                    "style": "<可选。默认值见 2.3，仅写需覆盖的键>",
                    "layout": "<可选。默认值见 2.5，仅写需覆盖的键>",
                    "component": { "<component_key>": { "...": "结构同上，递归" } },
                    "connection": { "...": "结构见 connection object" }
                }
            },
            "connection": { "...": "结构见 connection object" }
        },
        "<diagram_name_2>": { "...": "其余 diagram object，结构同上" }
    }
}
```

connection object：

```Json
{
    "<src_name>_to_<dst_name>": {
        "text": "<连接文本，由连接类型规定，见 2.4>",
        "style": "<可选。默认值见 2.4，仅写需覆盖的键>"
    }
}
```

规则说明：

- `<...>` 为占位符，实际输出时替换为具体内容
- `name` 是必要字段，不可删除；key 必须在同一层级的 object 内唯一，但不同 key 允许相同 `name`（key 是唯一标识，`name` 是显示名）
- **connection 的作用域**：connection 可写在任一祖先层级，描述本级**及其子级**组件间的连接关系，不必提升到最近公共祖先
- connection 键名固定为 `<源组件名>_to_<目标组件名>`
- `text` / `style` 均可省略，渲染时取默认值；**仅在与默认不同时显式写出**，保持 Json 精简
- 组件 `type` 按 UVM 基类/角色判定：`uvm_component` 派生按角色归入 2.3 类型；sequence/configuration 等 `uvm_object` 归 `object`
- `layout` 与 `text` / `style` 同理可省略，仅在与默认不同时显式写出（见 2.5）

### 2.3 组件类型与默认 style

公共默认值（所有组件类型共用）：

| style 键 | 默认值 |
| --- | --- |
| `text.horizontal_align` | `center` |
| `text.vertical_align` | `bottom` |
| `text.color` | `#3F3F3F` |
| `line.color` | `#B1CE46` |

各组件类型的差异键（未列出的键取公共默认值）：

| type | shape | fill.color | line.width |
| --- | --- | --- | --- |
| `test` | rounded-rectangle | #A5B6C5 | 2 |
| `testbench` | rounded-rectangle | #8596A5 | 2 |
| `environment` | rounded-rectangle | #9394E7 | 2 |
| `agent` | rounded-rectangle | #5F97D2 | 2 |
| `sequencer` / `driver` / `monitor` | rounded-rectangle | #F1D77E | 2 |
| `referencemodel` / `scoreboard` / `ral` | rounded-rectangle | #63E398 | 2 |
| `object`（sequence/configuration 等 uvm_object） | ellipse | #9DC3E7 | 1 |
| `interface` | diamond | #9DC3E7 | 1 |

其余合法 `shape` 值（仅覆盖时使用）：rectangle, square, circle, triangle, trapezoid, parallelogram, hexagon。

> **config_db 不是组件类型**：config_db 是一种**连接关系**（生产者 set → 消费者 get），统一用 2.4 的 `config-db` 连接表达，不建模为节点。

### 2.4 连接类型与默认 style

#### TLM 连接

component 之间通过 TLM 传递 transaction，如 Sequencer/Driver/Monitor/ReferenceModel/Scoreboard 之间。

- `text` 固定格式：`<producer_port_type>-<transaction_class>-<consumer_port_type>`，如 `port-axi_transaction-export`
- 默认 style：

| style 键 | 默认值 |
| --- | --- |
| `routing` | `right-angle` |
| `color` | `#9DC3E7` |
| `width` | 1 |
| `begin` | `square` |
| `end` | `circle` |

#### config-db 连接

config_db 的 set → get 依赖（virtual interface、config object 等）。

- `text` 固定格式：`<type>`，如 `axi_if`
- 默认 style：

| style 键 | 默认值 |
| --- | --- |
| `routing` | `right-angle` |
| `color` | `#95A5B5` |
| `width` | 1 |
| `begin` | `none` |
| `end` | `block-arrow` |

#### 其他 style 约定

- `routing` 合法值：`right-angle`, `straight`, `curved`
- `begin` / `end` 合法值：`block-arrow`, `open-arrow`, `circle`, `diamond`, `square`, `none`
- `line.width` 表示相对基础位宽的倍数

### 2.5 layout（布局约束）

`layout` 是可选的布局约束对象，diagram 与 component 均可携带，用于约束 archify 的网格排布，避免同级组件被排成过长的一行。当前仅定义一个键：

| layout 键 | 含义 | 默认值 |
| --- | --- | --- |
| `max_column` | 本级直接子组件排布时的最大列数；超过则换行 | diagram：`8`；type=`environment`：`3`；type=`agent`：`2`；其余 component 类型取 diagram 默认（`8`） |

- 与 `style` 同理：默认值不写出，仅在与默认不同时显式写 `layout`
- `max_column` 只约束列数上限，行数由子组件数量自动决定
- 该值在 Phase 3 按 `testbench_architecture_json_to_archify_ir_spec.md` 第 4 节消费
