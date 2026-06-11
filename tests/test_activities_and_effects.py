"""Cue runner mechanics and storylet effect application (logic only)."""

import pygame
import pytest

from core.audio import NullAudio
from core.speech import NullSpeech
from game import profile as profile_mod
from game.activities.cue_runner import CueRunner
from game.run import RunState
from story.effects import apply_effects


def make_runner(cues, window=1.0):
    return CueRunner(NullAudio(), NullSpeech(), cues, window,
                     gap_for=lambda i: 0.5)


def test_cue_runner_hits_and_misses():
    runner = make_runner(["left", "right", "center"])
    runner.update(1.0)          # first gap elapses -> cue 0 live
    assert runner.state == "active"
    assert runner.handle_key(pygame.K_LEFT) == "hit"
    runner.update(0.5)          # gap -> cue 1 live
    assert runner.handle_key(pygame.K_LEFT) == "wrong"
    runner.update(0.5)          # gap -> cue 2 live
    runner.update(1.1)          # window expires -> miss
    assert runner.done
    assert (runner.hits, runner.wrongs, runner.misses) == (1, 1, 1)
    assert runner.accuracy() == pytest.approx(1 / 3)


def test_cue_runner_countersteer_keys():
    runner = make_runner(["gust_left", "brace"])
    runner.update(1.0)
    assert runner.handle_key(pygame.K_RIGHT) == "hit"   # steer into the gust
    runner.update(0.5)
    assert runner.handle_key(pygame.K_SPACE) == "hit"   # brace
    assert runner.done and runner.hits == 2


def test_apply_effects_profile_and_run():
    profile = profile_mod.new_profile()
    run = RunState(profile, "skiff", ["shallows"], seed=3)
    msgs = apply_effects({
        "set": {"act2_started": 1},
        "add": {"affinity_odessa": 2},
        "pearls": 7,
        "almanac": "page_market_day",
        "unlock_vessel": "wavecutter",
        "salvage": 5,
        "hull": -2,
    }, profile, run)
    assert profile["qualities"]["act2_started"] == 1
    assert profile["qualities"]["affinity_odessa"] == 2
    assert profile["pearls"] == 7
    assert "page_market_day" in profile["almanac"]
    assert "wavecutter" in profile["unlocked_vessels"]
    assert run.salvage == 5
    assert run.hull == run.hull_max - 2
    assert any("pearls" in m for m in msgs)


def test_apply_effects_idempotent_unlocks():
    profile = profile_mod.new_profile()
    apply_effects({"almanac": "page_market_day"}, profile)
    apply_effects({"almanac": "page_market_day"}, profile)
    assert profile["almanac"].count("page_market_day") == 1


def test_pearls_never_negative():
    profile = profile_mod.new_profile()
    apply_effects({"pearls": -50}, profile)
    assert profile["pearls"] == 0
