from __future__ import annotations


PUBLIC_PAGES = ("Market Overview", "Stock Scanner", "Options Scanner", "Testing Lab")
PRIVATE_PAGES = ("Trade Journal", "Settings")


def available_pages(public_mode: bool) -> list[str]:
    pages = list(PUBLIC_PAGES)
    if not public_mode:
        pages.extend(PRIVATE_PAGES)
    return pages
