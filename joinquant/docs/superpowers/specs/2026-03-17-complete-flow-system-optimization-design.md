# complete_flow_system.py 优化设计文档

**日期：** 2026-03-17
**文件：** `strategies/trend/complete_flow_system.py`
**目标：** 提升年化收益率，回撤控制在20%以内

---

## 背景与问题诊断

当前策略（v3）采用10步完整交易流程，针对17支ETF做周度选股。主要问题：

1. **趋势门槛过严**：`trend_threshold=0.01` 要求短均线比长均线高1%，震荡期（flat）的ETF全部被排除，错失大量行情
2. **信号逻辑太窄**：强信号（20日突破）和弱信号（MA多头+RSI健康区）是二元判断，满足条件的ETF数量有限，且无法区分信号强弱
3. **仓位固定**：无论市场处于牛市还是熊市，`max_positions` 固定为2，熊市期间缺乏保护

---

## 优化方案：方案二（动量评分排名 + 大盘分档控仓）

### Part 1：市场环境分档（新增 `get_market_regime`）

**函数签名：** `get_market_regime() -> (int, float)`，返回 `(max_open_positions, regime_factor)`

- `max_open_positions`：本次可**同时持有**的最大头寸数（即 `g.max_positions` 的动态版本）
- `regime_factor`：仓位上限缩放系数，乘到每个槽位的 `slot_cap` 上

以沪深300（`000300.XSHG`）MA60 为基准：

| 档位 | 判断条件 | max_open_positions | regime_factor |
|------|---------|-------------------|--------------|
| 牛市 | 沪深300收盘 > MA60 且偏差 > +2% | 2 | 1.00 |
| 震荡 | 沪深300收盘 在 MA60 ±2% 以内 | 1 | 0.70 |
| 熊市 | 沪深300收盘 < MA60 且偏差 < -2% | 1 | 0.40 |

- 数据来源：`attribute_history('000300.XSHG', 65, '1d', ['close'])`（65条保证MA60可计算）
- **fallback**：若 `len(data) < 60`（数据不足以计算MA60，如回测起始期），默认返回震荡档 `(1, 0.70)`
- `get_market_regime()` 在 `rebalance()` 开头调用（仅依赖市场数据，与持仓无关），`regime_factor` 透传到后续所有开仓和加仓计算
- `g.max_positions` 保持固定值 `2`，仅用于 `calc_trade_value()` 的 `slot_cap` 计算基准，不随大盘变化

**`rebalance()` 执行顺序：**
```
1. max_open_positions, regime_factor = get_market_regime()   ← 在此获取市场环境
2. for sec in positions: check_exit_one(...)                 ← 先执行平仓
3. open_slots = max_open_positions - len(positions)          ← 平仓后再计算剩余槽位
4. if open_slots <= 0: return
5. 扫描候选 → 开仓
6. Step 10 加仓
```

**平台注意：** JoinQuant 中 `order_target(sec, 0)` 发出后，`context.portfolio.positions` 在**同一次 `rebalance` 执行内**不会立即移除该持仓（订单当日收盘成交后才更新）。因此步骤3的 `len(positions)` 仍包含刚发出平仓指令的标的，`open_slots` 可能被低估。**接受此限制**：这与原策略行为完全一致，在 `max_open_positions=1` 的熊市档中，同一 bar 内发生出场后不会立即开新仓，需等到下一周才能补仓。这是保守行为，对降低熊市风险是有利的。

**仓位暴露示例（`g.max_positions=2` 固定作为 slot_cap 分母）：**
- 牛市：最多2仓 × `(portfolio/2 × 0.95 × 1.00)` ≈ 95%
- 熊市：最多1仓 × `(portfolio/2 × 0.95 × 0.40)` ≈ 19%

### Part 2：动量评分系统（新增 `calc_momentum_score`，替代 `get_signal`）

**函数签名：** `calc_momentum_score(prices) -> float`
- `prices`：与现有 `attribute_history` 调用返回格式相同，包含 `['open', 'high', 'low', 'close']` 列
- RSI 计算复用现有 `_calc_rsi()` 辅助函数
- 若数据不足（`len(prices) < g.long_ma + 1`，即 < 61 条，或 RSI 为 NaN），返回 `0.0`（此阈值保证 MA60 斜率子项可正确计算；`g.breakout_days=20` 的需求被此条件覆盖）
- 返回值：0.0～100.0 的浮点数（各子项独立上限之和恰好为100，无需额外 clamp）

对每个ETF计算综合动量得分，取代原有强/弱二元信号：

| 子项 | 计算公式 | 上限 |
|------|---------|------|
| 突破强度 | `min(max((当前价 - 20日最高) / 20日最高, 0) / 0.05, 1.0) * 40` | 40分 |
| RSI强度 | 见下方条件公式 | 30分 |
| 均线斜率 | `min(max((短均线 - 长均线) / 长均线, 0) / 0.03, 1.0) * 30` | 30分 |

