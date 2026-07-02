"""Achievements: the coast's own marks in the ledger.

Definitions live in data/achievements.json and reuse the story engine's
requirement DSL, so an achievement can gate on any quality, stat, or seen
storylet ({"q": "races_won", "gte": 5}, {"seen": "victory_finale"}).
Unlocks persist in profile["achievements"] and are announced with queued
speech so they never talk over the moment that earned them.

Hidden achievements keep their name and description to themselves until
unlocked; the list speaks a placeholder so story beats stay unspoiled.
"""

import json
import os
from typing import Optional

from core.paths import DATA_DIR
from game import profile as profile_mod
from story.engine import check_requirements

HIDDEN_NAME = "A secret the sea is keeping"
HIDDEN_HELP = ("Some marks name themselves only when made. "
               "Follow the story; the sea will tell you.")

_cache: Optional[dict] = None


def _data() -> dict:
    global _cache
    if _cache is None:
        path = os.path.join(DATA_DIR, "achievements.json")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                _cache = json.load(f)
        else:
            _cache = {}
    return _cache


def categories() -> list[dict]:
    return _data().get("categories", [])


def all_achievements() -> list[dict]:
    return _data().get("achievements", [])


def build_context(profile: dict) -> dict:
    """The storylet quality context, plus collection totals."""
    ctx = profile_mod.build_context(profile)
    ctx.update({
        "vessels_owned": len(profile.get("unlocked_vessels", [])),
        "gear_owned": len(profile.get("owned_gear", [])),
        "salvage_lifetime": profile["stats"].get("salvage_lifetime", 0),
    })
    return ctx


def is_unlocked(profile: dict, achievement_id: str) -> bool:
    return achievement_id in profile.get("achievements", {})


def check_new(profile: dict) -> list[dict]:
    """Marks and returns every locked achievement whose requirements now hold."""
    unlocked = profile.setdefault("achievements", {})
    ctx = build_context(profile)
    seen = profile["seen_storylets"]
    new = []
    for ach in all_achievements():
        if ach["id"] in unlocked:
            continue
        if check_requirements(ach.get("requires", []), ctx, seen):
            unlocked[ach["id"]] = profile.get("tides", 0)
            new.append(ach)
    return new


def announce(game) -> list[dict]:
    """Checks for new unlocks and queues their announcements. The audio cue
    plays once however many land together; each name is spoken in turn."""
    new = check_new(game.profile)
    if new:
        game.audio.big_success()
        for ach in new:
            game.speech.queue(f"Achievement unlocked: {ach['name']}. "
                              f"{ach['description']}")
    return new
