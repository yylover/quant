## ADDED Requirements

### Requirement: Backtest visualization with position and return views
The system MUST generate visual outputs for moving-average backtest results, including at minimum price-with-signals view, position line view, and cumulative return (or net value) view.

#### Scenario: Produce required charts in one run
- **WHEN** user executes backtest visualization workflow with valid result data
- **THEN** system SHALL generate all required chart views without requiring manual post-processing

### Requirement: Price chart overlays strategy context
The system MUST plot price series with moving averages and explicit buy/sell markers so that trading decisions can be visually audited.

#### Scenario: Render buy and sell markers
- **WHEN** backtest includes executed trades
- **THEN** price chart SHALL display buy and sell points aligned to trade timestamps and direction

### Requirement: Position and performance series are time-aligned
The system MUST ensure that position line and return/net value lines are time-aligned with the underlying market data timeline.

#### Scenario: Validate timeline consistency
- **WHEN** plotting position and return-related charts
- **THEN** all plotted series SHALL use a consistent timestamp index and preserve chronological order

### Requirement: Export chart artifacts for reporting
The system MUST support saving generated charts to disk with deterministic naming or user-provided output paths.

#### Scenario: Save charts to output directory
- **WHEN** user specifies an output directory or default output settings
- **THEN** system SHALL persist chart files and report their output locations after execution
