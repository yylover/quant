# complete_flow_system.py 优化 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 优化 `strategies/trend/complete_flow_system.py`，通过动量评分系统替代二元信号、大盘分档控仓，提升年化收益率，同时将最大回撤控制在20%以内。

**Architecture:** 在保持原有10步交易框架不变的前提下，新增两个纯函数（`get_market_regime`、`calc_momentum_score`），修改 `calc_trade_value` 签名加入 `regime_factor`，更新 `rebalance` 整合新逻辑，删除已废弃的 `get_signal`。

**Tech Stack:** Python 3.x，JoinQuant 平台 API（`attribute_history`, `order_target_value`, `run_weekly` 等），pandas，无外部依赖。

---

## 文件结构

| 文件 | 操作 | 说明 |
|------|------|------|
| `strategies/trend/complete_flow_system.py` | 修改 | 唯一改动文件，所有变更集中于此 |

---

## Chunk 1：参数更新 + 新增纯函数

---

### Task 1：更新 `initialize()` 参数

**Files:**
- Modify: `strategies/trend/complete_flow_system.py:71-98`

**背景：** `trend_threshold` 从 `0.01` 降至 `0.003`，让均线偏差在 ±0.3% 以内的 ETF 被判为震荡（flat），而非空头（down）。`profit_trigger` 从 `0.05` 降至 `0.03`，更早启动跟踪止盈。

- [ ] **Step 1：修改 `trend_threshold`**

  在 `initialize()` 中找到：
  ```python
  g.trend_threshold = 0.01  # 均线偏差阈值
  ```
  改为：
  ```python
  g.trend_threshold = 0.003  # 均线偏差阈值（降低，震荡期也可参与）
  ```

- [ ] **Step 2：修改 `profit_trigger`**

  找到：
  ```python
  g.profit_trigger = 0.05   # 达到5%浮盈后才启动跟踪止盈
  ```
  改为：
  ```python
  g.profit_trigger = 0.03   # 达到3%浮盈后启动跟踪止盈（更早锁利）
  ```

- [ ] **Step 3：更新 `g.max_positions` 注释**

  找到 `initialize()` 中：
  ```python
  g.max_positions = 2       # 最多同时持有2个ETF
  ```
  更新注释以反映新含义（`max_positions` 不再直接控制最大持仓数，而是作为 slot_cap 计算基准）：
  ```python
  g.max_positions = 2       # slot_cap 计算基准（固定为2，不随大盘变化；实际持仓数由 get_market_regime() 动态决定）
  ```

- [ ] **Step 4：Commit**

  ```bash
  git add strategies/trend/complete_flow_system.py
  git commit -m "feat: 降低趋势阈值 trend_threshold=0.003, profit_trigger=0.03"
  ```

---

### Task 2：新增 `get_market_regime()` 函数

**Files:**
- Modify: `strategies/trend/complete_flow_system.py`（在 `get_trend()` 函数结束之后、`get_support()` 函数之前插入）

**背景：** 以沪深300 MA60 为基准，返回 `(max_open_positions, regime_factor)` 控制本周最多开几个仓以及每个仓的资金上限系数。

- [ ] **Step 1：在 `get_trend()` 函数结束后，插入以下新函数**

  ```python
  # ======================================================
  # 市场环境分档（大盘过滤）
  # ======================================================
  def get_market_regime():
      """
      以沪深300（000300.XSHG）MA60 为基准，判断市场环境。
      返回 (max_open_positions, regime_factor)：
        牛市（偏差 > +2%）：(2, 1.00)
        震荡（偏差 ±2%）  ：(1, 0.70)
        熊市（偏差 < -2%）：(1, 0.40)
      fallback（数据不足）：(1, 0.70)
      """
      data = attribute_history('000300.XSHG', 65, '1d', ['close'])
      if data is None or len(data) < 60:
          return 1, 0.70  # 数据不足，默认震荡档

      close = data['close']
      current = close.iloc[-1]
      ma60 = close.iloc[-60:].mean()

      if ma60 <= 0:
          return 1, 0.70

      diff = (current - ma60) / ma60
      if diff > 0.02:
          return 2, 1.00   # 牛市
      elif diff < -0.02:
          return 1, 0.40   # 熊市
      else:
          return 1, 0.70   # 震荡
  ```

- [ ] **Step 2：代码检查**

  确认：
  - fallback 条件使用 `len(data) < 60`（MA60 需要60条）
  - `diff > 0.02` 对应牛市，`diff < -0.02` 对应熊市，中间为震荡
  - 返回值类型为 `(int, float)`

