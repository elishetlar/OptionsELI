from __future__ import annotations

import pandas as pd

from .models import DataMeta


def yahoo_history(symbol: str, period: str = "1y", interval: str = "1d") -> tuple[pd.DataFrame, DataMeta]:
    import yfinance as yf

    ticker = "^VIX" if symbol.upper() == "VIX" else symbol.upper()
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=False, progress=False, threads=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if df.empty:
        raise RuntimeError(f"No Yahoo Finance data returned for {symbol}")
    retrieved = pd.Timestamp.now(tz="UTC").isoformat()
    latest = pd.Timestamp(df.index[-1])
    delayed = interval != "1d" or (pd.Timestamp.now(tz="UTC").tz_localize(None) - latest.tz_localize(None)).days > 2
    return df, DataMeta("Yahoo Finance via yfinance (unofficial, research use)", retrieved, False, delayed, "May be delayed and cached for up to 15 minutes; verify independently")
