from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from .models import SpreadCandidate


def _valid_quote(value: object) -> bool:
    return pd.notna(value) and float(value) >= 0


def build_credit_spreads(
    chain: pd.DataFrame,
    symbol: str,
    strategy: str,
    delta_min: float = 0.10,
    delta_max: float = 0.15,
    target_credit: float = 1.00,
    credit_tolerance: float = 0.75,
    max_loss_min: float = 300,
    max_loss_max: float = 500,
    widths: tuple[float, ...] = (5.0,),
    max_bid_ask: float = 0.50,
    min_open_interest: int = 100,
    transaction_cost: float = 2.60,
) -> list[SpreadCandidate]:
    """Construct same-expiration vertical credit spreads from quoted contracts."""
    if chain.empty or strategy not in {"put_credit", "call_credit"}:
        return []
    option_type = "put" if strategy == "put_credit" else "call"
    subset = chain[chain["option_type"].str.lower() == option_type].copy()
    results: list[SpreadCandidate] = []
    for expiration, group in subset.groupby("expiration"):
        group = group.sort_values("strike")
        for _, short in group.iterrows():
            if any(not _valid_quote(short.get(k)) for k in ("bid", "ask")):
                continue
            delta = short.get("delta")
            if pd.isna(delta) or not (delta_min <= abs(float(delta)) <= delta_max):
                continue
            if float(short["ask"]) - float(short["bid"]) > max_bid_ask or int(short.get("open_interest", 0)) < min_open_interest:
                continue
            for width in widths:
                long_strike = float(short["strike"]) - width if strategy == "put_credit" else float(short["strike"]) + width
                matches = group[np.isclose(group["strike"].astype(float), long_strike)]
                if matches.empty:
                    continue
                long = matches.iloc[0]
                if any(not _valid_quote(long.get(k)) for k in ("bid", "ask")):
                    continue
                if float(long["ask"]) - float(long["bid"]) > max_bid_ask or int(long.get("open_interest", 0)) < min_open_interest:
                    continue
                midpoint = ((float(short["bid"]) + float(short["ask"])) / 2) - ((float(long["bid"]) + float(long["ask"])) / 2)
                conservative = float(short["bid"]) - float(long["ask"])
                if midpoint <= 0 or conservative <= 0 or abs(midpoint - target_credit) > credit_tolerance:
                    continue
                max_profit = max(0.0, midpoint * 100 - transaction_cost)
                max_loss = width * 100 - midpoint * 100 + transaction_cost
                if not (max_loss_min <= max_loss <= max_loss_max):
                    continue
                breakeven = float(short["strike"]) - midpoint if strategy == "put_credit" else float(short["strike"]) + midpoint
                results.append(SpreadCandidate(
                    symbol=symbol.upper(), strategy=strategy, expiration=pd.Timestamp(expiration).date(),
                    short_strike=float(short["strike"]), long_strike=long_strike, width=width,
                    short_bid=float(short["bid"]), short_ask=float(short["ask"]), long_bid=float(long["bid"]), long_ask=float(long["ask"]),
                    short_delta=float(delta), open_interest=min(int(short.get("open_interest", 0)), int(long.get("open_interest", 0))),
                    midpoint_credit=round(midpoint, 2), conservative_credit=round(conservative, 2),
                    max_profit=round(max_profit, 2), max_loss=round(max_loss, 2), breakeven=round(breakeven, 2),
                    return_on_risk=round(max_profit / max_loss * 100, 2),
                    bid_ask_width=round((float(short["ask"]) - float(short["bid"])) + (float(long["ask"]) - float(long["bid"])), 2),
                    transaction_cost=round(transaction_cost, 2),
                    estimated_otm_probability=round(max(0.0, min(100.0, (1 - abs(float(delta))) * 100)), 1),
                ))
    return results


def payoff_at_expiration(candidate: SpreadCandidate, prices: np.ndarray) -> np.ndarray:
    credit = candidate.midpoint_credit * 100
    if candidate.strategy == "put_credit":
        short = -np.maximum(candidate.short_strike - prices, 0) * 100
        long = np.maximum(candidate.long_strike - prices, 0) * 100
    else:
        short = -np.maximum(prices - candidate.short_strike, 0) * 100
        long = np.maximum(prices - candidate.long_strike, 0) * 100
    return short + long + credit
