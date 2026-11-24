from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Return OHLCV data with standard, backward-looking indicators."""
    if df.empty:
        return df.copy()
    out = df.sort_index().copy()
    close, high, low = out["Close"], out["High"], out["Low"]
    for window in (20, 50, 200):
        out[f"SMA_{window}"] = close.rolling(window, min_periods=window).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rs = gain / loss.replace(0, np.nan)
    out["RSI_14"] = (100 - 100 / (1 + rs)).fillna(100).where(gain.ne(0), 50)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    out["MACD"] = ema12 - ema26
    out["MACD_SIGNAL"] = out["MACD"].ewm(span=9, adjust=False).mean()
    previous_close = close.shift(1)
    true_range = pd.concat(
        [(high - low), (high - previous_close).abs(), (low - previous_close).abs()], axis=1
    ).max(axis=1)
    out["ATR_14"] = true_range.rolling(14, min_periods=14).mean()
    out["REL_VOLUME"] = out["Volume"] / out["Volume"].rolling(20, min_periods=5).mean()
    out["SUPPORT_20"] = low.rolling(20, min_periods=5).min()
    out["RESISTANCE_20"] = high.rolling(20, min_periods=5).max()
    if "Volume" in out and out["Volume"].notna().any():
        typical = (high + low + close) / 3
        session = pd.Series(out.index.date, index=out.index) if isinstance(out.index, pd.DatetimeIndex) else pd.Series(0, index=out.index)
        pv = typical * out["Volume"]
        out["VWAP"] = pv.groupby(session).cumsum() / out["Volume"].groupby(session).cumsum().replace(0, np.nan)
    return out


def latest_snapshot(df: pd.DataFrame) -> dict:
    enriched = calculate_indicators(df)
    if enriched.empty:
        return {}
    row = enriched.iloc[-1]
    close = float(row["Close"])
    sma20 = row.get("SMA_20", np.nan)
    sma50 = row.get("SMA_50", np.nan)
    trend = "Bullish" if close > sma20 > sma50 else "Bearish" if close < sma20 < sma50 else "Mixed"
    return {
        "Price": close,
        "Trend": trend,
        "RSI": row.get("RSI_14"),
        "MACD": row.get("MACD"),
        "SMA20": sma20,
        "SMA50": sma50,
        "SMA200": row.get("SMA_200"),
        "ATR": row.get("ATR_14"),
        "Relative Volume": row.get("REL_VOLUME"),
        "Support": row.get("SUPPORT_20"),
        "Resistance": row.get("RESISTANCE_20"),
    }
