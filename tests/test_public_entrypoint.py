import ast
import sys
import types
from pathlib import Path

from streamlit.testing.v1 import AppTest

from optionseli.config import Settings
from optionseli.demo_data import demo_prices

ENTRYPOINT = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def test_public_entrypoint_executes_app_on_every_rerun(monkeypatch):
    import optionseli.market_data
    monkeypatch.setattr(optionseli.market_data, "yahoo_history", demo_prices)
    source = ENTRYPOINT.read_text()
    assert "runpy.run_path" in source
    assert "cloud_auth" not in source
    assert "st.login" not in source
    tree = ast.parse(source)
    assert not any(isinstance(node, ast.Import) and any(alias.name == "app" for alias in node.names) for node in ast.walk(tree))

    app = AppTest.from_file(ENTRYPOINT, default_timeout=30).run()
    assert not app.exception
    assert app.toggle[0].value is True
    assert app.toggle[0].disabled is True

    expected_titles = {
        "Market Overview": "Market Overview",
        "Stock Scanner": "Stock Scanner",
        "Options Scanner": "Options Credit Spread Scanner",
        "Testing Lab": "Paper Trading & Historical Testing Lab",
    }
    for page, title in expected_titles.items():
        app.radio[0].set_value(page).run()
        assert not app.exception, (page, [item.message for item in app.exception])
        assert title in [item.value for item in app.title]


def test_public_entrypoint_discards_stale_optionseli_modules(monkeypatch):
    """Regression: a hot deployment must not reuse an older scoring module."""
    import optionseli.market_data

    monkeypatch.setattr(optionseli.market_data, "yahoo_history", demo_prices)
    stale = types.ModuleType("optionseli.strategy_scoring")
    sys.modules["optionseli.strategy_scoring"] = stale
    app = AppTest.from_file(ENTRYPOINT, default_timeout=30).run()
    assert not app.exception
    assert hasattr(sys.modules["optionseli.strategy_scoring"], "score_candidate_with_context")


def test_public_demo_interactions_complete_without_crashing(monkeypatch):
    import optionseli.market_data
    monkeypatch.setattr(optionseli.market_data, "yahoo_history", demo_prices)
    app = AppTest.from_file(ENTRYPOINT, default_timeout=30).run()
    assert app.toggle[0].value is True

    app.radio[0].set_value("Stock Scanner").run()
    next(button for button in app.button if button.label == "Run stock scan").click().run()
    assert not app.exception
    assert len(app.dataframe) == 1

    app.radio[0].set_value("Options Scanner").run()
    next(button for button in app.button if button.label == "Scan option chains").click().run()
    assert not app.exception

    app.radio[0].set_value("Testing Lab").run()
    next(button for button in app.button if button.label == "Run signal test").click().run()
    assert not app.exception


def test_every_public_page_renders_without_tradier_token(monkeypatch):
    import optionseli.config
    import optionseli.market_data

    monkeypatch.setattr(optionseli.market_data, "yahoo_history", demo_prices)

    no_token = Settings(tradier_token="", public_mode=True, demo_mode=False)
    monkeypatch.setattr(optionseli.config, "get_settings", lambda *args, **kwargs: no_token)
    app = AppTest.from_file(ENTRYPOINT, default_timeout=30).run()
    assert not app.exception

    for page in ("Market Overview", "Stock Scanner", "Options Scanner", "Testing Lab"):
        app.radio[0].set_value(page).run()
        assert not app.exception, (page, [item.message for item in app.exception])

    app.radio[0].set_value("Options Scanner").run()
    scan_button = next(button for button in app.button if button.label == "Scan option chains")
    assert scan_button.disabled is False
    assert app.toggle[0].value is True
    assert app.toggle[0].disabled is True
