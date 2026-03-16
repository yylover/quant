-- MySQL 8.0 schema for quant backtesting system
-- Run these statements in your target database (e.g. `quant`)

-- 1. Instrument master table

CREATE TABLE IF NOT EXISTS instrument (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  symbol       VARCHAR(32) NOT NULL,         -- standardized code, e.g. 512800.SH
  raw_symbol   VARCHAR(32) NOT NULL,         -- original code, e.g. 512800
  exchange     VARCHAR(16) NOT NULL,         -- SSE / SZSE / ...
  name         VARCHAR(64) NULL,
  type         VARCHAR(16) NOT NULL,         -- stock / etf / index / future ...
  list_date    DATE NULL,
  delist_date  DATE NULL,
  currency     VARCHAR(8) NOT NULL DEFAULT 'CNY',
  created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_instrument_symbol (symbol),
  KEY idx_instrument_type_exchange (type, exchange)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- 2. Unified bar table (daily + intraday)

CREATE TABLE IF NOT EXISTS bar (
  id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  instrument_id  BIGINT UNSIGNED NOT NULL,
  `interval`     VARCHAR(8) NOT NULL,         -- '1d', '1m', '5m', ...
  ts             DATETIME NOT NULL,           -- bar start time or daily time
  open_price     DECIMAL(18,4) NOT NULL,
  high_price     DECIMAL(18,4) NOT NULL,
  low_price      DECIMAL(18,4) NOT NULL,
  close_price    DECIMAL(18,4) NOT NULL,
  volume         BIGINT UNSIGNED NULL,
  amount         DECIMAL(20,4) NULL,
  open_interest  DECIMAL(20,4) NULL,
  turnover_rate  DECIMAL(10,4) NULL,
  adjust_factor  DECIMAL(18,8) NULL,
  created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_bar_inst_interval_ts (instrument_id, `interval`, ts),
  KEY idx_bar_inst_interval_ts (instrument_id, `interval`, ts),
  CONSTRAINT fk_bar_instrument
    FOREIGN KEY (instrument_id) REFERENCES instrument(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- 3. Corporate actions (optional)

CREATE TABLE IF NOT EXISTS corporate_action (
  id                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  instrument_id     BIGINT UNSIGNED NOT NULL,
  ex_date           DATE NOT NULL,
  action_type       VARCHAR(32) NOT NULL,      -- dividend / split / bonus ...
  cash_dividend     DECIMAL(18,4) NULL,
  stock_bonus_ratio DECIMAL(10,4) NULL,
  split_ratio       DECIMAL(10,4) NULL,
  description       TEXT NULL,
  created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_ca_inst_exdate (instrument_id, ex_date),
  CONSTRAINT fk_ca_instrument
    FOREIGN KEY (instrument_id) REFERENCES instrument(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- 4. Strategy definition

CREATE TABLE IF NOT EXISTS strategy (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name        VARCHAR(64) NOT NULL,
  category    VARCHAR(32) NOT NULL,
  description TEXT NULL,
  params_json JSON NULL,                       -- stores fast/slow/fees/slippage/etc.
  created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_strategy_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- 5. Backtest runs

CREATE TABLE IF NOT EXISTS backtest_run (
  id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  strategy_id      BIGINT UNSIGNED NOT NULL,
  instrument_id    BIGINT UNSIGNED NULL,        -- can be NULL for portfolio-level runs
  `interval`       VARCHAR(8) NOT NULL,
  start_ts         DATETIME NOT NULL,
  end_ts           DATETIME NOT NULL,
  init_cash        DECIMAL(20,4) NOT NULL,
  fees             DECIMAL(10,6) NOT NULL,
  slippage         DECIMAL(10,6) NOT NULL,
  engine           VARCHAR(32) NOT NULL,        -- vectorbt / backtrader / ...
  status           VARCHAR(16) NOT NULL DEFAULT 'success',
  run_time         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  notes            TEXT NULL,
  -- common metrics (optional, for fast querying)
  total_return_pct DECIMAL(10,4) NULL,
  max_drawdown_pct DECIMAL(10,4) NULL,
  ann_return_pct   DECIMAL(10,4) NULL,
  ann_vol_pct      DECIMAL(10,4) NULL,
  sharpe_ratio     DECIMAL(10,4) NULL,
  PRIMARY KEY (id),
  KEY idx_br_strategy (strategy_id),
  KEY idx_br_inst (instrument_id),
  CONSTRAINT fk_br_strategy
    FOREIGN KEY (strategy_id) REFERENCES strategy(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_br_instrument
    FOREIGN KEY (instrument_id) REFERENCES instrument(id)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- 6. Backtest metrics (optional, for flexible metric storage)

CREATE TABLE IF NOT EXISTS backtest_metric (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  backtest_run_id BIGINT UNSIGNED NOT NULL,
  metric_name     VARCHAR(64) NOT NULL,
  metric_value    DECIMAL(20,8) NOT NULL,
  metric_extra    JSON NULL,
  PRIMARY KEY (id),
  KEY idx_bm_run (backtest_run_id),
  CONSTRAINT fk_bm_backtest_run
    FOREIGN KEY (backtest_run_id) REFERENCES backtest_run(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- 7. Backtest equity curve

CREATE TABLE IF NOT EXISTS backtest_equity (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  backtest_run_id BIGINT UNSIGNED NOT NULL,
  ts              DATETIME NOT NULL,
  equity          DECIMAL(20,4) NOT NULL,
  position_value  DECIMAL(20,4) NULL,
  cash            DECIMAL(20,4) NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_be_run_ts (backtest_run_id, ts),
  KEY idx_be_run (backtest_run_id),
  CONSTRAINT fk_be_backtest_run
    FOREIGN KEY (backtest_run_id) REFERENCES backtest_run(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- 8. Backtest trades

CREATE TABLE IF NOT EXISTS backtest_trade (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  backtest_run_id BIGINT UNSIGNED NOT NULL,
  instrument_id   BIGINT UNSIGNED NOT NULL,
  open_ts         DATETIME NOT NULL,
  close_ts        DATETIME NULL,
  direction       VARCHAR(8) NOT NULL,       -- long / short
  qty             DECIMAL(20,4) NOT NULL,
  open_price      DECIMAL(18,4) NOT NULL,
  close_price     DECIMAL(18,4) NULL,
  pnl             DECIMAL(20,4) NULL,
  fees            DECIMAL(20,4) NULL,
  slippage_cost   DECIMAL(20,4) NULL,
  PRIMARY KEY (id),
  KEY idx_bt_run (backtest_run_id),
  KEY idx_bt_inst (instrument_id),
  CONSTRAINT fk_bt_backtest_run
    FOREIGN KEY (backtest_run_id) REFERENCES backtest_run(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_bt_instrument
    FOREIGN KEY (instrument_id) REFERENCES instrument(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

