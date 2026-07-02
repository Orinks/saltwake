"""The loose-page pool, the almanac_loose effect, and the volume reader."""

import random
from types import SimpleNamespace

import pygame

from core.audio import NullAudio
from core.scenes import SceneManager
from core.speech import NullSpeech
from game import almanac
from game import profile as profile_mod
from scenes.almanac_scene import AlmanacScene
from story.effects import apply_effects


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, unicode="")


def test_data_shape():
    assert len(almanac.pages()) >= 50
    assert len(almanac.volumes()) == 5
    volume_ids = {v["id"] for v in almanac.volumes()}
    for page in almanac.pages():
        assert page["volume"] in volume_ids, page["id"]


def test_loose_pool_excludes_held_and_gated_pages():
    profile = profile_mod.new_profile()
    pool = almanac.loose_pool(profile)
    assert pool, "a fresh profile should have loose pages to find"
    assert all("after" not in p for p in pool), \
        "story-gated pages must stay out of the pool until their gate opens"
    held = pool[0]["id"]
    profile["almanac"].append(held)
    assert held not in [p["id"] for p in almanac.loose_pool(profile)]
    before = len(almanac.loose_pool(profile))
    profile["qualities"]["liss_saved"] = 1
    assert len(almanac.loose_pool(profile)) > before


def test_draw_loose_never_repeats_and_drains():
    profile = profile_mod.new_profile()
    profile["qualities"].update(
        {"liss_saved": 1, "jane_raised": 1, "brothers_reconciled": 1})
    rng = random.Random(7)
    drawn = []
    while True:
        page = almanac.draw_loose(profile, rng)
        if page is None:
            break
        drawn.append(page["id"])
    assert len(drawn) == len(set(drawn))
    assert len(drawn) == sum(1 for p in almanac.pages() if p.get("loose"))


def test_almanac_loose_effect_grants_and_reports_title():
    profile = profile_mod.new_profile()
    messages = apply_effects({"almanac_loose": 1}, profile)
    assert len(profile["almanac"]) == 1
    page = almanac.page_by_id(profile["almanac"][0])
    assert page["title"] in messages[0]


def test_almanac_loose_effect_reports_an_empty_pool():
    profile = profile_mod.new_profile()
    profile["qualities"].update(
        {"liss_saved": 1, "jane_raised": 1, "brothers_reconciled": 1})
    profile["almanac"] = [p["id"] for p in almanac.pages() if p.get("loose")]
    messages = apply_effects({"almanac_loose": 1}, profile)
    assert "already hold" in messages[0]


def make_scene(profile):
    game = SimpleNamespace(speech=NullSpeech(), audio=NullAudio(),
                           music=SimpleNamespace(play=lambda *_: None),
                           scenes=SceneManager(), profile=profile)
    scene = AlmanacScene(game)
    game.scenes.push(scene)
    return game, scene


def test_empty_almanac_offers_guidance():
    game, scene = make_scene(profile_mod.new_profile())
    assert "0 of" in game.speech.history[0]
    scene.handle_event(key(pygame.K_ESCAPE))
    assert scene not in game.scenes.stack


def test_volume_navigation_and_reading():
    profile = profile_mod.new_profile()
    profile["almanac"] = ["page_market_day"]
    game, scene = make_scene(profile)
    assert "1 of" in game.speech.history[0]
    scene.handle_event(key(pygame.K_RETURN))          # open The Town
    assert scene.mode == "pages"
    scene.handle_event(key(pygame.K_RETURN))          # read the page
    assert scene.reading is not None
    assert "Market day" in game.speech.history[-1]
    scene.handle_event(key(pygame.K_ESCAPE))          # back to page list
    assert scene.reading is None
    scene.handle_event(key(pygame.K_ESCAPE))          # back to volumes
    assert scene.mode == "volumes"


def test_expedition_haul_can_carry_a_page():
    from scenes.expedition import ExpeditionScene
    profile = profile_mod.new_profile()
    profile["qualities"]["met_nereus"] = 1
    game = SimpleNamespace(speech=NullSpeech(), audio=NullAudio(),
                           scenes=SceneManager(), profile=profile)
    run = SimpleNamespace(rng=random.Random(3))
    scene = ExpeditionScene.__new__(ExpeditionScene)
    scene.game = game
    scene.run = run
    scene._maybe_loose_page(1.0)                      # certain drop
    assert len(profile["almanac"]) == 1
    assert "Drowned Almanac" in game.speech.history[-1]
    profile["qualities"]["met_nereus"] = 0
    scene._maybe_loose_page(1.0)                      # gated off again
    assert len(profile["almanac"]) == 1
