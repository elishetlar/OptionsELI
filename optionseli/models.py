from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class DataMeta:
    source: str
    retrieved_at: str
    is_synthetic: bool = False
    is_delayed: bool = False
    note: str = ""


@dataclass(frozen=True)
class SpreadCandidate:
    symbol: str
    strategy: str
    expiration: date
    short_strike: float
    long_strike: float
    width: float
    short_bid: float
    short_ask: float
    long_bid: float
    long_ask: float
    short_delta: float | None
    open_interest: int
    midpoint_credit: float
    conservative_credit: float
    max_profit: float
    max_loss: float
    breakeven: float
    return_on_risk: float
    score: float = 0.0
    score_details: dict[str, float] = field(default_factory=dict)
    reasons: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    invalidation: str = ""
    bid_ask_width: float = 0.0
    transaction_cost: float = 0.0
    technical_distance: float | None = None
    technical_distance_atr: float | None = None
    technical_level: str = ""
