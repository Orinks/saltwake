"""The Chronicle as a navigable menu instead of one long report."""

from types import SimpleNamespace

import pygame

from core import clipboard
from core.audio import NullAudio
from core.scenes import SceneManager
from core.speech import NullSpeech
from game import profile as profile_mod
from scenes.chronicle_scene import (ChronicleScene, chronicle_entries,
                                    chronicle_text)


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


def test_chronicle_text_is_the_whole_record_as_lines():
    profile = profile_mod.new_profile()
    profile["tides"] = 3
    text = chronicle_text(profile)
    lines = text.splitlines()
    assert lines[0] == "Saltwake: the Chronicle of Tideborn."
    assert "Tides set out: 3" in lines
    assert len(lines) == 1 + len(chronicle_entries(profile))


def test_c_key_copies_and_confirms(monkeypatch):
    copied = []
    monkeypatch.setattr(clipboard, "copy_text", lambda t: copied.append(t) or True)
    game, scene = make_scene()
    scene.handle_event(key(pygame.K_c))
    assert copied and copied[0].startswith("Saltwake: the Chronicle")
    assert game.speech.history[-1] == "Chronicle copied to the clipboard."


def test_copy_menu_item_copies_too(monkeypatch):
    copied = []
    monkeypatch.setattr(clipboard, "copy_text", lambda t: copied.append(t) or True)
    game, scene = make_scene()
    scene.handle_event(key(pygame.K_END))     # focus the last item...
    scene.handle_event(key(pygame.K_UP))      # ...then up to "Copy the Chronicle"
    scene.handle_event(key(pygame.K_RETURN))
    assert copied
    assert scene in game.scenes.stack         # copying does not close the scene


def test_copy_failure_is_spoken(monkeypatch):
    monkeypatch.setattr(clipboard, "copy_text", lambda t: False)
    game, scene = make_scene()
    scene.handle_event(key(pygame.K_c))
    assert "Copying failed" in game.speech.history[-1]
