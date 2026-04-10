## ADDED Requirements

### Requirement: Parameterized moving-average strategy backtest
The system MUST support backtesting a moving-average crossover strategy with configurable short window, long window, initial capital, commission, slippage, and execution lag settings.

#### Scenario: Run backtest with valid parameters
- **WHEN** user provides price time series and valid strategy parameters
- **THEN** system SHALL complete the backtest and return structured outputs including signals, positions, period returns, cumulative net value, and trade records

### Requirement: Deterministic signal and position generation
The system MUST generate deterministic buy/sell/hold signals from short/long moving-average crossover rules and convert signals to positions without look-ahead bias.

#### Scenario: Golden-cross generates long position
- **WHEN** short moving average crosses above long moving average under configured rules
- **THEN** system SHALL create a buy signal and apply long position from the configured execution point

#### Scenario: Death-cross exits position
- **WHEN** short moving average crosses below long moving average under configured rules
- **THEN** system SHALL create a sell signal and reduce position according to the configured position model

### Requirement: Backtest metrics and exportable results
The system MUST compute core performance metrics and support exporting key backtest outputs for downstream analysis.

#### Scenario: Generate performance summary
- **WHEN** backtest execution is finished
- **THEN** system SHALL output total return, annualized return, max drawdown, volatility, and Sharpe ratio (or project-defined equivalent metrics)

#### Scenario: Persist result artifacts
- **WHEN** user enables result export
- **THEN** system SHALL write at least one machine-readable result file containing timestamps, positions, returns, and cumulative net value
