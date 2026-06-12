"""Choice responses are read like pages, so the menu that resumes under the
scene can never talk over them. Regression for choices that appeared to
respond silently (the response was queued and immediately interrupted)."""

from types import SimpleNamespace

import pygame

from core.audio import NullAudio
from core.scenes import SceneManager
from core.speech import NullSpeech
from game import profile as profile_mod
from scenes.storylet_scene import StoryletScene
from story.engine import StoryEngine, Storylet


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, unicode="")


def make_game():
    return SimpleNamespace(speech=NullSpeech(), audio=NullAudio(), music=None,
                           scenes=SceneManager(), profile=profile_mod.new_profile(),
                           story=StoryEngine(story_dir="__no_story_dir__"))


def play(game, raw, *extra_raw):
    for other in extra_raw:
        game.story.storylets[other["id"]] = Storylet(other)
    storylet = Storylet(raw)
    game.story.storylets[storylet.id] = storylet
    scene = StoryletScene(game, storylet)
    game.scenes.push(scene)
    return scene


def to_first_choice(scene):
    scene.handle_event(key(pygame.K_RETURN))  # past the only page -> choices
    scene.handle_event(key(pygame.K_RETURN))  # pick the focused choice


def test_choice_response_is_read_before_the_scene_closes():
    game = make_game()
    scene = play(game, {
        "id": "t1", "pages": ["page one"],
        "choices": [{"label": "Ask.", "response": ["line one", "line two"]}],
    })
    to_first_choice(scene)
    assert scene.mode == "response"
    assert scene in game.scenes.stack
    assert "line one" in game.speech.history
    assert "line two" not in game.speech.history
    scene.handle_event(key(pygame.K_RETURN))
    assert game.speech.history[-1] == "line two"
    assert scene in game.scenes.stack
    scene.handle_event(key(pygame.K_RETURN))  # past the last line -> close
    assert scene not in game.scenes.stack


def test_response_supports_reread_and_escape():
    game = make_game()
    scene = play(game, {
        "id": "t2", "pages": ["page one"],
        "choices": [{"label": "Ask.", "response": ["line one", "line two"]}],
    })
    to_first_choice(scene)
    scene.handle_event(key(pygame.K_RETURN))      # line two
    scene.handle_event(key(pygame.K_UP))          # back to line one
    assert game.speech.history[-1] == "line one"
    scene.handle_event(key(pygame.K_ESCAPE))
    assert scene not in game.scenes.stack


def test_effect_messages_are_part_of_the_readable_response():
    game = make_game()
    scene = play(game, {
        "id": "t3", "pages": ["page one"],
        "choices": [{"label": "Ask.",
                     "effects": {"add": {"affinity_nereus": 1}},
                     "response": ["line one"]}],
    })
    to_first_choice(scene)
    assert "Nereus thinks a little better of you." in scene.response_lines


def test_choice_without_response_closes_immediately():
    game = make_game()
    scene = play(game, {
        "id": "t4", "pages": ["page one"],
        "choices": [{"label": "Leave."}],
    })
    to_first_choice(scene)
    assert scene not in game.scenes.stack


def test_goto_still_chains_to_the_next_storylet():
    game = make_game()
    scene = play(game, {
        "id": "t5", "pages": ["page one"],
        "choices": [{"label": "Ask.", "response": ["bridge line"], "goto": "t5_next"}],
    }, {"id": "t5_next", "title": "Next.", "pages": ["next page"]})
    to_first_choice(scene)
    assert scene in game.scenes.stack
    assert scene.storylet.id == "t5_next"
    assert scene.mode == "pages"
    assert "bridge line" in game.speech.history
    assert "next page" in game.speech.history


def test_every_shipped_choice_has_a_response_or_a_goto():
    """Data audit: a choice with neither response nor goto plays silently."""
    engine = StoryEngine()
    assert engine.storylets, "story data should load"
    for storylet in engine.storylets.values():
        for choice in storylet.choices:
            assert choice.get("response") or choice.get("goto"), (
                f"{storylet.source}: {storylet.id} choice "
                f"{choice.get('label', '?')!r} has no response and no goto")
