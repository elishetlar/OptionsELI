from optionseli.config import get_settings
from optionseli.rate_limit import RateLimitExceeded, SlidingWindowRateLimiter
from optionseli.ui_policy import available_pages, options_scan_available


def test_streamlit_secrets_override_local_environment(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("TRADIER_API_TOKEN='local-token'\nOPTIONSELI_PUBLIC_MODE='false'\n")
    settings = get_settings(env_file, {
        "TRADIER_API_TOKEN": "cloud-token",
        "TRADIER_BASE_URL": "https://sandbox.tradier.com/v1",
        "OPTIONSELI_PUBLIC_MODE": True,
    })
    assert settings.tradier_token == "cloud-token"
    assert settings.public_mode is True


def test_public_navigation_excludes_private_pages():
    pages = available_pages(True)
    assert "Stock Scanner" in pages
    assert "Options Scanner" in pages
    assert "Trade Journal" not in pages
    assert "Settings" not in pages
    assert "Trade Journal" in available_pages(False)


def test_force_public_mode_cannot_be_overridden(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("OPTIONSELI_PUBLIC_MODE='false'\n")
    monkeypatch.setenv("OPTIONSELI_FORCE_PUBLIC_MODE", "true")
    assert get_settings(env_file).public_mode is True


def test_shared_rate_limiter_rejects_excess_requests():
    limiter = SlidingWindowRateLimiter(2, 60)
    limiter.acquire()
    limiter.acquire()
    try:
        limiter.acquire()
    except RateLimitExceeded as exc:
        assert "Try again" in str(exc)
    else:
        raise AssertionError("Expected the third request to be rate limited")


def test_options_scanner_availability_without_credentials():
    assert options_scan_available(False, False) is False
    assert options_scan_available(True, False) is True
    assert options_scan_available(False, True) is True
