"""The Drowned Almanac's data: volumes, pages, and the loose-page pool.

Marquee pages are granted by name from storylet effects ("almanac").
Loose pages carry ``"loose": true`` and drop from gameplay instead — deep
dives, fishing hauls, caches, and repeatable storylets use the
"almanac_loose" effect to grant a random page the player does not have
yet. A loose page may gate itself behind a story quality with
``"after": "<quality>"`` (the New Mornings volume arrives with the ending).
"""

import json
import os
import random
from typing import Optional

from core.paths import STORY_DIR

_cache: Optional[dict] = None


def _data() -> dict:
    global _cache
    if _cache is None:
        path = os.path.join(STORY_DIR, "almanac_pages.json")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                _cache = json.load(f)
        else:
            _cache = {}
    return _cache


def volumes() -> list[dict]:
    return _data().get("volumes", [])


def pages() -> list[dict]:
    return _data().get("pages", [])


def page_by_id(page_id: str) -> Optional[dict]:
    for page in pages():
        if page["id"] == page_id:
            return page
    return None


def _gate_open(page: dict, qualities: dict) -> bool:
    after = page.get("after")
    return after is None or qualities.get(after, 0) > 0


def loose_pool(profile: dict) -> list[dict]:
    """Loose pages the player can still find: not held, story gate open."""
    found = set(profile.get("almanac", []))
    qualities = profile.get("qualities", {})
    return [page for page in pages()
            if page.get("loose")
            and page["id"] not in found
            and _gate_open(page, qualities)]


def draw_loose(profile: dict, rng: Optional[random.Random] = None) -> Optional[dict]:
    """Grants a random still-findable loose page; None when the pool is dry."""
    pool = loose_pool(profile)
    if not pool:
        return None
    page = (rng or random).choice(pool)
    profile["almanac"].append(page["id"])
    return page
