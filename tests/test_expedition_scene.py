"""Expedition scene transitions. Regression for the region-end softlock:
pressing on into the next region left the scene in region_end mode, so
on_enter returned without presenting a row and the game hung."""

from types import SimpleNamespace

import pygame

from core.audio import NullAudio
from core.scenes import SceneManager
from core.speech import NullSpeech
from game import profile as profile_mod
from game.run import RunState
from scenes.expedition import ExpeditionScene
from story.engine import StoryEngine


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, unicode="")


def make_scene(region_ids):
    game = SimpleNamespace(speech=NullSpeech(), audio=NullAudio(),
                           music=SimpleNamespace(play=lambda *a, **k: None),
                           scenes=SceneManager(), profile=profile_mod.new_profile(),
                           story=StoryEngine(story_dir="__no_story_dir__"))
    run = RunState(game.profile, "skiff", region_ids, seed=7)
    scene = ExpeditionScene(game, run)
    game.scenes.push(scene)
    return game, scene, run


def test_press_on_into_the_next_region_presents_its_first_row():
    game, scene, run = make_scene(["shallows", "chop"])
    scene._region_end_menu()
    assert scene.mode == "region_end"
    scene.handle_event(key(pygame.K_RETURN))  # first item: press on
    assert run.region_index == 1
    assert scene.mode == "row"
    assert scene.menu is not None, "the new region's heading menu must open"
    assert any("Chop" in line for line in game.speech.history), \
        "the new region should be announced"


def test_turning_for_home_from_region_end_ends_the_run():
    game, scene, run = make_scene(["shallows", "chop"])
    scene._region_end_menu()
    scene.handle_event(key(pygame.K_DOWN))    # focus: turn for home
    scene.handle_event(key(pygame.K_RETURN))
    assert run.over and run.outcome == "homecoming"
