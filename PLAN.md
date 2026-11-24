# OptionsELI Development Plan

## Product principles

- Research and education only; never submit or route orders.
- Never silently substitute synthetic data for market data.
- Display source, retrieval time, freshness, and known limitations.
- Permit an empty result set when no spread meets the selected rules.
- Keep scores explainable and never describe them as probabilities.
- Store credentials only in environment variables, never in source control.

## Architecture

```text
app.py                         Streamlit entry point and navigation
optionseli/
  config.py                    Defaults, ticker universe, environment config
  models.py                    Typed option/spread data models
  demo_data.py                 Deterministic, explicitly synthetic datasets
  market_data.py               Yahoo market-data adapter and freshness metadata
  tradier.py                   Official Tradier sandbox/production read-only client
  indicators.py                Technical indicator calculations
  spreads.py                   Credit-spread construction, filters, payoff math
  scoring.py                   Transparent 0-100 component scoring
  database.py                  SQLite journal storage and analytics
  backtest.py                  Look-ahead-safe underlying-data testing framework
tests/                         Unit tests for calculations and persistence
```

The UI calls provider adapters, which return data plus source metadata. The options
engine accepts normalized option-chain rows, so it is testable independently of
Tradier. SQLite is used only for the local journal in this release.

## Phase 1 — working local release (implemented here)

- Dark professional Streamlit dashboard with Market Overview, Stock Scanner,
  Options Scanner, Trade Journal, and Testing Lab pages.
- Market overview for SPY, QQQ, IWM, and VIX with trends and volatility.
- Configurable 50-symbol liquid US stock/ETF scanner.
- RSI, MACD, 20/50/200-day averages, ATR, relative volume, support/resistance,
  and intraday VWAP when intraday bars are available.
- Read-only Tradier API client, sandbox-first, with environment credentials.
- Deterministic demonstration mode with prominent synthetic-data labels.
- Put and call credit spread construction using same-expiration option legs.
- User-adjustable delta, credit, loss, width, liquidity, expiration, and earnings
  exclusion controls.
- Midpoint and conservative natural-price estimates, payoff graph, risk metrics,
  transparent scoring, setup rationale, risks, and invalidation conditions.
- Local journal with realized P/L, win rate, average return, and drawdown.
- Honest historical-testing scaffold based on underlying signals only; it does not
  invent historical option chains or claim option-strategy performance.
- Tests, README, dependency list, and environment template.

## Phase 2 — data completeness and workflow

- Add a low-cost earnings-calendar provider or user-imported earnings calendar.
- Persist scan snapshots and watchlists.
- Add long calls, long puts, iron condors, and debit spreads.
- Add model-estimated Greeks as an opt-in feature, always labeled separately.
- Improve economic calendar integration after choosing a reliable source.
- Add CSV import/export for Robinhood trade history.

## Phase 3 — research depth

- Store legally obtained historical option-chain snapshots prospectively.
- Backtest spreads only once actual historical chain snapshots exist.
- Add walk-forward validation, regime analysis, portfolio correlation limits,
  assignment simulations, and richer transaction-cost models.
- Add alerting without any order execution.

## Verification gates

1. Unit tests validate spread payoff math, filters, indicators, and journal metrics.
2. Demo mode launches without credentials or network access.
3. Tradier failures remain visible and never fall back to synthetic data silently.
4. Every displayed dataset includes source and timestamp metadata.
5. A zero-result scan is treated as a valid outcome.
