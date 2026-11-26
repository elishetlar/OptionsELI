from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from math import isfinite

import pandas as pd

from .indicators import calculate_indicators, latest_snapshot
from .models import DataMeta


@dataclass(frozen=True)
class SignalAssessment:
    classification: str
    bullish_score: float
    bearish_score: float
    components: tuple[str, ...]
    unavailable: tuple[str, ...] = ()
    stale: bool = False


@dataclass(frozen=True)
class MarketRegime:
    classification: str
    bullish_score: float
    bearish_score: float
    volatility: str
    explanations: tuple[str, ...]
    stale: bool = False


@dataclass(frozen=True)
class StrategyDecision:
    classification: str
    preferred_strategy: str | None
    reasons: tuple[str, ...]


def _number(value: object) -> float | None:
    try:
        result = float(value)
        return result if isfinite(result) else None
    except (TypeError, ValueError):
        return None


def data_is_stale(df: pd.DataFrame, meta: DataMeta | None = None, max_market_days: int = 5) -> bool:
    """Identify old observations without treating normal delayed/sandbox data as stale."""
    if df.empty or not isinstance(df.index, pd.DatetimeIndex):
        return True
    latest = pd.Timestamp(df.index[-1])
    if latest.tzinfo is not None:
        latest = latest.tz_convert("UTC").tz_localize(None)
    today = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
    if len(pd.bdate_range(latest.normalize(), today)) - 1 > max_market_days:
        return True
    if meta and meta.retrieved_at:
        try:
            retrieved = datetime.fromisoformat(meta.retrieved_at.replace("Z", "+00:00"))
            if retrieved.tzinfo is None:
                retrieved = retrieved.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - retrieved).total_seconds() > 24 * 3600:
                return True
        except ValueError:
            return True
    return False


def assess_trend(df: pd.DataFrame, meta: DataMeta | None = None, intraday: bool = False) -> SignalAssessment:
    """Return transparent directional evidence scores, never a probability."""
    snap = latest_snapshot(df)
    if not snap:
        return SignalAssessment("No Trade", 0, 0, ("Price history is unavailable.",), stale=True)

    bull = bear = 0.0
    notes: list[str] = []
    unavailable: list[str] = []
    price = _number(snap.get("Price"))

    rsi = _number(snap.get("RSI"))
    if rsi is None:
        unavailable.append("RSI")
    elif rsi >= 55:
        bull += 12; notes.append(f"RSI {rsi:.1f} is above 55 (+12 bullish).")
    elif rsi <= 45:
        bear += 12; notes.append(f"RSI {rsi:.1f} is below 45 (+12 bearish).")
    else:
        bull += 4; bear += 4; notes.append(f"RSI {rsi:.1f} is neutral (+4 each direction).")

    enriched = calculate_indicators(df)
    row = enriched.iloc[-1]
    macd, macd_signal = _number(row.get("MACD")), _number(row.get("MACD_SIGNAL"))
    if macd is None or macd_signal is None:
        unavailable.append("MACD")
    elif macd > macd_signal:
        bull += 14; notes.append("MACD is above its signal line (+14 bullish).")
    elif macd < macd_signal:
        bear += 14; notes.append("MACD is below its signal line (+14 bearish).")
    else:
        bull += 3; bear += 3; notes.append("MACD equals its signal line (+3 each direction).")

    for label, weight in (("SMA20", 10), ("SMA50", 12), ("SMA200", 16)):
        average = _number(snap.get(label))
        if price is None or average is None:
            unavailable.append(label)
        elif price > average:
            bull += weight; notes.append(f"Price is above {label} (+{weight} bullish).")
        elif price < average:
            bear += weight; notes.append(f"Price is below {label} (+{weight} bearish).")

    support, resistance = _number(snap.get("Support")), _number(snap.get("Resistance"))
    atr = _number(snap.get("ATR"))
    if price is None or support is None or resistance is None or not atr:
        unavailable.append("support/resistance context")
    else:
        support_room = (price - support) / atr
        resistance_room = (resistance - price) / atr
        if support_room > resistance_room:
            bull += 10; notes.append("Price has more ATR-normalized room above support than below resistance (+10 bullish).")
        elif resistance_room > support_room:
            bear += 10; notes.append("Price has more ATR-normalized room below resistance than above support (+10 bearish).")
        else:
            bull += 3; bear += 3

    if intraday:
        vwap = _number(row.get("VWAP"))
        if price is None or vwap is None:
            unavailable.append("intraday VWAP")
        elif price > vwap:
            bull += 12; notes.append("Price is above valid intraday VWAP (+12 bullish).")
        elif price < vwap:
            bear += 12; notes.append("Price is below valid intraday VWAP (+12 bearish).")
    else:
        unavailable.append("intraday VWAP (daily history supplied)")

    # Normalize against the evidence that was actually available.
    available_max = 74 + (12 if intraday and "intraday VWAP" not in unavailable else 0)
    bullish = round(min(100.0, bull / available_max * 100), 1)
    bearish = round(min(100.0, bear / available_max * 100), 1)
    stale = data_is_stale(df, meta)
    if stale:
        classification = "No Trade"
        notes.append("The latest price observation is stale; directional use is blocked.")
    elif bullish >= 55 and bullish - bearish >= 15:
        classification = "Bullish"
    elif bearish >= 55 and bearish - bullish >= 15:
        classification = "Bearish"
    else:
        classification = "Neutral"
    return SignalAssessment(classification, bullish, bearish, tuple(notes), tuple(unavailable), stale)


