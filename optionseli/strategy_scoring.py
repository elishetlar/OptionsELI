from __future__ import annotations

from dataclasses import replace

from .models import SpreadCandidate
from .signals import MarketRegime, SignalAssessment


def score_candidate_with_context(
    candidate: SpreadCandidate,
    snapshot: dict,
    signal: SignalAssessment,
    regime: MarketRegime,
) -> SpreadCandidate:
    """Rank spread quality transparently; this score is not a probability."""
    directional = signal.bullish_score if candidate.strategy == "put_credit" else signal.bearish_score
    regime_direction = regime.bullish_score if candidate.strategy == "put_credit" else regime.bearish_score
    trend = min(30.0, directional * 0.30)
    regime_points = min(15.0, regime_direction * 0.15)
    liquidity = min(20.0, candidate.open_interest / 100.0) + max(0.0, 5.0 - candidate.bid_ask_width * 5)
    liquidity = min(25.0, liquidity)
    risk_reward = min(15.0, max(0.0, candidate.return_on_risk * 0.75))

    level_name = "support" if candidate.strategy == "put_credit" else "resistance"
    level = snapshot.get("Support") if candidate.strategy == "put_credit" else snapshot.get("Resistance")
    atr = snapshot.get("ATR")
    distance = None
    distance_atr = None
    technical = 4.0
    if level is not None:
        distance = float(level) - candidate.short_strike if candidate.strategy == "put_credit" else candidate.short_strike - float(level)
        if atr is not None and float(atr) > 0:
            distance_atr = distance / float(atr)
        technical = 15.0 if distance > 0 else max(0.0, 7.0 + distance * 2)

    details = {
        "Directional alignment": round(trend, 1),
        "Market regime": round(regime_points, 1),
        "Liquidity": round(liquidity, 1),
        "Technical strike placement": round(technical, 1),
        "Risk/reward": round(risk_reward, 1),
    }
    score = round(min(100.0, sum(details.values())), 1)
    direction_word = "bullish" if candidate.strategy == "put_credit" else "bearish"
    placement = (
        f"The short strike is ${abs(distance):.2f} {'beyond' if distance >= 0 else 'inside'} nearby {level_name}"
        + (f" ({distance_atr:.2f} ATR)." if distance_atr is not None else ".")
        if distance is not None else f"Verified {level_name} placement is unavailable."
    )
    reasons = (
        f"The {direction_word} signal score is {directional:.1f}/100 and the regime is {regime.classification.lower()}.",
        placement,
        f"Midpoint credit is ${candidate.midpoint_credit:.2f}; conservative executable estimate is ${candidate.conservative_credit:.2f}.",
        f"Return on risk is {candidate.return_on_risk:.1f}% after ${candidate.transaction_cost:.2f} estimated transaction costs.",
    )
    risks = (
        "Early assignment, especially around ex-dividend dates or deep in-the-money contracts",
        "Expiration and pin risk near either strike",
        "Bid-ask liquidity can deteriorate and actual fills may be worse than both estimates",
        "Correlated positions can concentrate portfolio losses",
        f"A move through nearby {level_name} would weaken the technical premise",
    )
    invalidation = (
        f"Reassess if the underlying closes through observed {level_name} near {float(level):.2f}, "
        f"the {direction_word} signal loses alignment, volatility changes sharply, or quotes become stale/illiquid."
        if level is not None else
        "Reassess if directional alignment weakens, volatility changes sharply, or quotes become stale/illiquid."
    )
    return replace(
        candidate, score=score, score_details=details, reasons=reasons, risks=risks,
        invalidation=invalidation, technical_distance=distance,
        technical_distance_atr=distance_atr, technical_level=level_name,
    )