- [ ] **Step 3：Commit**

  ```bash
  git add strategies/trend/complete_flow_system.py
  git commit -m "feat: 新增 get_market_regime() 大盘环境分档函数"
  ```

---

### Task 3：新增 `calc_momentum_score()` 函数

**Files:**
- Modify: `strategies/trend/complete_flow_system.py`（在 `get_signal()` 函数之前插入；Task 5 会删除 `get_signal()`）

**背景：** 对每个 ETF 计算 0～100 的综合动量评分，三个子项：突破强度（40分）+ RSI强度（30分）+ 均线斜率（30分）。

- [ ] **Step 1：在 `get_signal()` 函数之前插入以下新函数**

  ```python
  # ======================================================
  # 动量评分（替代二元信号）
  # ======================================================
  def calc_momentum_score(prices):
      """
      综合动量评分，返回 0.0～100.0。
      数据不足（< g.long_ma + 1 条）或 RSI 为 NaN 时返回 0.0。

      子项（各自独立上限，三项之和最大为100）：
        突破强度（40分）：收盘突破近 g.breakout_days 日高点的幅度，5%→满分
        RSI强度  （30分）：RSI 在 45～70 线性映射；RSI > 70 强制为 0
        均线斜率  （30分）：短均线高于长均线的偏差，3%→满分；负偏差为 0
      """
      close = prices['close']
      high  = prices['high']

      if len(close) < g.long_ma + 1:
          return 0.0

      current = close.iloc[-1]

      # --- 突破强度 ---
      recent_high = high.iloc[-g.breakout_days - 1:-1].max()
      if recent_high > 0:
          breakout_ratio = (current - recent_high) / recent_high
          breakout_score = min(max(breakout_ratio, 0) / 0.05, 1.0) * 40
      else:
          breakout_score = 0.0

      # --- RSI强度 ---
      rsi_series = _calc_rsi(close, g.rsi_period)
      rsi = rsi_series.iloc[-1]
      if rsi != rsi:  # NaN check
          return 0.0
      if rsi <= 70:
          rsi_score = max((rsi - 45) / 25, 0) * 30
      else:
          rsi_score = 0.0  # 过热，避免追高

      # --- 均线斜率 ---
      ma_short = close.iloc[-g.short_ma:].mean()
      ma_long  = close.iloc[-g.long_ma:].mean()
      if ma_long > 0:
          slope_ratio = (ma_short - ma_long) / ma_long
          slope_score = min(max(slope_ratio, 0) / 0.03, 1.0) * 30
      else:
          slope_score = 0.0

      return breakout_score + rsi_score + slope_score
  ```

- [ ] **Step 2：代码检查**

  确认以下关键点：
  - 数据长度守卫：`len(close) < g.long_ma + 1`（< 61 条返回 0.0）
  - 突破窗口：`high.iloc[-g.breakout_days - 1:-1].max()` 不含当日，与原 `get_signal` 一致
  - RSI NaN 检查：`if rsi != rsi` 等价于 `if math.isnan(rsi)`（纯 Python 浮点NaN检测）
  - RSI > 70 强制为 0.0（有意设计，非遗漏）
  - 三项之和理论最大值 = 40 + 30 + 30 = 100.0，无需额外 clamp

- [ ] **Step 3：Commit**

  ```bash
  git add strategies/trend/complete_flow_system.py
  git commit -m "feat: 新增 calc_momentum_score() 三分项动量评分函数"
  ```

---

## Chunk 2：修改现有函数 + 整合 `rebalance()`

---

### Task 4：更新 `calc_trade_value()` 签名

**Files:**
- Modify: `strategies/trend/complete_flow_system.py:223-230`

**背景：** 增加 `regime_factor` 参数，`slot_cap` 乘以该系数，使熊市/震荡期每个槽位的资金上限相应收缩。

- [ ] **Step 1：找到当前 `calc_trade_value` 定义**

  当前代码（约第223行）：
  ```python
  def calc_trade_value(portfolio_value, entry_price, stop_price):
      if entry_price <= stop_price or entry_price <= 0:
          return 0
      slot_cap    = portfolio_value / g.max_positions * 0.95
      risk_amount = portfolio_value * g.risk_pct
      risk_share  = entry_price - stop_price
      value       = (risk_amount / risk_share) * entry_price
      return min(value, slot_cap)
  ```

