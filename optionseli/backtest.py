from __future__ import annotations

import pandas as pd

from .indicators import calculate_indicators


def underlying_signal_test(prices: pd.DataFrame, holding_days: int = 10, cost_bps: float = 5.0) -> pd.DataFrame:
    """Test lagged underlying trend signals; does not simulate option returns."""
    data = calculate_indicators(prices)
    data["signal"] = (data["Close"] > data["SMA_50"]).astype(int).shift(1).fillna(0)
    future_return = data["Close"].shift(-holding_days) / data["Close"] - 1
    data["test_return"] = data["signal"] * (future_return - cost_bps / 10_000)
    return data.dropna(subset=["SMA_50", "test_return"])
