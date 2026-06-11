"""Meta progression: everything that persists between runs.

Design follows the Hades principle that a failed run must still move
something forward: pearls, renown, story qualities, almanac pages, and
sea-debt (wrecks feed their own storylet arc) all survive a wreck.
"""

import copy

from core import savegame

RENOWN_THRESHOLDS = [0, 10, 25, 45, 70, 100, 140, 190, 250, 320]

DEFAULT_PROFILE = {
    "name": "Tideborn",
    "pearls": 0,
    "renown": 0,
    "tides": 0,          # runs embarked
    "wrecks": 0,
    "homecomings": 0,    # runs finished by returning to port
    "deepest_region": 0,
    "qualities": {},
    "seen_storylets": {},
    "almanac": [],
    "unlocked_vessels": ["skiff"],
    "owned_gear": [],
    "unlocked_regions": ["shallows"],
    "tide_marks": 0,
    "stats": {
        "races_won": 0,
        "slaloms_cleared": 0,
        "dives_completed": 0,
        "storms_survived": 0,
        "fish_caught": 0,
        "rescues": 0,
        "salvage_lifetime": 0,
        "bosses_beaten": 0,
    },
    "settings": {"speech_rate": 50, "audio_volume": 0.5},
}


def new_profile() -> dict:
    return copy.deepcopy(DEFAULT_PROFILE)


def load_or_create() -> dict:
    data = savegame.load_profile()
    if data is None:
        return new_profile()
    # Backfill any keys added since the save was written.
    merged = new_profile()
    for key, value in data.items():
        if key in ("stats", "settings", "qualities", "seen_storylets") and isinstance(value, dict):
            merged[key].update(value)
        else:
            merged[key] = value
    return merged


def save(profile: dict) -> None:
    savegame.save_profile(profile)


def renown_level(profile: dict) -> int:
    points = profile.get("renown", 0)
    level = 0
    for i, threshold in enumerate(RENOWN_THRESHOLDS):
        if points >= threshold:
            level = i
    return level


def renown_to_next(profile: dict) -> int | None:
    level = renown_level(profile)
    if level + 1 >= len(RENOWN_THRESHOLDS):
        return None
    return RENOWN_THRESHOLDS[level + 1] - profile.get("renown", 0)


def get_quality(profile: dict, name: str) -> int:
    return profile["qualities"].get(name, 0)


def set_quality(profile: dict, name: str, value: int) -> None:
    profile["qualities"][name] = value


def add_quality(profile: dict, name: str, delta: int) -> int:
    value = profile["qualities"].get(name, 0) + delta
    profile["qualities"][name] = value
    return value


def mark_seen(profile: dict, storylet_id: str) -> None:
    seen = profile["seen_storylets"]
    seen[storylet_id] = seen.get(storylet_id, 0) + 1


def build_context(profile: dict, run=None) -> dict:
    """Quality context for storylet requirement checks."""
    ctx = dict(profile["qualities"])
    ctx.update({
        "runs": profile.get("tides", 0),
        "wrecks": profile.get("wrecks", 0),
        "homecomings": profile.get("homecomings", 0),
        "renown_level": renown_level(profile),
        "pearls": profile.get("pearls", 0),
        "tide_marks": profile.get("tide_marks", 0),
        "almanac_pages": len(profile.get("almanac", [])),
        "deepest_region": profile.get("deepest_region", 0),
        "bosses_beaten": profile["stats"].get("bosses_beaten", 0),
        "rescues": profile["stats"].get("rescues", 0),
        "races_won": profile["stats"].get("races_won", 0),
        "fish_caught": profile["stats"].get("fish_caught", 0),
        "slaloms_cleared": profile["stats"].get("slaloms_cleared", 0),
        "dives_completed": profile["stats"].get("dives_completed", 0),
        "storms_survived": profile["stats"].get("storms_survived", 0),
    })
    if run is not None:
        ctx.update({
            "hull": run.hull,
            "salvage": run.salvage,
            "region_index": run.region_index,
            "at_sea": 1,
        })
    return ctx
