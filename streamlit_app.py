"""Public Streamlit Community Cloud entrypoint.

This module forces the read-only public policy before loading the shared application.
Run ``app.py`` locally to retain private Settings and Trade Journal pages.
"""

import os
import runpy
from pathlib import Path

os.environ["OPTIONSELI_FORCE_PUBLIC_MODE"] = "true"

# Streamlit executes this entrypoint again for every widget interaction. A normal
# ``import app`` is cached by Python and renders nothing on the second run. run_path
# deliberately executes the shared app on every rerun.
runpy.run_path(str(Path(__file__).with_name("app.py")), run_name="__main__")
