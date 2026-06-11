"""Story engine behavior plus integrity checks over the real content corpus."""

import json
import os
import random

import pytest

from core.paths import STORY_DIR
from story.engine import StoryEngine, Storylet, check_requirements

KNOWN_OPS = {"eq", "ne", "gt", "gte", "lt", "lte"}
KNOWN_EFFECT_KEYS = {
    "set", "add", "pearls", "renown", "almanac", "unlock_vessel",
    "unlock_region", "salvage", "hull", "grit", "supplies",
}


@pytest.fixture(scope="module")
def engine():
    return StoryEngine()


def _all_requirements(reqs):
    for r in reqs:
        if "any" in r:
            yield from _all_requirements(r["any"])
        elif "all" in r:
            yield from _all_requirements(r["all"])
        else:
            yield r


def test_corpus_loads_and_is_substantial(engine):
    assert len(engine.storylets) >= 60
    words = 0
    for s in engine.storylets.values():
        words += sum(len(p.split()) for p in s.pages)
        for c in s.choices:
            words += sum(len(p.split()) for p in c.get("response", []))
    assert words > 8000, f"story corpus unexpectedly small: {words} words"


def test_goto_targets_exist(engine):
    for s in engine.storylets.values():
        for c in s.choices:
            goto = c.get("goto")
            if goto:
                assert goto in engine.storylets, f"{s.id} -> missing goto {goto}"


def test_requirement_shapes(engine):
    for s in engine.storylets.values():
        for req in _all_requirements(s.requires):
            if "q" in req:
                ops = [k for k in req if k in KNOWN_OPS]
                assert ops, f"{s.id} has a quality requirement without an operator"
            else:
                assert "seen" in req or "not_seen" in req, \
                    f"{s.id} has an unrecognized requirement {req}"


def test_effect_keys_are_known(engine):
    for s in engine.storylets.values():
        for effects in [s.effects] + [c.get("effects", {}) for c in s.choices]:
            for key in effects:
                assert key in KNOWN_EFFECT_KEYS, f"{s.id} uses unknown effect {key}"


def test_almanac_effects_reference_real_pages(engine):
    with open(os.path.join(STORY_DIR, "almanac_pages.json"), encoding="utf-8") as f:
        page_ids = {p["id"] for p in json.load(f)["pages"]}
    referenced = set()
    for s in engine.storylets.values():
        for effects in [s.effects] + [c.get("effects", {}) for c in s.choices]:
            if "almanac" in effects:
                referenced.add(effects["almanac"])
    assert referenced <= page_ids, f"missing pages: {referenced - page_ids}"
    assert page_ids <= referenced, f"unobtainable pages: {page_ids - referenced}"


def test_unlock_vessels_exist(engine):
    from game.data_loader import vessels
    ids = set(vessels())
    for s in engine.storylets.values():
        for effects in [s.effects] + [c.get("effects", {}) for c in s.choices]:
            if "unlock_vessel" in effects:
                assert effects["unlock_vessel"] in ids


def test_priority_and_once_selection():
    engine = StoryEngine.__new__(StoryEngine)
    engine.storylets = {}
    engine.rng = random.Random(7)
    for sid, prio, reqs in [("low", 1, []), ("high", 9, []),
                            ("gated", 20, [{"q": "runs", "gte": 5}])]:
        engine.storylets[sid] = Storylet(
            {"id": sid, "where": "tavern", "priority": prio, "requires": reqs})
    seen = {}
    assert engine.pick("tavern", {"runs": 0}, seen).id == "high"
    assert engine.pick("tavern", {"runs": 6}, seen).id == "gated"
    seen = {"high": 1, "gated": 1}
    assert engine.pick("tavern", {"runs": 6}, seen).id == "low"
    seen["low"] = 1
    assert engine.pick("tavern", {"runs": 6}, seen) is None


def test_requirement_logic():
    seen = {"a": 1}
    assert check_requirements([{"seen": "a"}], {}, seen)
    assert not check_requirements([{"not_seen": "a"}], {}, seen)
    assert check_requirements([{"q": "x", "gte": 2, "lte": 4}], {"x": 3}, {})
    assert not check_requirements([{"q": "x", "gte": 2, "lte": 4}], {"x": 5}, {})
    assert check_requirements(
        [{"any": [{"q": "x", "gte": 9}, {"seen": "a"}]}], {"x": 0}, seen)


def test_main_arc_progression_is_reachable(engine):
    """Walk the spine: a player who plays enough always reaches the finale."""
    ctx = {"runs": 1, "met_nereus": 1, "almanac_pages": 2, "cleared_shallows": 1}
    seen = {}

    def pick(where):
        s = engine.pick(where, ctx, seen)
        assert s is not None, f"no storylet eligible at {where}"
        seen[s.id] = seen.get(s.id, 0) + 1  # what viewing does in-game
        return s

    assert pick("talk_nereus").id == "nereus_handwriting"
    ctx["handwriting_known"] = 1
    assert pick("lighthouse").id == "lighthouse_first"
    ctx.update({"act2_started": 1, "recognized": 1, "seen_pale_ferry": 1})
    assert pick("talk_odessa").id == "ferry_aftermath_odessa"
    ctx.update({"jane_quest": 1, "cleared_wreckwater": 1})
    assert pick("talk_nereus").id == "nereus_trench"
    ctx["jane_located"] = 1
    assert pick("talk_odessa").id == "raising_the_jane"
    ctx.update({"jane_raised": 1, "act3_started": 1})
    assert pick("boss_the_undertow").id == "boss_undertow_first"
    assert pick("victory").id == "victory_finale"
