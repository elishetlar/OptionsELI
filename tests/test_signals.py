from datetime import datetime, timezone

import numpy as np
import pandas as pd

from optionseli.models import DataMeta
from optionseli.signals import MarketRegime, assess_trend, choose_strategy, data_is_stale


def price_history(direction: int = 1, end=None) -> pd.DataFrame:
    idx = pd.bdate_range(end=end or pd.Timestamp.today().normalize(), periods=260)
    close = np.linspace(100, 200, len(idx)) if direction > 0 else np.linspace(200, 100, len(idx))
    return pd.DataFrame({
        "Open": close, "High": close + 1, "Low": close - 1,
        "Close": close, "Volume": np.linspace(1_000_000, 2_000_000, len(idx)),
    }, index=idx)


def current_meta() -> DataMeta:
    return DataMeta("test", datetime.now(timezone.utc).isoformat())


def test_automatic_strategy_selects_put_for_aligned_bullish_conditions():
    signal = assess_trend(price_history(1), current_meta())
    regime = MarketRegime("Bullish", 80, 10, "Contained", ("test",))
    decision = choose_strategy(signal, regime)
    assert signal.classification == "Bullish"
    assert decision.preferred_strategy == "put_credit"


def test_automatic_strategy_selects_call_for_aligned_bearish_conditions():
    signal = assess_trend(price_history(-1), current_meta())
    regime = MarketRegime("Bearish", 10, 80, "Elevated", ("test",))
    assert choose_strategy(signal, regime).preferred_strategy == "call_credit"


def test_conflicting_regime_returns_no_trade():
    signal = assess_trend(price_history(1), current_meta())
    regime = MarketRegime("Bearish", 10, 80, "Elevated", ("test",))
    decision = choose_strategy(signal, regime)
    assert decision.classification == "No Trade"
    assert decision.preferred_strategy is None


def test_stale_history_blocks_strategy_selection():
    old = price_history(1, end="2020-01-31")
    assert data_is_stale(old, current_meta())
    signal = assess_trend(old, current_meta())
    regime = MarketRegime("Bullish", 80, 10, "Contained", ("test",))
    assert signal.classification == "No Trade"
    assert choose_strategy(signal, regime).preferred_strategy is None


def test_daily_history_explicitly_marks_vwap_unavailable():
    signal = assess_trend(price_history(1), current_meta())
    assert any("VWAP" in item for item in signal.unavailable)
