import os

from optionseli.config import get_settings
from optionseli.settings_store import masked_token_hint, save_market_settings


def test_masked_token_never_returns_full_secret():
    secret = "super-secret-token-1234"
    hint = masked_token_hint(secret)
    assert secret not in hint
    assert hint.endswith("1234)")


def test_saved_env_is_private_and_ignored_location(tmp_path, monkeypatch):
    from optionseli import settings_store

    env_path = tmp_path / ".env"
    monkeypatch.setattr(settings_store, "ENV_PATH", env_path)
    save_market_settings("secret", "account", "https://sandbox.tradier.com/v1", True)
    assert oct(env_path.stat().st_mode & 0o777) == "0o600"
    assert "TRADIER_API_TOKEN='secret'" in env_path.read_text()
    assert os.environ["TRADIER_API_TOKEN"] == "secret"


def test_settings_reload_saved_credentials_without_module_reload(tmp_path, monkeypatch):
    from optionseli import settings_store

    env_path = tmp_path / ".env"
    monkeypatch.setattr(settings_store, "ENV_PATH", env_path)
    monkeypatch.setenv("TRADIER_API_TOKEN", "stale-token")
    save_market_settings("new-token", "acct", "https://sandbox.tradier.com/v1", False)
    loaded = get_settings(env_path)
    assert loaded.tradier_token == "new-token"
    assert loaded.tradier_account_id == "acct"
    assert loaded.demo_mode is False
