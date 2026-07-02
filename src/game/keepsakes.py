"""Keepsakes: personal objects the sea returns, and their owners.

The sea holds people's memories and gives them back attached to things —
the game's whole premise, playable in miniature for everyone else. A
keepsake surfaces with dive salvage (rarely) or from a story beat, rides
in the sea chest with a spoken hint about who might know it, and pays off
in a delivery storylet at the quay.

Data lives in data/keepsakes.json. Each entry may gate its appearance
behind a story quality with ``"after": "<quality>"`` so an object never
surfaces before its owner could receive it.
"""

import json
import os
import random
from typing import Optional

from core.paths import DATA_DIR

_cache: Optional[list] = None


def all_keepsakes() -> list[dict]:
    global _cache
    if _cache is None:
        path = os.path.join(DATA_DIR, "keepsakes.json")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                _cache = json.load(f).get("keepsakes", [])
        else:
            _cache = []
    return _cache


def by_id(keepsake_id: str) -> Optional[dict]:
    for keepsake in all_keepsakes():
        if keepsake["id"] == keepsake_id:
            return keepsake
    return None


def _gate_open(keepsake: dict, qualities: dict) -> bool:
    after = keepsake.get("after")
    return after is None or qualities.get(after, 0) > 0


def pool(profile: dict) -> list[dict]:
    """Keepsakes that can still surface: not carried, not delivered,
    story gate open."""
    held = set(profile.get("keepsakes", []))
    done = set(profile.get("keepsakes_delivered", []))
    qualities = profile.get("qualities", {})
    return [k for k in all_keepsakes()
            if k["id"] not in held and k["id"] not in done
            and _gate_open(k, qualities)]


def draw(profile: dict, rng: Optional[random.Random] = None) -> Optional[dict]:
    """Surfaces a random findable keepsake; None when the sea has nothing
    personal left to hand back."""
    findable = pool(profile)
    if not findable:
        return None
    keepsake = (rng or random).choice(findable)
    profile["keepsakes"].append(keepsake["id"])
    return keepsake


def grant(profile: dict, keepsake_id: str) -> Optional[dict]:
    """Grants a specific keepsake by id (story-driven finds)."""
    if keepsake_id in profile.get("keepsakes", []) or \
            keepsake_id in profile.get("keepsakes_delivered", []):
        return None
    keepsake = by_id(keepsake_id)
    if keepsake is not None:
        profile["keepsakes"].append(keepsake_id)
    return keepsake


def deliver(profile: dict, keepsake_id: str) -> Optional[dict]:
    """Moves a carried keepsake to delivered. Returns it, or None if it
    was not aboard."""
    if keepsake_id not in profile.get("keepsakes", []):
        return None
    profile["keepsakes"].remove(keepsake_id)
    profile["keepsakes_delivered"].append(keepsake_id)
    return by_id(keepsake_id)
