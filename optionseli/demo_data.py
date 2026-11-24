from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from .models import DataMeta


def demo_prices(symbol: str, periods: int = 260) -> tuple[pd.DataFrame, DataMeta]:
    seed = sum(ord(c) for c in symbol) + 2025
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=periods)
    start = 80 + seed % 350
    returns = rng.normal(0.00035, 0.014, periods)
    close = start * np.exp(np.cumsum(returns))
    open_ = close * (1 + rng.normal(0, 0.003, periods))
    high = np.maximum(open_, close) * (1 + rng.uniform(0.001, 0.012, periods))
    low = np.minimum(open_, close) * (1 - rng.uniform(0.001, 0.012, periods))
    volume = rng.integers(8_000_000, 80_000_000, periods)
    df = pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}, index=idx)
    meta = DataMeta("OptionsELI deterministic demonstration generator", pd.Timestamp.now(tz="UTC").isoformat(), True, False, "Not market data")
    return df, meta


def demo_option_chain(symbol: str, spot: float) -> tuple[pd.DataFrame, DataMeta]:
    rng = np.random.default_rng(sum(ord(c) for c in symbol) + 99)
    rows = []
    for dte in (21, 30, 45):
        expiration = date.today() + timedelta(days=dte)
        step = 1 if spot < 100 else 5
        center = round(spot / step) * step
        for option_type in ("put", "call"):
            for strike in np.arange(center - 8 * step, center + 9 * step, step):
                distance = (strike - spot) / (spot * np.sqrt(dte / 365))
                if option_type == "put":
                    delta = -max(0.03, min(0.90, 0.50 + distance * 0.55))
                    intrinsic = max(strike - spot, 0)
                else:
                    delta = max(0.03, min(0.90, 0.50 - distance * 0.55))
                    intrinsic = max(spot - strike, 0)
                time_value = max(0.08, spot * 0.025 * np.exp(-abs(distance) * 1.7) * np.sqrt(dte / 30))
                mid = intrinsic + time_value
                spread = max(0.04, min(0.35, mid * 0.12))
                rows.append({
                    "symbol": symbol, "expiration": expiration, "option_type": option_type,
                    "strike": float(strike), "bid": round(max(0.01, mid - spread / 2), 2),
                    "ask": round(mid + spread / 2, 2), "delta": round(delta, 3),
                    "open_interest": int(rng.integers(150, 6000)), "volume": int(rng.integers(10, 1500)),
                })
    meta = DataMeta("OptionsELI deterministic demonstration generator", pd.Timestamp.now(tz="UTC").isoformat(), True, False, "Synthetic chain; never use for trading")
    return pd.DataFrame(rows), meta
