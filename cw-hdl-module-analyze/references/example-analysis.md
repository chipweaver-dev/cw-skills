# 期望输出示例（节选）

以一个参数化 UART 发送器 `uart_tx` 为例，展示三个最见功夫的章节的期望形态。
完整标准以 `references/report-template.md` 为准；本文件仅节选、不可当作模板使用。

## §3.1 端口清单（节选）

| # | 名称 | 方向 | 位宽/公式 | 类型 | 复位值 | 组 | 功能描述 | 依据 |
|---|------|------|-----------|------|--------|----|----------|------|
| 1 | clk | input | 1 | wire | — | A | 系统时钟，上升沿驱动全部时序逻辑 | uart_tx.v:42 |
| 2 | rst_n | input | 1 | wire | — | A | 异步低有效复位，见 §4.2 | uart_tx.v:43 |
| 3 | i_data | input | 8 | wire | — | B | 待发送字节，i_valid 为高的那一拍被采样；期间须保持稳定 [INFERENCE]（无缓存寄存器，uart_tx.v:88） | uart_tx.v:45 |
| 4 | i_valid | input | 1 | wire | — | D | 发送请求；busy 期间忽略新请求 | uart_tx.v:46 |
| 5 | o_tx | output | 1 | reg | 1'b1 | C | 串行输出，空闲态为高 | uart_tx.v:50 |
| 6 | o_done | output | 1 | reg | 1'b0 | C | 停止位发完后拉高一拍 | uart_tx.v:51 |

## §7 状态机（节选）

状态编码（uart_tx.v:60-64，二进制编码）：

| 状态 | 编码 | 含义 | 依据 |
|------|------|------|------|
| IDLE | 2'd0 | 空闲，tx=1，等待 i_valid | uart_tx.v:60 |
| START | 2'd1 | 输出起始位 tx=0 | uart_tx.v:61 |
| DATA | 2'd2 | 逐位移出 8 bit，LSB first | uart_tx.v:62 |
| STOP | 2'd3 | 输出停止位 tx=1，持续一个位周期 | uart_tx.v:63 |

转移表（uart_tx.v:90-118）：

| 当前态 | 触发条件（信号级布尔式） | 次态 | 主要动作/输出 |
|-------|--------------------------|------|----------------|
| IDLE | i_valid == 1'b1 | START | sh_reg <= i_data；baud_cnt <= 0 |
| IDLE | i_valid == 1'b0 | IDLE | 保持 |
| START | baud_cnt == BAUD_DIV-1 | DATA | baud_cnt <= 0；bit_idx <= 0 |
| DATA | baud_cnt == BAUD_DIV-1 && bit_idx == 7 | STOP | 移出最后一位 |
| DATA | baud_cnt == BAUD_DIV-1 && bit_idx < 7 | DATA | bit_idx+1；sh_reg 右移 |
| STOP | baud_cnt == BAUD_DIV-1 | IDLE | o_done <= 1'b1（一拍） |

复位态：IDLE（异步）。Moore 型：tx 与状态推进仅依赖现态与内部计数器。

## §6.1 波特率发生器（节选）

* 对应源码：uart_tx.v:70-78（always @(posedge clk or negedge rst_n)）
* 行为：在 clk 上升沿，rst_n 为低时 baud_cnt 清零；否则当 baud_cnt == BAUD_DIV-1 时清零，
  其余情况自增 1。BAUD_DIV = CLK_FREQ/BAUD（默认 50MHz/115200 ≈ 434）。


## 标注示范（反面示例）

不可接受："DATA 状态会发数据，发完去 STOP 等等。"（模糊、无行号、未给编码）
可接受：见上表——条件为信号级布尔式、状态有编码、动作可执行。
