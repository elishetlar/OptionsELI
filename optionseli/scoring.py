from __future__ import annotations

from dataclasses import replace

from .models import SpreadCandidate


def score_candidate(candidate: SpreadCandidate, snapshot: dict, iv_rank: float | None = None) -> SpreadCandidate:
    """Explainable heuristic score; explicitly not a probability of profit."""
    expected_trend = "Bullish" if candidate.strategy == "put_credit" else "Bearish"
    trend = 25.0 if snapshot.get("Trend") == expected_trend else 14.0 if snapshot.get("Trend") == "Mixed" else 4.0
    liquidity = min(25.0, 8 + candidate.open_interest / 250)
    technical = 12.0
    support, resistance = snapshot.get("Support"), snapshot.get("Resistance")
    if candidate.strategy == "put_credit" and support is not None and candidate.short_strike < support:
        technical = 20.0
    elif candidate.strategy == "call_credit" and resistance is not None and candidate.short_strike > resistance:
        technical = 20.0
    risk_reward = min(20.0, candidate.return_on_risk / 2)
    volatility = 5.0 if iv_rank is None else min(10.0, max(0.0, iv_rank / 10))
    details = {"Trend alignment": trend, "Liquidity": liquidity, "Technical level": technical, "Risk/reward": risk_reward, "Volatility context": volatility}
    score = round(min(100.0, sum(details.values())), 1)
    reasons = (
        f"Short strike delta is {abs(candidate.short_delta or 0):.2f}",
        f"Return on risk is {candidate.return_on_risk:.1f}% at midpoint",
        f"Underlying trend is {snapshot.get('Trend', 'unavailable')}",
    )
    risks = ("Early assignment", "Expiration and pin risk", "Wide or changing liquidity", "Correlated portfolio exposure")
    level = support if candidate.strategy == "put_credit" else resistance
    invalidation = f"Reassess if price breaks the observed {'support' if candidate.strategy == 'put_credit' else 'resistance'} near {level:.2f}." if level else "Reassess if the technical trend no longer supports the trade."
    return replace(candidate, score=score, score_details=details, reasons=reasons, risks=risks, invalidation=invalidation)
