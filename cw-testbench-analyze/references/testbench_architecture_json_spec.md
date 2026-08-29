# Testbench Architecture Json Specification

> 本文件是 **cw-testbench-analyze Skill** 的 Json 文件输出格式规范。Agent 在生成任何架构图的Json描述时，**必须严格遵循本规范**，以保证输出的一致性、可渲染性和可 diff 性

---

## 1. 目标与适用范围

- **输入**：UVM Testbench 源码（SystemVerilog）或仿真 Run Log（如 `uvm_top.print_topology()` 输出、`uvm_report` 层级打印）
- **输出**：一（或多）个符合本规范的架构图Json描述文件，描述 TB/组件 的层级、TLM 连接、Virtual Interface 绑定和 config_db 依赖关系
- **优先级**：源码与 log 信息冲突时，以源码为准

## 2. Json 文件格式

### 2.1 顶层 object

```Json
{
    "version"     : <string>,        // 从 testbench 总结的版本号
    "type"        : "architecture",  // 固定值
    "name"        : <string>,        // 文件名称
    "description" : <string>,        // 总结一句描述
    "diagram"     : { ... }          // 包含各 diagram 的内容，见 2.2
}
```

### 2.2 diagram

diagram object 的示例：

```Json
{
    "diagram": {
        "<diagram_name>" : {
            "name": "<name>",
            "description": "<description>",
            "hierarchy": "从 testbench 自顶向下的层级，如 tb_top",
            "class": "<组件的类名>",
            "text": "<一般由 name\n(class) 组成，用于显示在图形的文字>",
            "style": {
                "shape": "rounded-rectangle", // 矩形rectangle, 圆角矩形rounded-rectangle, 正方形square, 椭圆ellipse, 圆形circle, 三角形triangle, 菱形diamond, 梯形trapezoid, 平行四边形parallelogram, 六边形hexagon
                "text": {
                    "horizontal_align": "center", // left,center,right
                    "vertical_align": "bottom", // top,middle,bottom
                    "bold": true,
                    "italic": false,
                    "underline": false,
                    "strikethrough": false,
                    "color": "#3F3F3F"
                },
                "fill": {
                    "color": "#A5B6C5"
                },
                "line": {
                    "color": "#95A5B5",
                    "width": 2
                }
            },
            "component": {
                "<component_name>": {
                    "name": "<name>",
                    "description": "<description>",
                    "hierarchy": "从 testbench 自顶向下的层级，如 tb_top",
                    "class": "<组件的类名>",
                    "text": "<一般由 name\n(class) 组成，用于显示在图形的文字>",
                    "style": "<component_style>",
                    "component": {
                        <sub-component object>
                    },
                    "connection": {
                        "<src_name>_to_<dst_name>": {
                            "text": "<连接文本，由具体组件类型规定>",
                            "style": {
                                "routing": "right-angle", // right-angle,straight,curved
                                "color": "#95A5B5",
                                "width": 2,
                                "begin": "none", // block-arrow, open-arrow, circle, diamond, square, none
                                "end": "block-arrow" // block-arrow, open-arrow, circle, diamond, square, none
                            }
                        }
                    }
                }
            },
            "connection": {
                "<src_name>_to_<dst_name>": {
                    "text": "<连接文本，由具体组件类型规定>",
                    "style": {
                        "routing": "right-angle", // right-angle,straight,curved
                        "color": "#95A5B5",
                        "width": 2,
                        "begin": "none", // block-arrow, open-arrow, circle, diamond, square, none
                        "end": "block-arrow" // block-arrow, open-arrow, circle, diamond, square, none
                    }
                }
            }
        },
        "<diagram_name_2>": {
            // 其余 diagram object，结构同上
        }
    }
}
```

规则说明：

- `<...>` 为占位符，实际输出时按具体组件类型要求替换为具体内容
- `component` 可递归嵌套，结构与 TB 组件层级一致
- `connection` 的键名格式固定为 `<源组件名>_to_<目标组件名>`，text 由具体组件类型规定
- `style` 为格式指导
  - `line.width` 表示相对基础位宽的倍数

### 2.3 各类型 component 的 style

#### Test

