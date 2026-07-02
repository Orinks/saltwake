"""Keepsakes: found rarely, carried with a hint, always deliverable."""

import random
from types import SimpleNamespace

import pygame

from core.audio import NullAudio
from core.scenes import SceneManager
from core.speech import NullSpeech
from game import keepsakes
from game import profile as profile_mod
from scenes.sea_chest_scene import SeaChestScene, sea_chest_entries
from story.effects import apply_effects
from story.engine import StoryEngine


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, unicode="")


def all_gates_open() -> dict:
    profile = profile_mod.new_profile()
    profile["qualities"].update(
        {k.get("after"): 1 for k in keepsakes.all_keepsakes() if "after" in k})
    return profile


def test_every_keepsake_has_a_delivery_quest():
    """Each keepsake must be waited for somewhere: a storylet that requires
    carrying it and an effect that delivers it."""
    engine = StoryEngine()
    required, delivered = set(), set()
    settable = set()
    for s in engine.storylets.values():
        for req in s.requires:
            for name in ([req.get("q")] if "q" in req else []):
                if name and name.startswith("keepsake_"):
                    required.add(name.removeprefix("keepsake_"))
        for effects in [s.effects] + [c.get("effects", {}) for c in s.choices]:
            if "deliver_keepsake" in effects:
                delivered.add(effects["deliver_keepsake"])
            settable |= set(effects.get("set", {}))
            settable |= set(effects.get("add", {}))
    ids = {k["id"] for k in keepsakes.all_keepsakes()}
    assert len(ids) == len(keepsakes.all_keepsakes()), "duplicate keepsake ids"
    assert ids <= required, f"keepsakes nobody waits for: {ids - required}"
    assert ids <= delivered, f"keepsakes nobody can deliver: {ids - delivered}"
    for k in keepsakes.all_keepsakes():
        assert k["name"] and k["found"] and k["hint"], k["id"]
        if "after" in k:
            assert k["after"] in settable, \
                f"{k['id']} gates on unknown quality {k['after']}"


def test_pool_respects_gates_carrying_and_delivery():
    profile = profile_mod.new_profile()
    early = {k["id"] for k in keepsakes.pool(profile)}
    assert "liss_slate" not in early          # gated behind the finale
    profile = all_gates_open()
    assert len(keepsakes.pool(profile)) == len(keepsakes.all_keepsakes())
    rng = random.Random(11)
    first = keepsakes.draw(profile, rng)
    assert first["id"] in profile["keepsakes"]
    assert first["id"] not in {k["id"] for k in keepsakes.pool(profile)}
    keepsakes.deliver(profile, first["id"])
    assert profile["keepsakes"] == []
    assert profile["keepsakes_delivered"] == [first["id"]]
    assert first["id"] not in {k["id"] for k in keepsakes.pool(profile)}


def test_effects_grant_and_deliver():
    profile = all_gates_open()
    messages = apply_effects({"keepsake": "rens_thimble"}, profile)
    assert profile["keepsakes"] == ["rens_thimble"]
    assert "brass thimble" in messages[0]
    assert apply_effects({"keepsake": "rens_thimble"}, profile) == []  # no dupes
    apply_effects({"deliver_keepsake": "rens_thimble"}, profile)
    assert profile["keepsakes_delivered"] == ["rens_thimble"]


def test_context_exposes_carried_and_delivered():
    profile = all_gates_open()
    keepsakes.grant(profile, "odessa_whistle")
    ctx = profile_mod.build_context(profile)
    assert ctx["keepsake_odessa_whistle"] == 1
    assert ctx["keepsakes_found"] == 1
    keepsakes.deliver(profile, "odessa_whistle")
    ctx = profile_mod.build_context(profile)
    assert "keepsake_odessa_whistle" not in ctx
    assert ctx["delivered_odessa_whistle"] == 1
    assert ctx["keepsakes_delivered"] == 1


def test_delivery_storylet_fires_when_carrying():
    engine = StoryEngine()
    profile = all_gates_open()
    keepsakes.grant(profile, "odessa_whistle")
    ctx = profile_mod.build_context(profile)
    seen = dict.fromkeys(
        ("odessa_01", "odessa_02", "odessa_03", "odessa_04",
         "epilogue_odessa"), 1)   # arc beats already heard; delivery is next
    picked = engine.pick("talk_odessa", ctx, seen)
    assert picked.id == "deliver_odessa_whistle"


def test_dive_can_surface_a_keepsake():
    from scenes.expedition import ExpeditionScene
    profile = all_gates_open()
    game = SimpleNamespace(speech=NullSpeech(), audio=NullAudio(),
                           scenes=SceneManager(), profile=profile)
    scene = ExpeditionScene.__new__(ExpeditionScene)
    scene.game = game
    scene.run = SimpleNamespace(rng=SimpleNamespace(random=lambda: 0.0,
                                                    choice=random.Random(5).choice))
    assert scene._maybe_keepsake() is True
    assert len(profile["keepsakes"]) == 1
    assert "sea chest" in game.speech.history[-1]


def test_sea_chest_speaks_carried_and_delivered():
    profile = all_gates_open()
    keepsakes.grant(profile, "rens_thimble")
    keepsakes.grant(profile, "brick_medal")
    keepsakes.deliver(profile, "brick_medal")
    entries = sea_chest_entries(profile)
    assert entries[0][0] == "A brass thimble, sea-smoothed"
    assert "given home" in entries[1][0]
    game = SimpleNamespace(speech=NullSpeech(), audio=NullAudio(), music=None,
                           scenes=SceneManager(), profile=profile)
    scene = SeaChestScene(game)
    game.scenes.push(scene)
    assert "1 carried, 1 given home" in game.speech.history[0]
    scene.handle_event(key(pygame.K_RETURN))
    assert "Brinehouse" in game.speech.history[-1]
    scene.handle_event(key(pygame.K_ESCAPE))
    assert scene not in game.scenes.stack
