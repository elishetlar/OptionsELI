from __future__ import annotations

import logging


logger = logging.getLogger("optionseli")
logger.setLevel(logging.INFO)


def log_event(event: str, **fields: object) -> None:
    """Log operational metadata only; credential-like fields are never accepted."""
    safe_fields = {
        key: value for key, value in fields.items()
        if not any(term in key.lower() for term in ("token", "secret", "password", "account", "authorization"))
    }
    details = " ".join(f"{key}={value}" for key, value in sorted(safe_fields.items()))
    logger.info("event=%s%s", event, f" {details}" if details else "")


def log_failure(event: str, error: Exception, **fields: object) -> None:
    """Log an exception class without its message, which may contain provider data."""
    log_event(event, error_type=type(error).__name__, **fields)
