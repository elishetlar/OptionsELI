from pathlib import Path
from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest

from optionseli.cloud_auth import identity_is_allowed, run_authenticated_app

ENTRYPOINT = Path(__file__).resolve().parents[1] / "streamlit_app.py"


class StopExecution(RuntimeError):
    pass


class FakeStreamlit:
    def __init__(self):
        self.user = SimpleNamespace(is_logged_in=False, email=None)
        self.errors = []
        self.runner_reached = False

    def error(self, message):
        self.errors.append(message)

    def title(self, _message):
        pass

    def info(self, _message):
        pass

    def button(self, _label, **_kwargs):
        return False

    def stop(self):
        raise StopExecution


def test_unauthenticated_request_never_runs_application_or_market_code():
    st = FakeStreamlit()
    runner_calls = []

    with pytest.raises(StopExecution):
        run_authenticated_app(
            st,
            {"OPTIONSELI_ALLOWED_EMAILS": ["owner@example.com"]},
            Path("app.py"),
            lambda *args, **kwargs: runner_calls.append((args, kwargs)),
        )
    assert runner_calls == []


def test_non_allowlisted_identity_is_rejected():
    user = SimpleNamespace(is_logged_in=True, email="other@example.com")
    assert identity_is_allowed(user, {"owner@example.com"}) is False


def test_allowlisted_identity_is_accepted_case_insensitively():
    user = SimpleNamespace(is_logged_in=True, email="Owner@Example.com")
    assert identity_is_allowed(user, {"owner@example.com"}) is True


def test_authenticated_request_runs_shared_app_once(monkeypatch):
    import optionseli.cloud_auth

    st = FakeStreamlit()
    calls = []
    monkeypatch.setattr(optionseli.cloud_auth, "require_cloud_auth", lambda *_args: True)
    assert run_authenticated_app(st, {}, Path("app.py"), lambda *args, **kwargs: calls.append((args, kwargs)))
    assert calls == [(('app.py',), {"run_name": "__main__"})]


def test_production_entrypoint_without_auth_renders_no_dashboard(monkeypatch):
    import optionseli.cloud_auth

    monkeypatch.setattr(optionseli.cloud_auth, "_allowed_emails", lambda _secrets: set())
    app = AppTest.from_file(ENTRYPOINT, default_timeout=30).run()
    assert not app.exception
    assert len(app.radio) == 0
    assert len(app.toggle) == 0
    assert len(app.dataframe) == 0
    assert any("remains locked" in error.value for error in app.error)
