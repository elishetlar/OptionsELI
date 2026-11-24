import ast
from pathlib import Path

from streamlit.testing.v1 import AppTest

from optionseli.config import Settings

ENTRYPOINT = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def test_public_entrypoint_executes_app_on_every_rerun():
    source = ENTRYPOINT.read_text()
    assert "runpy.run_path" in source
    tree = ast.parse(source)
    assert not any(isinstance(node, ast.Import) and any(alias.name == "app" for alias in node.names) for node in ast.walk(tree))

    app = AppTest.from_file(ENTRYPOINT, default_timeout=30).run()
    assert not app.exception
    app.toggle[0].set_value(True).run()
    assert not app.exception

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


def test_public_demo_interactions_complete_without_crashing():
    app = AppTest.from_file(ENTRYPOINT, default_timeout=30).run()
    app.toggle[0].set_value(True).run()

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

    no_token = Settings(tradier_token="", public_mode=True, demo_mode=False)
    monkeypatch.setattr(optionseli.config, "get_settings", lambda *args, **kwargs: no_token)
    app = AppTest.from_file(ENTRYPOINT, default_timeout=30).run()
    assert not app.exception

    for page in ("Market Overview", "Stock Scanner", "Options Scanner", "Testing Lab"):
        app.radio[0].set_value(page).run()
        assert not app.exception, (page, [item.message for item in app.exception])

    app.radio[0].set_value("Options Scanner").run()
    scan_button = next(button for button in app.button if button.label == "Scan option chains")
    assert scan_button.disabled is True