def assess_market_regime(
    spy: SignalAssessment,
    qqq: SignalAssessment,
    vix_history: pd.DataFrame | None,
    vix_meta: DataMeta | None = None,
) -> MarketRegime:
    notes: list[str] = []
    bull = (spy.bullish_score + qqq.bullish_score) / 2
    bear = (spy.bearish_score + qqq.bearish_score) / 2
    stale = spy.stale or qqq.stale
    volatility = "Unavailable"
    if vix_history is None or vix_history.empty:
        notes.append("Volatility regime is unavailable; no VIX observation was supplied.")
    else:
        stale = stale or data_is_stale(vix_history, vix_meta)
        close = float(vix_history["Close"].iloc[-1])
        mean20 = float(vix_history["Close"].tail(20).mean())
        if close >= 25 or close > mean20 * 1.10:
            volatility = "Elevated"
            bear += 10; bull = max(0, bull - 10)
            notes.append(f"VIX is elevated at {close:.1f} versus its 20-session mean {mean20:.1f}.")
        elif close <= 18 and close <= mean20 * 1.05:
            volatility = "Contained"
            bull += 8
            notes.append(f"VIX is contained at {close:.1f} versus its 20-session mean {mean20:.1f}.")
        else:
            volatility = "Normal"
            notes.append(f"VIX is in a middle regime at {close:.1f}; 20-session mean is {mean20:.1f}.")
    bull, bear = round(min(100, bull), 1), round(min(100, bear), 1)
    if stale:
        classification = "Stale / No Trade"
    elif bull >= 55 and bull - bear >= 12:
        classification = "Bullish"
    elif bear >= 55 and bear - bull >= 12:
        classification = "Bearish"
    else:
        classification = "Neutral"
    notes.insert(0, f"SPY is {spy.classification}; QQQ is {qqq.classification}.")
    return MarketRegime(classification, bull, bear, volatility, tuple(notes), stale)


def choose_strategy(signal: SignalAssessment, regime: MarketRegime) -> StrategyDecision:
    if signal.stale or regime.stale:
        return StrategyDecision("No Trade", None, ("Price or regime data is stale.",))
    if signal.classification == "Bullish" and regime.classification in {"Bullish", "Neutral"}:
        return StrategyDecision("Put credit spread", "put_credit", ("Underlying evidence is bullish.", f"Market regime is {regime.classification.lower()}."))
    if signal.classification == "Bearish" and regime.classification in {"Bearish", "Neutral"}:
        return StrategyDecision("Call credit spread", "call_credit", ("Underlying evidence is bearish.", f"Market regime is {regime.classification.lower()}."))
    return StrategyDecision("No Trade", None, (f"Underlying signal is {signal.classification.lower()} while the market regime is {regime.classification.lower()}.", "Directional evidence conflicts or is too weak."))
