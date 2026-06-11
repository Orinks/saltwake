"""The Chronicle as a navigable menu instead of one long report."""

from types import SimpleNamespace

import pygame

from core.audio import NullAudio
from core.scenes import SceneManager
from core.speech import NullSpeech
from game import profile as profile_mod
from scenes.chronicle_scene import ChronicleScene, chronicle_entries


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, unicode="")


def make_scene(profile=None):
    game = SimpleNamespace(speech=NullSpeech(), audio=NullAudio(), music=None,
                           scenes=SceneManager(), profile=profile or profile_mod.new_profile())
    scene = ChronicleScene(game)
    game.scenes.push(scene)
    return game, scene


def test_entries_cover_the_record():
    profile = profile_mod.new_profile()
    profile["tides"] = 7
    profile["stats"]["rescues"] = 2
    spoken = [text for text, _ in chronicle_entries(profile)]
    assert "Tides set out: 7" in spoken
    assert "Souls rescued: 2" in spoken
    assert len(spoken) >= 14
    assert all(help_text for _, help_text in chronicle_entries(profile))


def test_arrowing_speaks_each_entry():
    game, scene = make_scene()
    scene.handle_event(key(pygame.K_DOWN))
    assert "Homecomings" in game.speech.history[-1]
    scene.handle_event(key(pygame.K_DOWN))
    assert "Wrecks" in game.speech.history[-1]


def test_enter_reads_entry_with_flavor():
    game, scene = make_scene()
    scene.handle_event(key(pygame.K_RETURN))
    last = game.speech.history[-1]
    assert "Tides set out" in last and "cast off" in last


def test_escape_and_close_item_pop():
    game, scene = make_scene()
    scene.handle_event(key(pygame.K_ESCAPE))
    assert scene not in game.scenes.stack
