from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

LIQUID_UNIVERSE = [
    "SPY", "QQQ", "IWM", "DIA", "AAPL", "NVDA", "META", "MSFT", "AMZN", "TSLA",
    "AMD", "GOOGL", "GOOG", "NFLX", "AVGO", "INTC", "MU", "ORCL", "CRM", "ADBE",
    "JPM", "BAC", "WFC", "GS", "C", "V", "MA", "PYPL", "COIN", "HOOD",
    "XOM", "CVX", "OXY", "SLB", "UNH", "LLY", "PFE", "MRK", "ABBV", "JNJ",
    "WMT", "COST", "HD", "DIS", "NKE", "BA", "CAT", "GE", "GLD", "TLT",
]


@dataclass(frozen=True)
class Settings:
    # default_factory is intentional: values must be read when Settings is created,
    # not once when this module is imported by Streamlit.
    tradier_token: str = field(default_factory=lambda: os.getenv("TRADIER_API_TOKEN", ""))
    tradier_account_id: str = field(default_factory=lambda: os.getenv("TRADIER_ACCOUNT_ID", ""))
    tradier_base_url: str = field(default_factory=lambda: os.getenv("TRADIER_BASE_URL", "https://sandbox.tradier.com/v1"))
    demo_mode: bool = field(default_factory=lambda: os.getenv("OPTIONSELI_DEMO_MODE", "true").lower() in {"1", "true", "yes"})
    db_path: Path = field(default_factory=lambda: Path(os.getenv("OPTIONSELI_DB_PATH", "data/optionseli.db")))
    public_mode: bool = field(default_factory=lambda: (
        os.getenv("OPTIONSELI_FORCE_PUBLIC_MODE", "false").lower() in {"1", "true", "yes"}
        or os.getenv("OPTIONSELI_FORCE_PRIVATE_CLOUD_MODE", "false").lower() in {"1", "true", "yes"}
        or os.getenv("OPTIONSELI_PUBLIC_MODE", "false").lower() in {"1", "true", "yes"}
    ))
    private_cloud_mode: bool = field(default_factory=lambda: os.getenv("OPTIONSELI_FORCE_PRIVATE_CLOUD_MODE", "false").lower() in {"1", "true", "yes"})
    private_cloud_tradier_authorized: bool = field(default_factory=lambda: os.getenv("OPTIONSELI_PRIVATE_CLOUD_TRADIER_AUTHORIZED", "false").lower() in {"1", "true", "yes"})
    api_calls_per_minute: int = field(default_factory=lambda: int(os.getenv("OPTIONSELI_API_CALLS_PER_MINUTE", "50")))
    max_expirations_per_scan: int = field(default_factory=lambda: int(os.getenv("OPTIONSELI_MAX_EXPIRATIONS_PER_SCAN", "4")))
    public_tradier_authorized: bool = field(default_factory=lambda: os.getenv("OPTIONSELI_PUBLIC_TRADIER_AUTHORIZED", "false").lower() in {"1", "true", "yes"})


def get_settings(env_path: str | Path = ".env", secret_values: dict | None = None) -> Settings:
    """Reload the private environment file and return one current configuration.

    ``override=True`` is required for Streamlit: the Python process survives script
    reruns, so values from a newly saved .env must replace its earlier environment.
    """
    load_dotenv(dotenv_path=env_path, override=True)
    for key, value in (secret_values or {}).items():
        if key.startswith("TRADIER_") or key.startswith("OPTIONSELI_"):
            os.environ[key] = str(value)
    return Settings()


DEFAULTS = {
    "delta_min": 0.10,
    "delta_max": 0.15,
    "target_credit": 1.00,
    "max_loss_min": 300.0,
    "max_loss_max": 500.0,
    "widths": [5.0],
    "max_bid_ask": 0.50,
    "min_open_interest": 100,
    "dte_min": 14,
    "dte_max": 45,
    "transaction_cost": 2.60,
}
