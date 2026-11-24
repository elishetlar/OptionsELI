from __future__ import annotations

from datetime import date

import pandas as pd
import requests

from .models import DataMeta


class TradierError(RuntimeError):
    pass


class TradierClient:
    """Read-only client for official Tradier market-data endpoints."""

    def __init__(self, token: str, base_url: str = "https://sandbox.tradier.com/v1", timeout: int = 15):
        if not token:
            raise TradierError("TRADIER_API_TOKEN is not configured")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}", "Accept": "application/json"})

    def _get(self, path: str, params: dict | None = None) -> dict:
        try:
            response = self.session.get(f"{self.base_url}{path}", params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            raise TradierError(f"Tradier request failed: {exc}") from exc

    def expirations(self, symbol: str) -> list[date]:
        payload = self._get("/markets/options/expirations", {"symbol": symbol, "includeAllRoots": "true", "strikes": "false"})
        raw = payload.get("expirations", {}).get("date", [])
        if isinstance(raw, str):
            raw = [raw]
        return [date.fromisoformat(item) for item in raw]

    def test_connection(self) -> dict:
        """Validate credentials with a harmless read-only market-clock request."""
        payload = self._get("/markets/clock")
        clock = payload.get("clock") or {}
        if not clock:
            raise TradierError("Tradier responded, but no market-clock data was returned")
        return {
            "state": clock.get("state", "unknown"),
            "description": clock.get("description", "Connection authenticated"),
            "next_change": clock.get("next_change"),
        }

    def quote(self, symbol: str) -> dict:
        """Return the latest available read-only quote, including after hours."""
        payload = self._get("/markets/quotes", {"symbols": symbol.upper(), "greeks": "false"})
        quote = (payload.get("quotes") or {}).get("quote")
        if isinstance(quote, list):
            quote = quote[0] if quote else None
        if not quote:
            raise TradierError(f"Tradier returned no quote for {symbol.upper()}")
        # Tradier may have no current last trade outside market hours. Preserve the
        # provider values and expose the latest usable price without inventing one.
        latest = quote.get("last")
        if latest is None:
            latest = quote.get("close")
        return {
            "symbol": quote.get("symbol", symbol.upper()),
            "latest": latest,
            "last": quote.get("last"),
            "close": quote.get("close"),
            "bid": quote.get("bid"),
            "ask": quote.get("ask"),
            "trade_date": quote.get("trade_date"),
            "type": quote.get("type"),
        }

    def option_chain(self, symbol: str, expiration: date) -> tuple[pd.DataFrame, DataMeta]:
        payload = self._get("/markets/options/chains", {"symbol": symbol, "expiration": expiration.isoformat(), "greeks": "true"})
        raw = payload.get("options", {}).get("option", [])
        if isinstance(raw, dict):
            raw = [raw]
        rows = []
        for item in raw:
            greeks = item.get("greeks") or {}
            rows.append({
                "symbol": symbol.upper(), "expiration": expiration, "option_type": item.get("option_type"),
                "strike": item.get("strike"), "bid": item.get("bid"), "ask": item.get("ask"),
                "delta": greeks.get("delta"), "open_interest": item.get("open_interest") or 0,
                "volume": item.get("volume") or 0,
            })
        note = "Sandbox market data may be delayed. Missing Greeks remain missing."
        meta = DataMeta("Official Tradier API", pd.Timestamp.now(tz="UTC").isoformat(), False, "sandbox" in self.base_url, note)
        return pd.DataFrame(rows), meta
