---
name: cw-testbench-create
description: >-
  创建一个通用的 UVM/SystemVerilog Testbench 目录框架。
  当用户说「创建 testbench」「新建验证环境」「搭建 TB 框架」「初始化验证环境」
  「新建 tb」「创建 uvm 环境」或任何需要从头搭建验证环境的请求时触发。
  这是一个通用框架，不绑定任何特定项目，生成后可针对具体需求继续填充。
---

# cw-testbench-create：创建 UVM Testbench 目录框架

## 使用场景

用户希望在指定路径下创建一个标准的 UVM/SystemVerilog 验证环境目录结构，作为后续开发的起点。本 skill **只生成目录骨架和必要的占位文件**，不生成具体的验证组件代码。

## 流程

### 1. 收集信息

向用户确认以下信息：

| 信息 | 说明 | 默认值 |
|------|------|--------|
| **TB 名称** | 验证环境的名称，用作顶层目录名 | `uvm_tb` |
| **输出路径** | 在哪个目录下创建 | 用户当前工作目录 |

如果用户已明确给出这些信息，跳过确认直接执行。

### 2. 创建目录结构

在目标路径下创建以下目录结构。所有目录名遵循**小写+下划线**风格（snake_case）。

- `<tb_name>/`
  - `filelist/` — 编译文件列表
    - `dut.f` — DUT 文件列表
    - `tb.f` — Testbench 文件列表
    - `vip.f` — VIP 文件列表（可选）
  - `harness/` — 顶层测试平台
    - `tb_top.sv` — 顶层模块（含 initial/test 启动）
    - `dut_inst.svi` — DUT 所需 wire 例化，DUT 实例化
    - `if_inst.svi` — 接口实例化, 接口 uvm_config_db set 机制
  - `component/` — 验证组件，每个组件必须为对应组件类别下的组件名称独立文件夹
    - `env/` — 验证环境
      - `apb_env/` — APB Environment (可选)
      - `xxx_env/` — TB 顶层 env
    - `agt/` — Agent
      - `xxx_agt/` — Agent (可选)
    - `com/` — 公共组件
      - `clk_gen/` — 时钟复位管理组件
        - `clk_gen_if.v` — 时钟复位管理 Interface
    - `ral/` — 寄存器模型（可选）
      - `xxx_ral/` — RAL package
        - `xxx_ral.sv` — RAL package
  - `testcase/` — 测试用例
    - `tc_base_test.sv` — 仅实现基础功能,用于其他 Test 继承
    - `tc_sanity_test.sv` — 冒烟测试
  - `tool/` — 工具和脚本
    - `makefile/` — Makefile
      - `eda_common.mk` — 定义基础eda工作流，各仿真路径 Makefile include 此 make 文件, 从 references\eda_common.mk 拷贝到 TB
    - `tcl/` — TCL 脚本
      - `run.tcl` — 仿真运行脚本，从 references\run.tcl 拷贝到 TB
  - `workdir/` — 仿真工作目录（运行结果输出到此）
    - `sim_sanity/` — 冒烟测试运行目录
      - `Makefile` — flow 入口，参考 references\Makefile 结合工程环境修改
  - `design/` — RTL 路径（软链接到此）
  - `<tb_name>.md` — 空的 markdown 文件，用于人与ai下一步协同工作

### 3. 创建占位文件

对于 `.sv` / `.svi` 文件，写入最小的占位内容：

- **tb_top.sv** 
  - 包含   initial begin $timeformat(-9, 3, " ns", 10); end block

占位内容遵循的原则：
- 文件能被编译通过（语法正确）
- 组件继承正确的 UVM 基类
- 关键位置留 `// TODO` 标记，引导后续开发

### 4. 输出确认

创建完成后，向用户展示所创建的目录结构概览，并告知：
- 总目录数和文件数
- 关键文件路径
- 下一步可以做什么（如「添加 DUT」「实现 agent」「编写 testcase」等）

## 示例

**用户输入：**
> 创建 testbench，名字叫 ddr3_phy_tb，放在 z:/prj/ddr3_phy/verify/ 下

**Skill 执行：**
1. 创建 `z:/prj/ddr3_phy/verify/ddr3_phy_tb/` 及其全部子目录
2. 在各 `.sv` 文件中写入 UVM 空组件模板
3. 在 `filelist/` 下创建空的 `.f` 文件
4. 在 `tool/makefile/` 下创建 Makefile 骨架
5. 输出目录树

## 注意事项

- 始终使用 `mkdir -p` 创建目录，避免因中间目录不存在而失败
- 路径中可能包含空格，始终对路径变量加引号
- 路径分隔符使用 Unix 风格的正斜杠 `/`
- 如果目标路径已存在同名目录，**提示用户确认是否覆盖**，不要直接覆盖
- 如果用户只需要部分目录（如不需要 RAL），尊重用户选择
- 文件名中的 `xxx` 是占位符，使用时应替换为具体的模块名（如 `ddr3_phy_env.sv`），但需要用户提供模块名
