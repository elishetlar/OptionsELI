from __future__ import annotations

import os
from pathlib import Path

from dotenv import set_key


ENV_PATH = Path(".env")


def save_market_settings(token: str, account_id: str, base_url: str, demo_mode: bool) -> None:
    """Persist private local settings without ever returning or logging secrets."""
    ENV_PATH.touch(mode=0o600, exist_ok=True)
    os.chmod(ENV_PATH, 0o600)
    values = {
        "TRADIER_API_TOKEN": token,
        "TRADIER_ACCOUNT_ID": account_id,
        "TRADIER_BASE_URL": base_url,
        "OPTIONSELI_DEMO_MODE": str(demo_mode).lower(),
    }
    for key, value in values.items():
        set_key(str(ENV_PATH), key, value, quote_mode="always")
        os.environ[key] = value


def masked_token_hint(token: str) -> str:
    if not token:
        return "Not configured"
    return f"Configured (ends in …{token[-4:]})" if len(token) >= 4 else "Configured"
