# Testbench Architecture JSON → Archify IR 映射规范

> 本文件定义 cw-testbench-analyze Phase 1 输出的中间 Json（见 `testbench_architecture_json_spec.md`）到 **archify architecture IR** 的转换规则。Phase 2 **必须按本规范转换**，并通过 archify CLI 校验后交付。
>
> archify 的完整 schema 见 archify skill 目录下 `schemas/architecture.schema.json` 与 `schemas/common.schema.json`；渲染行为以 archify 自己的 SKILL.md 为准。
>
> **替代路径**：默认按本规范由本 skill 完成 IR 转换（确定性、可 diff）；仅在**用户明确要求**时，可改为把中间 Json 直接交给 archify skill 全流程渲染（archify agent 读拓扑语义后自行创作 IR）。archify 没有自动转换命令，其 agent 只承诺理解自然语言与 Mermaid 输入，对私有格式的语义解读不可复现，故此路径为例外而非默认。

---

## 1. archify IR 结构要点

```Json
{
    "schema_version": 1,               // 固定值
    "diagram_type": "architecture",    // 固定值
    "meta": { "title": "<必填>", "...": "见第 4 节" },
    "components": [ { "id": "...", "type": "...", "label": "...", "...": "" } ],
    "boundaries": [ { "kind": "region", "label": "...", "wraps": ["<id>"] } ],
    "connections": [ { "from": "<id>", "to": "<id>", "label": "...", "variant": "..." } ]
}
```

硬性约束（schema 校验会拒绝违规输出）：

- `id` 必须匹配 `^[a-zA-Z][a-zA-Z0-9_-]*$`——**不允许 `.`、`[`、`]`、中文**等字符
- `component.type` 只能是：`frontend` / `backend` / `database` / `cloud` / `security` / `messagebus` / `external`
- `connection.variant` 只能是：`default` / `emphasis` / `security` / `dashed`
- 中间格式的 `style`（颜色/形状/端点符号）在 archify 中**没有对应字段**，一律丢弃，由 archify 的主题接管

## 2. 组件映射

### 2.1 层级展平

中间格式是嵌套 component 树，archify 是**扁平 components[] + boundaries[] 包裹**：

- 递归展开所有 component 为 components[]，每个组件一条
- `id` 由 `hierarchy` 路径生成：层级分隔符 `.` 替换为 `_`（如 `tb_top.env.u_apb_agt` → `tb_top_env_u_apb_agt`）；过长时可手工起短 id，但必须保证全局唯一且符合 id 正则
- **environment 层不作为节点**，转为 `boundaries[]`：`{ "kind": "region", "label": "<env name>", "wraps": [<该 env 直接管辖的子组件 id>] }`；嵌套 env 生成多层 boundary。tb_top 若只是顶层容器，可省略为最外层 boundary 或不表达
- `label` 取 `name`，`sublabel` 取 `class`；中间格式的 `text` 字段丢弃（archify 自行渲染 label + sublabel）

### 2.2 type 语义映射

按 UVM 角色映射到 archify 的 7 种语义类型（**语义映射，不是 1:1 换色**）：

| 中间格式 type | archify type | 说明 |
| --- | --- | --- |
| `test` | `external` | 激励来源，位于被画系统之外 |
| `testbench` | `backend` | TB 顶层容器/逻辑 |
| `environment` | （转 boundary，见 2.1） | env 用区域包裹表达 |
| `agent` | `backend` | agent 及其内部 |
| `sequencer` | `messagebus` | transaction 通道 |
| `driver` / `monitor` | `backend` | 行为侧组件 |
| `referencemodel` / `scoreboard` | `security` | checker 语义（archify 惯例：校验类组件用 security） |
| `object` | 默认**不转节点**，仅以 connection label 体现；用户要求展示时用 `messagebus` | 避免 uvm_object 淹没主结构 |
| `interface` | `external` | TB 与 DUT 之间的边界实体 |
| DUT / Dram 等 design 侧实体 | `backend`（核心）/ `external`（行为模型） | 按是否属验证环境判断 |

### 2.3 节点规模控制

archify 建议**最多 12 个主节点**。默认**折叠 agent 内部**（sqr/drv/mon 收进 agent 一个节点）；仅当用户明确要求细节且节点预算允许时展开。仍超限时按 diagram 拆成多个 IR 文件分别渲染。

## 3. 连接映射

| 中间格式 connection | archify connection | 规则 |
| --- | --- | --- |
| TLM 连接 | `{ "from", "to", "label": "<text>", "variant": "emphasis" }` | 主数据流用 `emphasis`；次要 TLM 连接可用 `default` |
| config-db 连接 | `{ "from", "to", "label": "<text>", "variant": "dashed" }` | set 端为 `from`，get 端为 `to` |
| `text` | `label` | 原样保留 |
| `style.routing` | 默认**不写**（auto） | 仅自动路由明显不佳时用 `straight` / `orthogonal-h` / `orthogonal-v`；**禁止 `via` / `labelAt`**（archify 要求诊断后才允许加） |
| `style.begin` / `end` | 无对应字段 | 丢弃 |
| `style.color` / `width` | 无对应（`width` 除外） | 丢弃；原 `width` ≥ 2 的连接可写 `width: 2` |

注意：中间格式的连接可能写在任一祖先层级（见 JSON 规范 2.2），转换时统一提升为扁平 connections[]，`from`/`to` 按连接键名引用的组件解析为对应 `id`。同一对组件的多条连接在 IR 中是**多条数组元素**，无键名冲突问题。

## 4. meta 与布局

| archify 字段 | 取值 |
| --- | --- |
| `meta.title` | diagram 的 `name`（缺省用 tb_name） |
| `meta.subtitle` | diagram 的 `description` |
| `meta.locale` | `"zh-CN"`（用户要求英文时改 `en`） |
| `meta.output` | 目标 html 路径 |
| `meta.quality_profile` | `"showcase"`（用户明确要 dense 时才用 `"standard"`） |
| `layout` / `pos` / `row` / `col` | 首个候选**不做精细坐标规划**，遵循 archify 的快速授权路径；但必须落实中间格式的 `layout.max_column`（见 JSON 规范 2.5）：diagram 的 `max_column` 写入 IR 顶层 `"layout": { "mode": "grid", "cols": N }`（archify 限 1–12）；environment / agent 的 `max_column` 作为该 boundary 内组件 `row` / `col` 排布的列数上限（超出换行） |

不使用的字段：`meta.repository` / `engineering_profile` / `views` / `legend` / `cards`——除非用户要求，否则不写。

## 5. 校验与交付（Phase 2 必须执行）

archify CLI 位于 archify skill 目录（`~/.claude/skills/archify/` 或工程 `.claude/skills/archify/`），用 `node` 执行：

```bash
ARCHIFY=~/.claude/skills/archify   # 按实际安装位置调整

# 1. 校验 IR 候选
node $ARCHIFY/bin/archify.mjs validate architecture <candidate.json> --quality showcase --json

# 2. 校验通过后生成交付物
node $ARCHIFY/bin/archify.mjs deliver architecture <candidate.json> <output.html> --quality showcase --json
```

- showcase 通过标准：**9 项 artifact checks 全部通过、0 composition errors、0 warnings**；只有 4 项基础检查算 basic，不算通过
- validate 失败时按诊断的 `subject` / `supportedFixes` 定点修复后重跑；连续两轮无改善则如实报告未解决项，不得谎报成功
- validate 通过后**冻结候选**，不再修改 IR；交付以 `deliver` 退出码 0 为准