| style 键 | 默认值 |
| --- | --- |
| `shape` | `rounded-rectangle` |
| `text.horizontal_align` | `center` |
| `text.vertical_align` | `bottom` |
| `text.color` | "#3F3F3F" |
| `fill.color` | "#A5B6C5" |
| `line.color` | "#B1CE46" |
| `line.width` | 2 |

#### Testbench

Testbench component 的默认 style：

| style 键 | 默认值 |
| --- | --- |
| `shape` | `rounded-rectangle` |
| `text.horizontal_align` | `center` |
| `text.vertical_align` | `bottom` |
| `text.color` | "#3F3F3F" |
| `fill.color` | "#8596A5" |
| `line.color` | "#B1CE46" |
| `line.width` | 2 |

#### Agent

Agent component 的默认 style: 

| style 键 | 默认值 |
| --- | --- |
| `shape` | `rounded-rectangle` |
| `text.horizontal_align` | `center` |
| `text.vertical_align` | `bottom` |
| `text.color` | "#3F3F3F" |
| `fill.color` | "#5F97D2" |
| `line.color` | "#B1CE46" |
| `line.width` | 2 |

#### Environment

| style 键 | 默认值 |
| --- | --- |
| `shape` | `rounded-rectangle` |
| `text.horizontal_align` | `center` |
| `text.vertical_align` | `bottom` |
| `text.color` | "#3F3F3F" |
| `fill.color` | "#9394E7" |
| `line.color` | "#B1CE46" |
| `line.width` | 2 |

#### Sequencer,Driver,Monitor

| style 键 | 默认值 |
| --- | --- |
| `shape` | `rounded-rectangle` |
| `text.horizontal_align` | `center` |
| `text.vertical_align` | `bottom` |
| `text.color` | "#3F3F3F" |
| `fill.color` | "#F1D77E" |
| `line.color` | "#B1CE46" |
| `line.width` | 2 |

#### Referencemodel,Scoreboard

| style 键 | 默认值 |
| --- | --- |
| `shape` | `rounded-rectangle` |
| `text.horizontal_align` | `center` |
| `text.vertical_align` | `bottom` |
| `text.color` | "#3F3F3F" |
| `fill.color` | "#63E398" |
| `line.color` | "#B1CE46" |
| `line.width` | 2 |

#### Sequence,Configuration 等 uvm_object

Sequence,Configuration 等 uvm_object 的默认 style:

| style 键 | 默认值 |
| --- | --- |
| `shape` | `ellipse` |
| `text.horizontal_align` | `center` |
| `text.vertical_align` | `bottom` |
| `text.color` | "#3F3F3F" |
| `fill.color` | "#9DC3E7" |
| `line.color` | "#B1CE46" |
| `line.width` | 1 |

#### Interface

| style 键 | 默认值 |
| --- | --- |
| `shape` | `diamond` |
| `text.horizontal_align` | `center` |
| `text.vertical_align` | `bottom` |
| `text.color` | "#3F3F3F" |
| `fill.color` | "#9DC3E7" |
| `line.color` | "#B1CE46" |
| `line.width` | 1 |

#### Config-db

producer && consumer component 的默认 style:  

| style 键 | 默认值 |
| --- | --- |
| `shape` | `rectangle` |
| `text.horizontal_align` | `center` |
| `text.vertical_align` | `bottom` |
| `text.color` | "#3F3F3F" |
| `fill.color` | "#9DC3E7" |
| `line.color` | "#B1CE46" |
| `line.width` | 1 |

### 2.4 各类型 connection 的 style

#### 表示 TLM 连接关系

component 之间如果使用 TLM 传递 transaction，如 Sequencer, Driver, Monitor, Referencemodel, Scoreboard 之间的连接

规定 text :

- <producer_type>-<transaction_class>-<Consumer_type>
  - 如 port-axi_transaction-export

规定 style:

| style 键 | 默认值 |
| --- | --- |
| `routing` | `right-angle` |
| `color` | "#9DC3E7" |
| `width` | 1 |
| `begin` | `square` |
| `end` | `circle` |

#### 表示 Config_db 连接关系

规定 text :

- <type>
  - 如 axi_if

规定 style:

| style 键 | 默认值 |
| --- | --- |
| `routing` | `right-angle` |
| `color` | "#9DC3E7" |
| `width` | 1 |
| `begin` | `none` |
| `end` | `block-arrow` |