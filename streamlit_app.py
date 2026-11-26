"""Private Streamlit Community Cloud entrypoint.

Streamlit Community Cloud private sharing controls access before this script runs.
Run ``app.py`` locally to retain local Settings and Trade Journal pages.
"""

import importlib
import os
import runpy
import sys
from pathlib import Path

os.environ["OPTIONSELI_FORCE_PRIVATE_CLOUD_MODE"] = "true"

# Streamlit reruns this entrypoint in a long-lived interpreter. Invalidate source
# caches and discard every OptionsELI module from an earlier deployment so a new
# app.py can never be paired with stale package code. A fixed module list is unsafe:
# newly added modules or exports would otherwise remain cached across hot deploys.
importlib.invalidate_caches()
for module_name in tuple(sys.modules):
    if module_name != "optionseli" and not module_name.startswith("optionseli."):
        continue
    sys.modules.pop(module_name, None)

# Streamlit's private-sharing proxy authenticates invited viewers before this
# entrypoint is served. Execute the shared app on each Streamlit rerun.
runpy.run_path(str(Path(__file__).with_name("app.py")), run_name="__main__")
