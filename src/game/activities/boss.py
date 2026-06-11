"""Reach wardens: each region ends in a signature contest, turned up loud."""

from game.activities.boat_race import BoatRaceScene
from game.activities.storm_run import StormRunScene
from game.activities.dive_salvage import DiveSalvageScene
from game.activities.jetski_slalom import JetskiSlalomScene

BOSSES = {
    "regatta_champion": {
        "scene": BoatRaceScene,
        "mult": 1.25,
        "title": "The Shallows Regatta",
        "renown": 6,
        "salvage": 10,
        "quality": "cleared_shallows",
        "music": "warden",
    },
    "ferry_ghost": {
        "scene": StormRunScene,
        "mult": 1.3,
        "title": "The Pale Ferry's Wake",
        "renown": 8,
        "salvage": 14,
        "quality": "cleared_chop",
        "music": "warden",
    },
    "leviathan_wake": {
        "scene": DiveSalvageScene,
        "mult": 1.4,
        "title": "The Leviathan's Wake",
        "renown": 10,
        "salvage": 18,
        "quality": "cleared_wreckwater",
        "music": "warden",
    },
    "the_undertow": {
        "scene": StormRunScene,
        "mult": 1.55,
        "title": "The Undertow",
        "renown": 15,
        "salvage": 25,
        "quality": "cleared_glass_squall",
        "music": "undertow",
    },
}


def get_boss(kind: str) -> dict:
    return BOSSES.get(kind, BOSSES["regatta_champion"])
