"""Every achievement must be earnable, and none may fire on a new game.

These are data lints: they cross-reference achievements.json against the
story corpus and catalogs so a typo'd quality, an unreachable threshold,
or a start-of-game unlock can never ship again.
"""

import glob
import json
import os

from core.paths import DATA_DIR
from game import achievements
from game import data_loader
from game import profile as profile_mod

STORY_GLOB = os.path.join(DATA_DIR, "story", "*.json")

# Qualities written by engine code rather than storylet effects.
CODE_SET_QUALITIES = {"sea_debt", "undertow_faced"}

# Counters exposed by the requirement context (see profile.build_context
# and achievements.build_context).
CONTEXT_KEYS = {
    "runs", "wrecks", "homecomings", "renown_level", "pearls", "tide_marks",
    "almanac_pages", "deepest_region", "bosses_beaten", "rescues",
    "races_won", "fish_caught", "slaloms_cleared", "dives_completed",
    "storms_survived", "keepsakes_carried", "keepsakes_delivered",
    "keepsakes_found", "vessels_owned", "gear_owned", "salvage_lifetime",
}


def _storylets() -> dict:
    out = {}
    for path in glob.glob(STORY_GLOB):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for s in data.get("storylets", []):
            if "id" in s:
                out[s["id"]] = s
    return out


def _settable_qualities(storylets: dict) -> set:
    names = set(CODE_SET_QUALITIES)
    for s in storylets.values():
        effect_sets = [s.get("effects", {})]
        effect_sets += [c.get("effects", {}) for c in s.get("choices", [])]
        for eff in effect_sets:
            names.update(eff.get("set", {}))
            names.update(eff.get("add", {}))
    with open(os.path.join(DATA_DIR, "story", "bosses.json"),
              encoding="utf-8") as f:
        for boss in json.load(f).get("bosses", []):
            if boss.get("quality"):
                names.add(boss["quality"])
    return names


def _leaf_requirements(requires: list):
    for req in requires:
        if "any" in req:
            yield from _leaf_requirements(req["any"])
        elif "all" in req:
            yield from _leaf_requirements(req["all"])
        else:
            yield req


def _max_obtainable(storylets: dict, quality: str) -> int:
    """Best case for an additive quality: storylet-level adds always apply;
    a storylet's choices are mutually exclusive, so only the best counts."""
    total = 0
    for s in storylets.values():
        base = s.get("effects", {}).get("add", {}).get(quality, 0)
        best_choice = max((c.get("effects", {}).get("add", {}).get(quality, 0)
                           for c in s.get("choices", [])), default=0)
        total += base + best_choice
    return total


def test_every_requirement_references_something_real():
    storylets = _storylets()
    settable = _settable_qualities(storylets)
    for ach in achievements.all_achievements():
        for req in _leaf_requirements(ach.get("requires", [])):
            if "q" in req:
                name = req["q"]
                assert (name in settable or name in CONTEXT_KEYS
                        or name.startswith(("keepsake_", "delivered_"))), \
                    f"{ach['id']}: quality '{name}' is never set anywhere"
            for key in ("seen", "not_seen"):
                if key in req:
                    assert req[key] in storylets, \
                        f"{ach['id']}: {key} '{req[key]}' does not exist"


def test_no_achievement_unlocks_on_a_new_game():
    fresh = achievements.check_new(profile_mod.new_profile())
    assert fresh == [], [a["id"] for a in fresh]


def test_collection_thresholds_are_reachable():
    storylets = _storylets()
    with open(os.path.join(DATA_DIR, "keepsakes.json"), encoding="utf-8") as f:
        keepsakes = json.load(f)["keepsakes"]
    limits = {
        "vessels_owned": len(data_loader.vessels()),
        "gear_owned": len(data_loader.gear()),
        "keepsakes_delivered": len(keepsakes),
        "keepsakes_found": len(keepsakes),
        "deepest_region": len(data_loader.regions()),
        "tide_marks": 5,  # settings clamp
    }
    from game import almanac
    limits["almanac_pages"] = len(almanac.pages())
    for ach in achievements.all_achievements():
        for req in _leaf_requirements(ach.get("requires", [])):
            name = req.get("q")
            if name in limits:
                need = req.get("gte", req.get("eq", 0))
                assert need <= limits[name], \
                    f"{ach['id']}: needs {name} >= {need}, only {limits[name]} exist"


def test_affinity_thresholds_leave_headroom():
    """Every affinity gate must be reachable with at least one point to
    spare, so a single missed once-only beat can't permanently lock a
    relationship achievement."""
    storylets = _storylets()
    for ach in achievements.all_achievements():
        for req in _leaf_requirements(ach.get("requires", [])):
            name = req.get("q", "")
            if name.startswith("affinity_") or name == "sea_grace":
                need = req.get("gte", req.get("eq", 0))
                obtainable = _max_obtainable(storylets, name)
                assert obtainable >= need + 1, \
                    (f"{ach['id']}: needs {name} >= {need}, max obtainable "
                     f"is {obtainable} (no headroom)")


def test_keepsake_story_gates_are_settable():
    storylets = _storylets()
    settable = _settable_qualities(storylets)
    with open(os.path.join(DATA_DIR, "keepsakes.json"), encoding="utf-8") as f:
        for keepsake in json.load(f)["keepsakes"]:
            after = keepsake.get("after")
            assert after is None or after in settable, \
                f"keepsake {keepsake['id']}: gate '{after}' is never set"
