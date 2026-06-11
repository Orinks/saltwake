"""The paged manual: structure and navigation behavior."""

from types import SimpleNamespace

import pygame

from core.audio import NullAudio
from core.scenes import SceneManager
from core.speech import NullSpeech
from scenes.help_scene import HELP_PAGES, HelpScene


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k)


def make_scene():
    game = SimpleNamespace(speech=NullSpeech(), audio=NullAudio(),
                           music=None, scenes=SceneManager())
    scene = HelpScene(game)
    game.scenes.push(scene)
    return game, scene


def test_pages_are_well_formed():
    assert len(HELP_PAGES) >= 8
    titles = [t for t, _ in HELP_PAGES]
    assert len(set(titles)) == len(titles)
    for title, lines in HELP_PAGES:
        assert title and lines
        assert all(isinstance(line, str) and line for line in lines)


def test_open_announces_controls_and_first_page():
    game, _ = make_scene()
    opening = game.speech.history[-1]
    assert "Left and Right arrows change pages" in opening
    assert f"Page 1 of {len(HELP_PAGES)}" in opening


def test_page_cycling_wraps_both_ways():
    game, scene = make_scene()
    scene.handle_event(key(pygame.K_RIGHT))
    assert scene.page == 1
    assert "Page 2" in game.speech.history[-1]
    scene.handle_event(key(pygame.K_LEFT))
    scene.handle_event(key(pygame.K_LEFT))
    assert scene.page == len(HELP_PAGES) - 1
    assert f"Page {len(HELP_PAGES)}" in game.speech.history[-1]


def test_line_reading_clamps_at_ends():
    game, scene = make_scene()
    lines = HELP_PAGES[0][1]
    scene.handle_event(key(pygame.K_DOWN))
    assert game.speech.history[-1] == lines[0]
    for _ in range(len(lines) + 3):
        scene.handle_event(key(pygame.K_DOWN))
    assert game.speech.history[-1] == lines[-1]
    scene.handle_event(key(pygame.K_UP))
    assert game.speech.history[-1] == lines[-2]


def test_enter_reads_whole_page_and_page_change_resets_line():
    game, scene = make_scene()
    scene.handle_event(key(pygame.K_DOWN))
    scene.handle_event(key(pygame.K_RETURN))
    title, lines = HELP_PAGES[0]
    assert game.speech.history[-1] == f"{title}. " + " ".join(lines)
    scene.handle_event(key(pygame.K_RIGHT))
    assert scene.line == -1


def test_escape_pops_scene():
    game, scene = make_scene()
    scene.handle_event(key(pygame.K_ESCAPE))
    assert scene not in game.scenes.stack
