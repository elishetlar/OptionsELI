from datetime import date, datetime, timezone

import pandas as pd

from optionseli.tradier import TradierClient, chain_data_is_stale


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_quote_uses_close_when_market_has_no_last(monkeypatch):
    client = TradierClient("not-a-real-token")
    monkeypatch.setattr(client.session, "get", lambda *args, **kwargs: FakeResponse({"quotes": {"quote": {"symbol": "SPY", "last": None, "close": 600.25}}}))
    quote = client.quote("spy")
    assert quote["latest"] == 600.25
    assert quote["symbol"] == "SPY"


def test_chain_request_is_read_only_get(monkeypatch):
    client = TradierClient("not-a-real-token")
    calls = []
    monkeypatch.setattr(client.session, "get", lambda url, params, timeout: (calls.append((url, params)) or FakeResponse({"options": {"option": []}})))
    chain, _ = client.option_chain("SPY", date(2030, 1, 18))
    assert chain.empty
    assert calls[0][0].endswith("/markets/options/chains")


def test_history_parses_actual_provider_candles(monkeypatch):
    client = TradierClient("not-a-real-token", "https://api.tradier.com/v1")
    payload = {"history": {"day": [
        {"date": "2026-11-23", "open": 600, "high": 604, "low": 598, "close": 603, "volume": 1234},
        {"date": "2026-11-24", "open": 603, "high": 608, "low": 602, "close": 607, "volume": 2345},
    ]}}
    monkeypatch.setattr(client.session, "get", lambda *args, **kwargs: FakeResponse(payload))
    frame, meta = client.history("SPY", date(2026, 11, 23), date(2026, 11, 24))
    assert list(frame.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert frame.iloc[-1]["Close"] == 607
    assert meta.source == "Official Tradier API"
    assert meta.observed_at.startswith("2026-11-24")
    assert not meta.is_synthetic


def test_chain_preserves_greeks_and_provider_timestamp(monkeypatch):
    client = TradierClient("not-a-real-token", "https://api.tradier.com/v1")
    timestamp_ms = 1_795_630_200_000
    payload = {"options": {"option": {
        "option_type": "put", "strike": 600, "bid": 1.2, "ask": 1.3,
        "bid_date": timestamp_ms, "open_interest": 400, "volume": 20,
        "greeks": {"delta": -0.12, "gamma": 0.02, "theta": -0.08, "vega": 0.1, "rho": -0.04, "mid_iv": 0.22},
    }}}
    monkeypatch.setattr(client.session, "get", lambda *args, **kwargs: FakeResponse(payload))
    chain, meta = client.option_chain("SPY", date(2026, 12, 18))
    assert chain.iloc[0]["delta"] == -0.12
    assert chain.iloc[0]["mid_iv"] == 0.22
    assert pd.notna(chain.iloc[0]["quote_timestamp"])
    assert meta.observed_at


def test_chain_freshness_fails_closed_and_accepts_recent_quotes():
    now = datetime(2026, 11, 25, 15, 0, tzinfo=timezone.utc)
    assert chain_data_is_stale(pd.DataFrame())
    assert chain_data_is_stale(pd.DataFrame({"quote_timestamp": [None]}), now)
    fresh = pd.DataFrame({"quote_timestamp": ["2026-11-25T14:55:00+00:00"]})
    stale = pd.DataFrame({"quote_timestamp": ["2026-11-25T13:00:00+00:00"]})
    assert not chain_data_is_stale(fresh, now)
    assert chain_data_is_stale(stale, now)
