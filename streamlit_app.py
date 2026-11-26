"""Public Streamlit Community Cloud entrypoint.

This module forces the read-only public policy before loading the shared application.
Run ``app.py`` locally to retain private Settings and Trade Journal pages.
"""

import importlib
import os
import runpy
import sys
from pathlib import Path

os.environ["OPTIONSELI_FORCE_PUBLIC_MODE"] = "true"

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

# Streamlit executes this entrypoint again for every widget interaction. A normal
# ``import app`` is cached by Python and renders nothing on the second run. run_path
# deliberately executes the shared app on every rerun.
runpy.run_path(str(Path(__file__).with_name("app.py")), run_name="__main__")
