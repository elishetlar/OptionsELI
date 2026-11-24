from datetime import date

from optionseli.tradier import TradierClient


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
