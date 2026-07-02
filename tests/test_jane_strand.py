"""The vessel is visible to story requirements, and the Jane strand uses it."""

from types import SimpleNamespace

import pygame

from core.audio import NullAudio
from core.scenes import SceneManager
from core.speech import NullSpeech
from game import profile as profile_mod
from scenes.run_end import RunEndScene
from scenes.storylet_scene import StoryletScene
from story.engine import StoryEngine


def fake_run(vessel_id="skiff", salvage=0, outcome="homecoming"):
    return SimpleNamespace(vessel_id=vessel_id, salvage=salvage, hull=5,
                           region_index=0, renown_earned=0, outcome=outcome)


def test_build_context_names_the_hull_under_you():
    profile = profile_mod.new_profile()
    ctx = profile_mod.build_context(profile, fake_run("lantern_jane"))
    assert ctx["vessel_lantern_jane"] == 1
    assert "vessel_lantern_jane" not in profile_mod.build_context(profile)


def test_jane_storylets_require_being_aboard_her():
    engine = StoryEngine()
    profile = profile_mod.new_profile()
    seen = profile["seen_storylets"]
    aboard = profile_mod.build_context(profile, fake_run("lantern_jane"))
    ashore_hull = profile_mod.build_context(profile, fake_run("skiff"))
    assert engine.pick("embark", aboard, seen).id == "embark_jane_first"
    assert engine.pick("embark", ashore_hull, seen).id != "embark_jane_first"
    assert engine.pick("homecoming", aboard, seen).id == "homecoming_jane_sailed"
    aboard["liss_saved"] = 1
    seen["boss_undertow_first"] = 1   # always seen before the finale in play
    assert engine.pick("boss_the_undertow", aboard, seen).id == "boss_undertow_jane_return"


def test_run_end_storylets_see_the_finished_run():
    """Regression: the run-end hook used to drop the run, so beats gated on
    salvage aboard (homecoming_rich) or the vessel could never fire."""
    profile = profile_mod.new_profile()
    profile["homecomings"] = 5   # keep the early-homecoming beats ineligible
    game = SimpleNamespace(speech=NullSpeech(), audio=NullAudio(),
                           music=SimpleNamespace(play=lambda *_: None),
                           scenes=SceneManager(), profile=profile,
                           story=StoryEngine())
    run = fake_run("skiff", salvage=45)
    scene = RunEndScene(game, run)
    game.scenes.push(scene)
    top = game.scenes.current
    assert isinstance(top, StoryletScene)
    assert top.storylet.id == "homecoming_rich"


def test_wrecking_the_jane_has_its_own_answer():
    engine = StoryEngine()
    profile = profile_mod.new_profile()
    profile["wrecks"] = 6
    profile["qualities"]["liss_saved"] = 1
    seen = {"wreck_liss_scolding": 1}   # her scolding already delivered
    ctx = profile_mod.build_context(profile, fake_run("lantern_jane", outcome="wreck"))
    ctx["undertow_faced"] = 1
    assert engine.pick("wreck", ctx, seen).id == "wreck_jane"