- [ ] **Step 2：替换为新签名版本**

  ```python
  def calc_trade_value(portfolio_value, entry_price, stop_price, regime_factor=1.0):
      if entry_price <= stop_price or entry_price <= 0:
          return 0
      slot_cap    = portfolio_value / g.max_positions * 0.95 * regime_factor
      risk_amount = portfolio_value * g.risk_pct
      risk_share  = entry_price - stop_price
      value       = (risk_amount / risk_share) * entry_price
      return min(value, slot_cap)
  ```

  关键变化：
  - 函数签名增加 `regime_factor=1.0`（默认值1.0保持向后兼容，现有调用不需改参数即可工作）
  - `slot_cap` 计算末尾乘以 `regime_factor`

- [ ] **Step 3：代码检查**

  确认 `g.max_positions`（固定为2）在分母中，`regime_factor` 在分子方向缩放，数值关系：
  - 牛市 `regime_factor=1.0`：slot_cap = portfolio × 0.95 / 2 ≈ 47.5%
  - 震荡 `regime_factor=0.70`：slot_cap = portfolio × 0.95 × 0.70 / 2 ≈ 33.25%
  - 熊市 `regime_factor=0.40`：slot_cap = portfolio × 0.95 × 0.40 / 2 ≈ 19%

- [ ] **Step 4：Commit**

  ```bash
  git add strategies/trend/complete_flow_system.py
  git commit -m "feat: calc_trade_value 增加 regime_factor 参数支持动态仓位缩放"
  ```

---

### Task 5：重写 `rebalance()` 整合所有新逻辑

**Files:**
- Modify: `strategies/trend/complete_flow_system.py`（`rebalance()` 函数全部替换；因前置任务插入了新函数，实际行号会偏移，以函数名定位而非行号）

**背景：** 这是最核心的改动。按照 spec 中的执行顺序，整合 `get_market_regime()`、新趋势过滤、`calc_momentum_score()` 排序候选、Step 10 加仓更新。

- [ ] **Step 1：用以下完整代码替换 `rebalance()` 函数**

  ```python
  # ======================================================
  # 主调仓逻辑（每周一执行）
  # ======================================================
  def rebalance(context):
      need = max(g.long_ma, g.rsi_period, g.atr_period, g.breakout_days) + 5

      # -------- 市场环境分档 --------
      max_open_positions, regime_factor = get_market_regime()
      log.info('[市场环境] max_open_positions={} regime_factor={:.0%}'.format(
          max_open_positions, regime_factor))

      # -------- 09 平仓优先 --------
      for sec in list(context.portfolio.positions.keys()):
          prices = attribute_history(sec, need, '1d', ['open', 'high', 'low', 'close'])
          if prices is None or len(prices) < need:
              continue
          check_exit_one(context, sec, prices)

      # -------- 检查剩余开仓容量 --------
      # 注意：JoinQuant 平仓订单在当日收盘后才结算，此处 len(positions) 仍含刚发出平仓的标的
      # 这是平台限制，行为与原策略一致，熊市档下属于保守处理（接受）
      open_slots = max_open_positions - len(context.portfolio.positions)
      if open_slots <= 0:
          return

      # -------- 扫描 ETF 池，收集满足条件的候选标的 --------
      # 结构：(score, security, entry_price, stop_price)
      candidates = []

      for sec in g.etf_pool:
          if sec in context.portfolio.positions:
              continue  # 已持有，跳过

          prices = attribute_history(sec, need, '1d', ['open', 'high', 'low', 'close'])
          if prices is None or len(prices) < need:
              continue

          # 01 辨趋势（放宽：只排除明确空头，震荡期也可参与）
          trend = get_trend(prices)
          if trend == 'down':
              continue

          # 动量评分（替代原有强/弱二元信号）
          score = calc_momentum_score(prices)
          if score < 30:
              continue  # 分数不足，跳过

          entry_price = prices['close'].iloc[-1]

          # 03 找位置（支撑）
          support = get_support(prices, trend)

          # 05 定止损
          stop_price = calc_stop(entry_price, support, prices)

          # 07 看空间
          if not check_space(entry_price, stop_price, prices):
              continue

          candidates.append((score, sec, entry_price, stop_price))

      if not candidates:
          return

      # 按评分降序排列，取前 open_slots 名
      candidates.sort(key=lambda x: x[0], reverse=True)
      portfolio_value = context.portfolio.portfolio_value

      for score, sec, entry_price, stop_price in candidates[:open_slots]:
          # 06 定仓位（传入 regime_factor）
          trade_val = calc_trade_value(portfolio_value, entry_price, stop_price, regime_factor)
          if trade_val <= 0:
              continue
          avail = context.portfolio.available_cash * 0.95
          if trade_val > avail:
              trade_val = avail
          if trade_val <= 0:
              continue

          # 08 开仓
          order_target_value(sec, trade_val)
          g.state[sec] = {
              'stop':      stop_price,
              'highest':   entry_price,
              'add_count': 0,
          }
          log.info('[开仓] {} 得分={:.1f} 入场={:.3f} 止损={:.3f} 风险={:.1%} 环境系数={:.0%}'.format(
              sec, score, entry_price, stop_price,
              (entry_price - stop_price) / entry_price,
              regime_factor
          ))

      # -------- 10 加仓：浮盈且再次满足买点 --------
      for sec in list(context.portfolio.positions.keys()):
          state = g.state.get(sec)
          if not state or state.get('add_count', 0) >= g.max_add_times:
              continue
          position = context.portfolio.positions.get(sec)
          if not position or position.total_amount <= 0:
              continue

          current = context.portfolio.positions[sec].price
          if current <= position.avg_cost * 1.03:  # 至少浮盈3%才考虑加仓
              continue

          prices = attribute_history(sec, need, '1d', ['open', 'high', 'low', 'close'])
          if prices is None or len(prices) < need:
              continue

          # 趋势过滤（与新开仓对称：只排除明确空头）
          if get_trend(prices) == 'down':
              continue
          # 信号过滤（评分 >= 30）
          if calc_momentum_score(prices) < 30:
              continue

          support    = get_support(prices, 'up')
          stop_price = calc_stop(current, support, prices)

          # 加仓量 = 目标槽位价值 − 当前持仓价值（防止超配）
          pos_val    = position.value
          target_val = calc_trade_value(portfolio_value, current, stop_price, regime_factor)
          add_val    = max(0, target_val - pos_val)
          avail      = context.portfolio.available_cash * 0.95
          add_val    = min(add_val, avail)
          if add_val <= 0:
              continue

          order_target_value(sec, pos_val + add_val)
          state['add_count'] = state.get('add_count', 0) + 1
          log.info('[加仓] {} 浮盈={:.1%} 加仓量={:.0f}'.format(
              sec, (current - position.avg_cost) / position.avg_cost, add_val))
  ```

