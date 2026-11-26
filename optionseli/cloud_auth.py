from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any


def _allowed_emails(secrets: Mapping[str, Any]) -> set[str]:
    raw = secrets.get("OPTIONSELI_ALLOWED_EMAILS", [])
    if isinstance(raw, str):
        raw = raw.split(",")
    if not isinstance(raw, Iterable):
        return set()
    return {str(value).strip().casefold() for value in raw if str(value).strip()}


def identity_is_allowed(user: Any, allowed_emails: set[str]) -> bool:
    if not bool(getattr(user, "is_logged_in", False)):
        return False
    email = str(getattr(user, "email", "") or "").strip().casefold()
    return bool(email and email in allowed_emails)


def require_cloud_auth(st: Any, secrets: Mapping[str, Any]) -> bool:
    """Render the OIDC gate and return True only for an allowlisted identity."""
    allowed = _allowed_emails(secrets)
    if not allowed:
        st.error("Authentication is not configured. The application remains locked.")
        return False

    user = st.user
    if not bool(getattr(user, "is_logged_in", False)):
        st.title("OptionsELI")
        st.info("This is a private application. Sign in with the authorized account to continue.")
        if st.button("Sign in securely", type="primary"):
            st.login("google")
        return False

    if not identity_is_allowed(user, allowed):
        st.error("This signed-in account is not authorized to access OptionsELI.")
        if st.button("Sign out"):
            st.logout()
        return False
    return True


def run_authenticated_app(
    st: Any,
    secrets: Mapping[str, Any],
    app_path: Path,
    runner: Callable[..., Any],
) -> bool:
    """Run the shared application only after authentication succeeds."""
    if not require_cloud_auth(st, secrets):
        st.stop()
        return False
    runner(str(app_path), run_name="__main__")
    return True
