import numpy as np
import pandas as pd

from optionseli.indicators import calculate_indicators


def test_indicators_have_expected_columns_and_no_future_dependency():
    idx = pd.bdate_range("2024-01-01", periods=220)
    base = pd.DataFrame({"Open": np.arange(220)+100, "High": np.arange(220)+102, "Low": np.arange(220)+98, "Close": np.arange(220)+101, "Volume": 1000}, index=idx)
    first = calculate_indicators(base)
    changed = base.copy(); changed.iloc[-1, changed.columns.get_loc("Close")] = 9999
    second = calculate_indicators(changed)
    assert {"RSI_14", "MACD", "SMA_200", "ATR_14", "REL_VOLUME", "VWAP"}.issubset(first.columns)
    pd.testing.assert_series_equal(first.iloc[-2], second.iloc[-2])
