"""Achievements: definitions are sound, unlocks fire once, announcements queue."""

from types import SimpleNamespace

import pygame

from core.audio import NullAudio
from core.scenes import SceneManager
from core.speech import NullSpeech
from game import achievements
from game import profile as profile_mod
from scenes.achievements_scene import AchievementsScene
from story.engine import StoryEngine

# Quality names granted outside storylet effects.
ENGINE_QUALITIES = {
    "undertow_faced", "sea_debt",                        # run-end settlement
    "cleared_shallows", "cleared_chop",                  # boss victories
    "cleared_wreckwater", "cleared_glass_squall",
}


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, unicode="")


def _requirement_names(reqs):
    for r in reqs:
        if "any" in r or "all" in r:
            yield from _requirement_names(r.get("any", []) + r.get("all", []))
        else:
            yield r


def test_definitions_are_substantial_and_unique():
    achs = achievements.all_achievements()
    assert len(achs) >= 100
    ids = [a["id"] for a in achs]
    assert len(ids) == len(set(ids))
    category_ids = {c["id"] for c in achievements.categories()}
    for ach in achs:
        assert ach["category"] in category_ids, ach["id"]
        assert ach["name"] and ach["description"], ach["id"]
        assert ach.get("requires"), f"{ach['id']} has no requirements"


def test_every_requirement_is_earnable():
    """Each "q" is a real quality or context key; each "seen" storylet exists."""
    engine = StoryEngine()
    settable = set(ENGINE_QUALITIES)
    for s in engine.storylets.values():
        for effects in [s.effects] + [c.get("effects", {}) for c in s.choices]:
            settable |= set(effects.get("set", {}))
            settable |= set(effects.get("add", {}))
    ctx_keys = set(achievements.build_context(profile_mod.new_profile()))
    for ach in achievements.all_achievements():
        for req in _requirement_names(ach["requires"]):
            if "seen" in req:
                assert req["seen"] in engine.storylets, \
                    f"{ach['id']} watches unknown storylet {req['seen']}"
            elif "q" in req:
                assert req["q"] in settable or req["q"] in ctx_keys, \
                    f"{ach['id']} gates on unknown quality {req['q']}"


def test_unlocks_fire_once_and_persist():
    profile = profile_mod.new_profile()
    assert achievements.check_new(profile) == []
    profile["tides"] = 1
    new = achievements.check_new(profile)
    assert [a["id"] for a in new] == ["tideborn"]
    assert "tideborn" in profile["achievements"]
    assert achievements.check_new(profile) == []          # no re-unlock


def test_announce_queues_name_and_description():
    game = SimpleNamespace(speech=NullSpeech(), audio=NullAudio(),
                           profile=profile_mod.new_profile())
    game.profile["stats"]["races_won"] = 5
    new = achievements.announce(game)
    assert {a["id"] for a in new} == {"race_1", "race_5"}
    spoken = " ".join(game.speech.history)
    assert "Achievement unlocked: First Across the Line." in spoken
    assert "I Don't Lap Traffic" in spoken


def make_scene(profile):
    game = SimpleNamespace(speech=NullSpeech(), audio=NullAudio(), music=None,
                           scenes=SceneManager(), profile=profile)
    scene = AchievementsScene(game)
    game.scenes.push(scene)
    return game, scene


def test_scene_counts_and_navigation():
    profile = profile_mod.new_profile()
    profile["tides"] = 1
    achievements.check_new(profile)
    game, scene = make_scene(profile)
    assert "1 of" in game.speech.history[0]
    scene.handle_event(key(pygame.K_RETURN))     # open The Tide That Turned
    assert scene.mode == "list"
    scene.handle_event(key(pygame.K_RETURN))     # read the first entry
    assert "Tideborn, unlocked" in game.speech.history[-1]
    scene.handle_event(key(pygame.K_ESCAPE))     # back to categories
    assert scene.mode == "categories"
    scene.handle_event(key(pygame.K_ESCAPE))
    assert scene not in game.scenes.stack


def test_hidden_achievements_stay_secret_until_unlocked():
    profile = profile_mod.new_profile()
    game, scene = make_scene(profile)
    hidden = next(a for a in achievements.all_achievements() if a.get("hidden"))
    label, detail = scene._entry(hidden)
    assert hidden["name"] not in label
    assert achievements.HIDDEN_NAME in label
    profile["achievements"][hidden["id"]] = 0
    label, detail = scene._entry(hidden)
    assert hidden["name"] in label and "unlocked" in label
    assert detail == hidden["description"]


def test_saved_unlocks_survive_a_profile_merge(monkeypatch):
    from core import savegame
    saved = profile_mod.new_profile()
    saved["achievements"]["tideborn"] = 3
    del saved["stats"]  # an old save missing newer keys still backfills
    monkeypatch.setattr(savegame, "load_profile", lambda: saved)
    rebuilt = profile_mod.load_or_create()
    assert rebuilt["achievements"] == {"tideborn": 3}
    assert rebuilt["stats"]["races_won"] == 0
