from __future__ import annotations


PUBLIC_PAGES = ("Market Overview", "Stock Scanner", "Options Scanner", "Testing Lab")
PRIVATE_PAGES = ("Trade Journal", "Settings")


def available_pages(public_mode: bool) -> list[str]:
    pages = list(PUBLIC_PAGES)
    if not public_mode:
        pages.extend(PRIVATE_PAGES)
    return pages


def options_scan_available(demo_mode: bool, tradier_configured: bool, public_tradier_allowed: bool = True) -> bool:
    return demo_mode or (tradier_configured and public_tradier_allowed)