**RSI强度完整条件公式：**
```python
rsi_score = max((rsi - 45) / 25, 0) * 30  if rsi <= 70  else 0.0
```
- RSI < 45：`max(负数, 0) * 30 = 0`
- RSI 45～70：线性映射，45→0分，70→30分
- RSI > 70（过热）：强制为 0.0，避免追高（有意设计，非遗漏）

**突破强度说明：**
- "20日最高"使用 `high.iloc[-g.breakout_days-1:-1].max()`（与原 `get_signal` 一致，引用 `g.breakout_days` 变量而非硬编码20）
- 未突破20日高点时 `max(负数, 0) = 0`，自然归零

**入场门槛：** 综合得分 ≥ 30分进入候选
**排序：** 每周按评分降序，取前 `open_slots` 名（平仓后剩余槽位数）

### Part 3：趋势过滤 & 参数调整

**趋势判断放宽（修改位置：`rebalance()` 中的新开仓扫描循环和Step10加仓循环，`get_trend()` 函数本身不变）：**

| 位置 | 原过滤条件 | 新过滤条件 |
|------|-----------|----------|
| 新开仓扫描循环（Step 08） | `if trend != 'up': continue` | `if trend == 'down': continue` |
| 加仓循环（Step 10） | `if get_trend(prices) != 'up': continue` | `if get_trend(prices) == 'down': continue` |

震荡期（`flat`）的ETF在新开仓和加仓时均可参与，两处对称处理。

**参数变更：**

| 参数 | 原值 | 新值 | 原因 |
|------|------|------|------|
| `trend_threshold` | `0.01` | `0.003` | 降低趋势判断阈值，震荡期更易被识别为 flat 而非 down |
| `profit_trigger` | `0.05` | `0.03` | 更早启动跟踪止盈，更快锁定利润 |

---

## 改动范围汇总

| 位置 | 改动类型 | 描述 |
|------|---------|------|
| `rebalance()` 开头 | 修改 | 调用 `get_market_regime()` 获取 `(max_open_positions, regime_factor)` |
| `rebalance()` 平仓后 | 修改 | `open_slots = max_open_positions - len(context.portfolio.positions)`（平仓后执行） |
| `rebalance()` 新开仓扫描循环 | 修改 | 趋势过滤从 `trend != 'up'` 改为 `trend == 'down'` |
| `rebalance()` 新开仓扫描循环 | 修改 | 调用 `calc_momentum_score()` 替代 `get_signal()`，按得分 ≥ 30 筛选并降序排列 |
| `rebalance()` 开仓调用 | 修改 | `calc_trade_value()` 增加 `regime_factor` 参数 |
| `rebalance()` Step 10 加仓 | 修改 | 趋势过滤从 `!= 'up'` 改为 `== 'down'`；`get_signal()` 改为 `calc_momentum_score(prices) >= 30` |
| `rebalance()` Step 10 加仓仓位 | 修改 | 删除原内联公式，改为：`target_val = calc_trade_value(portfolio_value, current, stop_price, regime_factor)`（返回值为目标槽位价值）；`add_val = max(0, target_val - pos_val)`（增量 = 目标槽位 − 当前持仓价值，防止超配）；调用 `order_target_value(sec, pos_val + add_val)`，统一受 `risk_pct` 和 `regime_factor` 约束 |
| `calc_trade_value()` | 修改 | 新签名：`calc_trade_value(portfolio_value, entry_price, stop_price, regime_factor=1.0)`；`slot_cap = portfolio_value / g.max_positions * 0.95 * regime_factor` |
| `initialize()` | 修改 | `trend_threshold=0.003`，`profit_trigger=0.03`；`g.max_positions` 保持 `2`（slot_cap 计算基准，不随大盘变化） |
| `get_signal()` | 废弃删除 | 由 `calc_momentum_score()` 完全替代 |
| 新增 `get_market_regime()` | 新增 | 大盘环境分档，返回 `(max_open_positions: int, regime_factor: float)` |
| 新增 `calc_momentum_score()` | 新增 | 三分项动量评分，复用 `_calc_rsi()` 和 `g.breakout_days`，返回 0.0～100.0 |

---

## 不变的部分

- ETF池（17支）
- 周度调仓频率
- `get_trend()` 函数内部逻辑
- `_calc_rsi()` 辅助函数
- `get_support()` 函数
- 止损计算逻辑（`calc_stop`、`_get_atr`）
- 出场逻辑（`check_exit_one`）
- `fixed_stop_pct=0.08`
- `g.max_positions = 2`（固定，仅用作 slot_cap 分母基准）
- `g.breakout_days = 20`（被 `calc_momentum_score` 继续引用）

---

## 预期效果

- **信号数量增加**：趋势放宽 + 评分制替代二元判断，每周候选ETF数量预计从0～2个提升到2～5个
- **收益率提升**：牛市/震荡期充分参与行情，动量高分ETF优先持有
- **熊市保护**：`max_open_positions=1` + `regime_factor=0.40`，最大资金暴露约为 `portfolio × 0.95 × 0.40 / 2 ≈ 19%`，约为牛市正常水平（95%）的20%
