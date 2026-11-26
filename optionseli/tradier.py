from __future__ import annotations

from datetime import date, datetime, timezone

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
            "prevclose": quote.get("prevclose"),
            "change": quote.get("change"),
            "change_percentage": quote.get("change_percentage"),
            "volume": quote.get("volume"),
            "type": quote.get("type"),
        }

    def history(self, symbol: str, start: date, end: date) -> tuple[pd.DataFrame, DataMeta]:
        """Return actual daily OHLCV history from the read-only Tradier endpoint."""
        payload = self._get("/markets/history", {
            "symbol": symbol.upper(), "interval": "daily",
            "start": start.isoformat(), "end": end.isoformat(),
        })
        raw = (payload.get("history") or {}).get("day", [])
        if isinstance(raw, dict):
            raw = [raw]
        frame = pd.DataFrame(raw)
        if frame.empty:
            raise TradierError(f"Tradier returned no daily history for {symbol.upper()}")
        required = {"date", "open", "high", "low", "close", "volume"}
        if not required.issubset(frame.columns):
            raise TradierError(f"Tradier history for {symbol.upper()} is incomplete")
        frame = frame.rename(columns={
            "open": "Open", "high": "High", "low": "Low",
            "close": "Close", "volume": "Volume",
        })
        frame.index = pd.to_datetime(frame.pop("date"))
        frame = frame[["Open", "High", "Low", "Close", "Volume"]].apply(pd.to_numeric, errors="coerce").dropna(subset=["Close"])
        observed = pd.Timestamp(frame.index[-1]).isoformat()
        sandbox = "sandbox" in self.base_url
        note = "Sandbox data is delayed 15 minutes." if sandbox else "Production timing depends on the account's market-data entitlements; verify observation timestamps."
        return frame, DataMeta("Official Tradier API", pd.Timestamp.now(tz="UTC").isoformat(), False, sandbox, note, observed)

    def option_chain(self, symbol: str, expiration: date) -> tuple[pd.DataFrame, DataMeta]:
        payload = self._get("/markets/options/chains", {"symbol": symbol, "expiration": expiration.isoformat(), "greeks": "true"})
        raw = payload.get("options", {}).get("option", [])
        if isinstance(raw, dict):
            raw = [raw]
        rows = []
        for item in raw:
            greeks = item.get("greeks") or {}
            quote_timestamp = _latest_timestamp(item.get("bid_date"), item.get("ask_date"), item.get("trade_date"))
            rows.append({
                "symbol": symbol.upper(), "expiration": expiration, "option_type": item.get("option_type"),
                "strike": item.get("strike"), "bid": item.get("bid"), "ask": item.get("ask"),
                "delta": greeks.get("delta"), "open_interest": item.get("open_interest") or 0,
                "volume": item.get("volume") or 0,
                "gamma": greeks.get("gamma"), "theta": greeks.get("theta"),
                "vega": greeks.get("vega"), "rho": greeks.get("rho"),
                "mid_iv": greeks.get("mid_iv"), "quote_timestamp": quote_timestamp,
            })
        frame = pd.DataFrame(rows)
        observed = ""
        if not frame.empty and frame["quote_timestamp"].notna().any():
            observed = pd.to_datetime(frame["quote_timestamp"], utc=True).max().isoformat()
        sandbox = "sandbox" in self.base_url
        note = "Sandbox data is delayed 15 minutes. Missing Greeks remain missing." if sandbox else "Production timing depends on entitlement. Missing Greeks remain missing; no estimates are substituted."
        meta = DataMeta("Official Tradier API", pd.Timestamp.now(tz="UTC").isoformat(), False, sandbox, note, observed)
        return frame, meta


def _timestamp(value: object) -> pd.Timestamp | None:
    if value in (None, "", 0):
        return None
    try:
        numeric = float(value)
        unit = "ms" if numeric > 10_000_000_000 else "s"
        return pd.to_datetime(numeric, unit=unit, utc=True)
    except (TypeError, ValueError, OverflowError):
        try:
            return pd.to_datetime(value, utc=True)
        except (TypeError, ValueError):
            return None


def _latest_timestamp(*values: object) -> str | None:
    parsed = [item for item in (_timestamp(value) for value in values) if item is not None]
    return max(parsed).isoformat() if parsed else None


def chain_data_is_stale(chain: pd.DataFrame, now: datetime | None = None) -> bool:
    """Fail closed when a chain has no verifiable recent quote timestamps."""
    if chain.empty or "quote_timestamp" not in chain or not chain["quote_timestamp"].notna().any():
        return True
    current = pd.Timestamp(now or datetime.now(timezone.utc))
    if current.tzinfo is None:
        current = current.tz_localize("UTC")
    latest = pd.to_datetime(chain["quote_timestamp"], utc=True, errors="coerce").max()
    if pd.isna(latest):
        return True
    # During regular US market hours, quotes older than 30 minutes are stale.
    eastern_now = current.tz_convert("America/New_York")
    in_session = eastern_now.weekday() < 5 and (9, 30) <= (eastern_now.hour, eastern_now.minute) <= (16, 15)
    quote_age_seconds = (current.to_pydatetime() - latest.to_pydatetime()).total_seconds()
    if in_session and quote_age_seconds > 30 * 60:
        return True
    latest_day = latest.tz_convert("America/New_York").normalize().tz_localize(None)
    current_day = eastern_now.normalize().tz_localize(None)
    return len(pd.bdate_range(latest_day, current_day)) - 1 > 1
