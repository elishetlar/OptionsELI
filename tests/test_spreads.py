from datetime import date

import numpy as np
import pandas as pd

from optionseli.spreads import build_credit_spreads, payoff_at_expiration


def test_put_credit_math_and_payoff():
    chain = pd.DataFrame([
        {"option_type": "put", "expiration": date(2030, 1, 18), "strike": 100, "bid": 1.50, "ask": 1.60, "delta": -.12, "open_interest": 1000},
        {"option_type": "put", "expiration": date(2030, 1, 18), "strike": 95, "bid": .45, "ask": .55, "delta": -.05, "open_interest": 800},
    ])
    results = build_credit_spreads(chain, "XYZ", "put_credit", target_credit=1.05, credit_tolerance=.1, transaction_cost=0)
    assert len(results) == 1
    spread = results[0]
    assert spread.midpoint_credit == 1.05
    assert spread.max_profit == 105
    assert spread.max_loss == 395
    assert spread.breakeven == 98.95
    assert np.allclose(payoff_at_expiration(spread, np.array([94, 100, 105])), [-395, 105, 105])


def test_missing_greeks_are_excluded():
    chain = pd.DataFrame([{"option_type": "call", "expiration": date(2030, 1, 18), "strike": 100, "bid": 1, "ask": 1.1, "delta": None, "open_interest": 999}])
    assert build_credit_spreads(chain, "XYZ", "call_credit") == []