- [ ] **Step 2：代码检查核对清单**

  逐项确认：
  - `get_market_regime()` 在函数开头第一行调用 ✓
  - 平仓循环在 `open_slots` 计算之前 ✓
  - 趋势过滤改为 `trend == 'down'` 跳过（非 `trend != 'up'`）✓
  - `calc_momentum_score(prices)` 调用替代原 `get_signal(prices)` ✓
  - 候选排序改为 `reverse=True`（得分降序）✓
  - `calc_trade_value` 调用传入 `regime_factor` ✓
  - Step 10 加仓趋势过滤改为 `== 'down'` ✓
  - Step 10 加仓信号改为 `calc_momentum_score(prices) < 30` ✓
  - Step 10 加仓使用 `target_val - pos_val` 计算增量（防超配）✓
  - 开仓 log 新增 `score` 和 `regime_factor` 字段 ✓

- [ ] **Step 3：Commit**

  ```bash
  git add strategies/trend/complete_flow_system.py
  git commit -m "feat: rebalance() 整合市场环境分档、动量评分排序、加仓逻辑更新"
  ```

---

### Task 6：删除废弃的 `get_signal()` 函数

**Files:**
- Modify: `strategies/trend/complete_flow_system.py`

**背景：** `get_signal()` 已被 `calc_momentum_score()` 完全替代，在 `rebalance()` 中不再被调用，需删除避免混淆。

- [ ] **Step 1：确认 `get_signal()` 不再有任何调用**

  全文搜索 `get_signal`，确认只剩函数定义本身，`rebalance()` 中已无调用。

