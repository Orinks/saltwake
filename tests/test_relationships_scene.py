"""Ties: relationship levels spoken by name, gated on having met people."""

from types import SimpleNamespace

import pygame

from core.audio import NullAudio
from core.scenes import SceneManager
from core.speech import NullSpeech
from game import profile as profile_mod
from scenes.relationships_scene import (RelationshipsScene, closeness,
                                        relationship_entries)


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, unicode="")


def make_scene(profile):
    game = SimpleNamespace(speech=NullSpeech(), audio=NullAudio(), music=None,
                           scenes=SceneManager(), profile=profile)
    scene = RelationshipsScene(game)
    game.scenes.push(scene)
    return game, scene


def test_closeness_levels_scale_with_affinity():
    assert closeness(0) == "strangers, so far"
    assert closeness(1) == "newly acquainted"
    assert closeness(3) == "warming to you"
    assert closeness(5) == "trusted"
    assert closeness(7) == "fast friends"
    assert closeness(12) == "family in all but paper"


def test_only_met_characters_are_listed():
    profile = profile_mod.new_profile()
    assert relationship_entries(profile) == []
    profile["qualities"]["met_odessa"] = 1
    profile["qualities"]["affinity_odessa"] = 4
    entries = relationship_entries(profile)
    assert len(entries) == 1
    assert entries[0][0] == "Odessa, the harbormaster: trusted"
    assert "Regard 4." in entries[0][1]


def test_keeper_and_liss_appear_only_after_their_story_gates():
    profile = profile_mod.new_profile()
    profile["qualities"].update({"met_keeper": 1, "affinity_keeper": 2})
    spoken = [text for text, _ in relationship_entries(profile)]
    assert any("Edras" in t for t in spoken)
    assert not any("Liss" in t for t in spoken)
    profile["qualities"]["liss_saved"] = 1
    spoken = [text for text, _ in relationship_entries(profile)]
    assert any("Liss" in t for t in spoken)


def test_bonds_are_named_in_the_detail():
    profile = profile_mod.new_profile()
    profile["qualities"].update(
        {"met_odessa": 1, "affinity_odessa": 8, "odessa_sworn": 1})
    text, help_text = relationship_entries(profile)[0]
    assert "family in all but paper" in text
    assert "boards dry, lines free" in help_text.lower()


def test_enter_reads_the_detail():
    profile = profile_mod.new_profile()
    profile["qualities"].update({"met_mirabel": 1, "affinity_mirabel": 2})
    game, scene = make_scene(profile)
    scene.handle_event(key(pygame.K_RETURN))
    last = game.speech.history[-1]
    assert "Mirabel" in last and "Regard 2." in last


def test_empty_quay_offers_guidance_and_escape_pops():
    game, scene = make_scene(profile_mod.new_profile())
    assert "Nobody at the quay knows you yet." in game.speech.history[-1]
    scene.handle_event(key(pygame.K_ESCAPE))
    assert scene not in game.scenes.stack
