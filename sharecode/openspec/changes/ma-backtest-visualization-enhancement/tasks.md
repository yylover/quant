## 1. Data and strategy foundation

- [ ] 1.1 Define and validate unified input schema for backtest data (timestamp, close price, optional volume/metadata).
- [ ] 1.2 Implement moving-average signal generator with configurable short/long windows and crossover rules.
- [ ] 1.3 Add execution timing control (e.g., next-bar execution) to avoid look-ahead bias.

## 2. Backtest engine and metrics

- [ ] 2.1 Implement position transition logic from signals, including entry/exit and flat state handling.
- [ ] 2.2 Implement return and net value calculation with configurable commission/slippage assumptions.
- [ ] 2.3 Generate trade ledger and summary metrics (total return, annualized return, drawdown, volatility, Sharpe).
- [ ] 2.4 Add export of machine-readable results (CSV/structured table) for positions, returns, net value, and trades.

## 3. Visualization outputs

- [ ] 3.1 Implement price chart with short/long moving averages and buy/sell markers.
- [ ] 3.2 Implement position-line chart aligned to the same trading timeline.
- [ ] 3.3 Implement cumulative return (or net value) chart aligned to the same trading timeline.
- [ ] 3.4 Add deterministic chart output naming and configurable output directory support.

## 4. Entry point and validation

- [ ] 4.1 Provide a single script/CLI entry to run backtest + plotting in one command.
- [ ] 4.2 Add parameter validation and friendly error messages for invalid windows, missing fields, or empty data.
- [ ] 4.3 Ensure execution summary prints output file locations and key performance metrics.

## 5. Verification and documentation

- [ ] 5.1 Add/extend tests for signal generation, position alignment, and return computation.
- [ ] 5.2 Add/extend tests for visualization timeline consistency and chart artifact generation.
- [ ] 5.3 Update usage documentation with examples for running MA backtest and reading generated charts.