- [ ] **Step 2：只删除 `get_signal()` 函数本身（`_calc_rsi()` 必须保留）**

  在源文件中找到并**只删除** `def get_signal(prices):` 函数（约第156-191行中 `get_signal` 的部分）：
  ```python
  def get_signal(prices):
      """
      ETF 适用信号（替代 K 线形态）：
        强信号：收盘价突破近 N 日最高价（动能突破）
        弱信号：均线多头排列 + RSI 在健康区间且上升
      返回 (has_signal, 'strong'/'weak'/None)
      """
      ...（全部函数体）...
      return False, None
  ```

  **严格注意：`_calc_rsi(close_series, period)` 紧邻 `get_signal` 之前定义，绝对不能删除**。
  `_calc_rsi` 由新增的 `calc_momentum_score()` 继续使用。

  删除后，该区域结构应为：
  ```
  # ======================================================
  # 04 看信号（ETF专用）← 此行注释一并删除（原属于 get_signal 的节头）
  # ======================================================
  def _calc_rsi(close_series, period):   ← 保留
      ...
  # ======================================================
  # 动量评分（替代二元信号）               ← Task 3 已插入的节头
  # ======================================================
  def calc_momentum_score(prices):       ← 保留（Task 3 新增）
      ...
  ```

  具体操作：删除从 `# ======================================================\n# 04 看信号（ETF专用）` 注释块头（紧接在 `_calc_rsi` 定义之上）到 `get_signal()` 函数最后一行 `return False, None` 为止，**不含** `def _calc_rsi` 及其函数体。

  即只删除 `def get_signal(prices):` 到 `return False, None` 这段，保留 `_calc_rsi()`。

- [ ] **Step 3：确认文件结构完整**

  确认文件中以下函数仍存在，顺序合理：
  - `initialize()`
  - `get_trend()`
  - `get_market_regime()`（新增）
  - `get_support()`
  - `_calc_rsi()`（保留）
  - `calc_momentum_score()`（新增，替代 `get_signal`）
  - `_get_atr()`
  - `calc_stop()`
  - `calc_trade_value()`（已修改签名）
  - `check_space()`
  - `check_exit_one()`
  - `rebalance()`（已重写）

- [ ] **Step 4：Commit**

  ```bash
  git add strategies/trend/complete_flow_system.py
  git commit -m "refactor: 删除废弃的 get_signal() 函数"
  ```

---

## Chunk 3：验证

---

### Task 7：代码完整性验证

**Files:**
- Read: `strategies/trend/complete_flow_system.py`

- [ ] **Step 1：检查无遗留 `get_signal` 引用**

  在文件中搜索 `get_signal`，应返回空结果。

- [ ] **Step 2：检查所有 `calc_trade_value` 调用点都传入了 `regime_factor`**

  搜索 `calc_trade_value(`，确认：
  - `rebalance()` 新开仓处：`calc_trade_value(portfolio_value, entry_price, stop_price, regime_factor)` ✓
  - `rebalance()` Step 10 加仓处：`calc_trade_value(portfolio_value, current, stop_price, regime_factor)` ✓
  - 函数签名默认值：`def calc_trade_value(... regime_factor=1.0)` ✓（无其他旧调用）

- [ ] **Step 3：检查参数初始值**

  在 `initialize()` 中确认：
  ```python
  g.trend_threshold = 0.003  # (原 0.01)
  g.profit_trigger  = 0.03   # (原 0.05)
  g.max_positions   = 2      # 不变
  ```

- [ ] **Step 4：Commit（如有任何小修正）**

  ```bash
  git add strategies/trend/complete_flow_system.py
  git commit -m "fix: 代码完整性修正"
  ```

---

### Task 8：提交到 JoinQuant 回测验证

**背景：** 该策略依赖 JoinQuant 平台 API（`attribute_history`、`order_target_value` 等），无法在本地运行单元测试，最终验证需在 JoinQuant 回测环境中进行。

- [ ] **Step 1：将 `strategies/trend/complete_flow_system.py` 完整内容粘贴到 JoinQuant 策略编辑器**

- [ ] **Step 2：设置回测参数**

  建议回测区间：`2018-01-01` ～ `2024-12-31`（涵盖 2018熊市、2020新冠、2021-2022回调、2023反弹）
  初始资金：`100万`

- [ ] **Step 3：对比优化前后的关键指标**

  | 指标 | 优化前（v3）目标 | 优化后（v4）目标 |
  |------|--------------|--------------|
  | 年化收益率 | 基准线 | 明显提升 |
  | 最大回撤 | 基准线 | ≤ 20% |
  | 夏普比率 | 基准线 | ≥ 优化前 |
  | 年交易次数 | ~50次 | 可能增加 |

- [ ] **Step 4：若回测指标符合预期，最终 commit**

  ```bash
  git add strategies/trend/complete_flow_system.py
  git commit -m "feat: complete_flow_system v4 - 动量评分+大盘分档控仓优化"
  ```
