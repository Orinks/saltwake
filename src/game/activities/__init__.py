"""Activity registry: maps node kinds to playable scenes."""


def get_activity_class(kind: str):
    from game.activities.boat_race import BoatRaceScene
    from game.activities.jetski_slalom import JetskiSlalomScene
    from game.activities.storm_run import StormRunScene
    from game.activities.dive_salvage import DiveSalvageScene
    from game.activities.fishing import FishingScene
    from game.activities.rescue_tow import RescueTowScene

    return {
        "boat_race": BoatRaceScene,
        "jetski_slalom": JetskiSlalomScene,
        "storm_run": StormRunScene,
        "dive_salvage": DiveSalvageScene,
        "fishing": FishingScene,
        "rescue_tow": RescueTowScene,
    }[kind]
