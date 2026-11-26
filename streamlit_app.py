"""Private, authenticated Streamlit Community Cloud entrypoint.

Authentication completes before the shared application or any market-data client is
loaded. Run ``app.py`` locally to retain local Settings and Trade Journal pages.
"""

import importlib
import os
import runpy
import sys
from pathlib import Path

import streamlit as st

from optionseli.cloud_auth import run_authenticated_app

os.environ["OPTIONSELI_FORCE_PRIVATE_CLOUD_MODE"] = "true"

# Streamlit reruns this entrypoint in a long-lived interpreter. Invalidate source
# caches and discard OptionsELI modules from an earlier deployment so a new app.py
# can never be paired with stale package code.
importlib.invalidate_caches()
for module_name in (
    "optionseli.config",
    "optionseli.models",
    "optionseli.scoring",
    "optionseli.signals",
    "optionseli.spreads",
    "optionseli.strategy_scoring",
    "optionseli.ui_policy",
):
    sys.modules.pop(module_name, None)

try:
    cloud_secrets = dict(st.secrets)
except (FileNotFoundError, RuntimeError):
    cloud_secrets = {}

# No app module or market-data code is imported until this gate succeeds.
run_authenticated_app(st, cloud_secrets, Path(__file__).with_name("app.py"), runpy.run_path)
