# OptionsELI

OptionsELI is a local, dark-mode Streamlit research dashboard for market analysis,
liquid-stock scanning, and put/call credit-spread evaluation. It never places orders.

> **Cloud-data note:** The owner has Tradier's permission to use a personal token in
> the private, single-user deployment. Public redistribution remains disabled.

> **Risk warning:** Options can lose the full amount at risk. Credit spreads carry
> early-assignment, expiration/pin, liquidity, gap, data-quality, and correlated-position
> risks. Scores in this application are transparent heuristics—not probabilities of
> profit, recommendations, or financial advice.

## What works in v0.1

- Market overview for SPY, QQQ, IWM, and VIX
- A configurable 50-symbol scanner and core technical indicators
- Official Tradier read-only production quotes, history, expirations, and option chains
- Automatic or manual put/call credit-spread construction with matching expirations
- Bullish/bearish signal scoring, SPY/QQQ/VIX regime filtering, and No Trade outcomes
- Adjustable risk, delta, credit, width, liquidity, and cost filters
- Midpoint and conservative execution estimates, payoff chart, and explainable score
- SQLite trade journal and honest underlying-signal testing scaffold
- Fully local deterministic demo mode (always labeled synthetic)

See `PLAN.md` for architecture, verification gates, and later phases.

## Private cloud deployment

OptionsELI relies on Streamlit Community Cloud private sharing for authenticated
viewer access. Cloud mode removes credential settings, the personal journal, and
SQLite access. See `DEPLOY.md` for private sharing, server-side secrets, and testing.

## Beginner-friendly Mac setup

1. Open **Terminal** (Applications → Utilities → Terminal).
2. Change into this project folder:

   ```bash
   cd "/path/to/OptionsELI"
   ```

3. Confirm Python 3.11+ is available: `python3 --version`. If it is missing, install
   Python from [python.org](https://www.python.org/downloads/macos/).
4. Create an isolated environment and install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. Create your private settings file:

   ```bash
   cp .env.example .env
   ```

   Demo mode works immediately. You can configure Tradier from the dashboard's
   **Settings** page: paste the token into the masked field, test it, and save it.
   OptionsELI stores it only in the Git-ignored local `.env` file with owner-only
   permissions. Manual `.env` configuration remains available if preferred.

6. Start the dashboard:

   ```bash
   streamlit run app.py
   ```

7. Your browser should open automatically. If it does not, visit
   [http://localhost:8501](http://localhost:8501). Stop the app with **Control-C**.

## Run tests

```bash
source .venv/bin/activate
pytest -q
```

## Data behavior

- Demo mode is synthetic, deterministic, and prominently labeled.
- With a Tradier token configured, stock quotes, daily history, expirations, and
  option chains come from the official read-only Tradier API. Yahoo Finance is only
  the local no-token fallback for stock history; it is never used after a Tradier
  live-data failure.
- Production timing depends on the account entitlement and instrument. Provider
  timestamps are displayed; sandbox feeds are delayed.
- Contracts without Greeks are excluded, and model Greeks are not substituted.
- The displayed OTM estimate is `1 − |short delta|`, clearly labeled as a rough
  model-based approximation—not a calibrated probability or guarantee.
- The earnings exclusion blocks individual-stock scans when no verified calendar is
  configured. It never invents earnings dates.
- No economic events are shown until a verified provider is added.
- Historical option performance is not simulated without real historical chains.

## Current limits / next work

Earnings and economic calendars, prospective option-chain storage, additional option
strategies, richer paper-trade lifecycle tracking, and genuine historical options
backtests remain for later phases. No OpenAI key is needed for any core feature.
