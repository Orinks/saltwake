"""Memories: seen storylets stay re-readable, grouped by teller."""

from types import SimpleNamespace

import pygame

from core.audio import NullAudio
from core.scenes import SceneManager
from core.speech import NullSpeech
from game import profile as profile_mod
from scenes.memories_scene import MemoriesScene, seen_by_group
from story.engine import StoryEngine


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, unicode="")


def make_game(seen_ids):
    profile = profile_mod.new_profile()
    for sid in seen_ids:
        profile["seen_storylets"][sid] = 1
    return SimpleNamespace(speech=NullSpeech(), audio=NullAudio(), music=None,
                           scenes=SceneManager(), profile=profile,
                           story=StoryEngine())


def open_scene(game):
    scene = MemoriesScene(game)
    game.scenes.push(scene)
    return scene


def test_unseen_story_is_not_listed():
    game = make_game([])
    assert seen_by_group(game.profile, game.story) == []
    scene = open_scene(game)
    assert "Nothing to remember yet." in game.speech.history[-1]


def test_seen_storylets_group_by_teller_in_order():
    game = make_game(["odessa_01", "arrival_01", "sea_bottle_orchestra"])
    groups = seen_by_group(game.profile, game.story)
    labels = [label for label, _ in groups]
    assert labels[0].startswith("The tide that turned")   # main before NPCs
    assert "Odessa" in labels
    ids = {s.id for _, storylets in groups for s in storylets}
    assert ids == {"odessa_01", "arrival_01", "sea_bottle_orchestra"}


def test_stale_seen_ids_are_ignored():
    game = make_game(["odessa_01", "removed_in_a_later_version"])
    groups = seen_by_group(game.profile, game.story)
    ids = {s.id for _, storylets in groups for s in storylets}
    assert ids == {"odessa_01"}


def test_reading_a_memory_speaks_its_pages_again():
    game = make_game(["odessa_01"])
    scene = open_scene(game)
    scene.handle_event(key(pygame.K_RETURN))          # open the Odessa group
    scene.handle_event(key(pygame.K_RETURN))          # open "Office hours."
    assert scene.reading is not None
    first = next(s for _, group in seen_by_group(game.profile, game.story)
                 for s in group if s.id == "odessa_01")
    assert first.pages[0] in game.speech.history[-2]
    scene.handle_event(key(pygame.K_RETURN))          # second page
    assert game.speech.history[-1] == first.pages[1]
    scene.handle_event(key(pygame.K_UP))              # back a page
    assert game.speech.history[-1] == first.pages[0]
    scene.handle_event(key(pygame.K_RETURN))
    scene.handle_event(key(pygame.K_RETURN))          # past the end -> list
    assert scene.reading is None
    assert scene in game.scenes.stack


def test_escape_walks_back_out():
    game = make_game(["odessa_01"])
    scene = open_scene(game)
    scene.handle_event(key(pygame.K_RETURN))          # group -> list
    scene.handle_event(key(pygame.K_RETURN))          # list -> reading
    scene.handle_event(key(pygame.K_ESCAPE))          # reading -> list
    assert scene.reading is None
    scene.handle_event(key(pygame.K_ESCAPE))          # list -> groups
    assert scene.mode == "groups"
    scene.handle_event(key(pygame.K_ESCAPE))          # groups -> close
    assert scene not in game.scenes.stack
