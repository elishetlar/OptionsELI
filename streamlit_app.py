"""Public Streamlit Community Cloud entrypoint.

This module forces the read-only public policy before loading the shared application.
Run ``app.py`` locally to retain private Settings and Trade Journal pages.
"""

import os

os.environ["OPTIONSELI_FORCE_PUBLIC_MODE"] = "true"

import app  # noqa: E402,F401  # Streamlit renders the imported application
