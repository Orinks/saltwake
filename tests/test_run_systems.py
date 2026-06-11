"""Chart generation, run state, weather, boons, and meta progression."""

import random

import pytest

from game import boons as boons_mod
from game import profile as profile_mod
from game.chart import generate_region_chart, spoken_name
from game.data_loader import region_by_id, vessels
from game.run import RunState
from game.weather import roll_sea_state, SEA_STATES


def make_profile(**overrides):
    p = profile_mod.new_profile()
    p.update(overrides)
    return p


def test_chart_shape_and_boss():
    region = region_by_id("shallows")
    rng = random.Random(11)
    chart = generate_region_chart(region, rng)
    assert len(chart) == region["rows"] + 1
    assert chart[-1] == [{"type": "boss", "kind": region["boss"]}]
    for row in chart[:-1]:
        assert 2 <= len(row) <= 3
        for node in row:
            assert spoken_name(node)
    midway = chart[region["rows"] // 2]
    assert any(n["type"] == "beacon" for n in midway)


def test_chart_deterministic_with_seed():
    region = region_by_id("chop")
    a = generate_region_chart(region, random.Random(5))
    b = generate_region_chart(region, random.Random(5))
    assert a == b


def test_weather_states_valid():
    rng = random.Random(3)
    for tier in range(4):
        for _ in range(50):
            assert roll_sea_state(tier, rng) in SEA_STATES


def test_run_state_lifecycle():
    profile = make_profile()
    run = RunState(profile, "skiff", ["shallows"], seed=42)
    assert run.hull == run.hull_max == vessels()["skiff"]["hull"]
    run.take_damage(3)
    assert run.hull == run.hull_max - 3 and not run.over
    run.take_damage(99)
    assert run.over and run.outcome == "wreck"


def test_gear_modifies_run():
    profile = make_profile(owned_gear=["hull_plates", "patched_wetsuit"])
    run = RunState(profile, "skiff", ["shallows"], seed=1)
    assert run.hull_max == vessels()["skiff"]["hull"] + 3
    assert run.grit_max == vessels()["skiff"]["grit"] + 2


def test_salvage_bonus_stacks():
    profile = make_profile()
    run = RunState(profile, "skiff", ["shallows"], seed=1)
    run.boons.append({"id": "tide_favor", "modifiers": {"salvage_gain": 0.2}})
    run.add_salvage(10)
    assert run.salvage == 12


def test_boon_grant_no_duplicates():
    profile = make_profile()
    run = RunState(profile, "skiff", ["shallows"], seed=9)
    offers = boons_mod.grant_random(run, random.Random(2), count=3)
    assert len({b["id"] for b in offers}) == len(offers) == 3
    run.boons.extend(offers)
    again = boons_mod.grant_random(run, random.Random(2), count=3)
    assert not {b["id"] for b in again} & {b["id"] for b in offers}


def test_consume_tag():
    profile = make_profile()
    run = RunState(profile, "skiff", ["shallows"], seed=9)
    run.boons.append({"id": "mirror_calm", "tags": ["reroll_fail"]})
    assert boons_mod.has_tag(run, "reroll_fail")
    assert boons_mod.consume_tag(run, "reroll_fail")
    assert not boons_mod.has_tag(run, "reroll_fail")


def test_renown_levels():
    p = make_profile(renown=0)
    assert profile_mod.renown_level(p) == 0
    p["renown"] = 10
    assert profile_mod.renown_level(p) == 1
    p["renown"] = 9999
    assert profile_mod.renown_level(p) == len(profile_mod.RENOWN_THRESHOLDS) - 1


def test_build_context_includes_run(tmp_path):
    p = make_profile(tides=4, wrecks=2)
    p["qualities"]["met_odessa"] = 1
    run = RunState(p, "skiff", ["shallows"], seed=2)
    run.salvage = 7
    ctx = profile_mod.build_context(p, run)
    assert ctx["runs"] == 4 and ctx["wrecks"] == 2
    assert ctx["met_odessa"] == 1
    assert ctx["salvage"] == 7 and ctx["at_sea"] == 1


def test_profile_save_roundtrip(tmp_path, monkeypatch):
    from core import savegame, paths
    monkeypatch.setattr(paths, "SAVE_DIR", str(tmp_path))
    monkeypatch.setattr(savegame, "SAVE_DIR", str(tmp_path))
    p = make_profile(pearls=33, tides=5)
    p["qualities"]["act2_started"] = 1
    savegame.save_profile(p)
    loaded = savegame.load_profile()
    assert loaded["pearls"] == 33
    assert loaded["qualities"]["act2_started"] == 1


def test_load_or_create_backfills_new_keys(tmp_path, monkeypatch):
    from core import savegame, paths
    monkeypatch.setattr(paths, "SAVE_DIR", str(tmp_path))
    monkeypatch.setattr(savegame, "SAVE_DIR", str(tmp_path))
    old = {"pearls": 5, "stats": {"races_won": 2}}
    savegame.save_profile(old)
    merged = profile_mod.load_or_create()
    assert merged["pearls"] == 5
    assert merged["stats"]["races_won"] == 2
    assert "rescues" in merged["stats"]
    assert merged["unlocked_vessels"] == ["skiff"]
