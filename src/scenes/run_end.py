"""End of a tide: wreck, homecoming, or victory.

Hades' core lesson lives here: a run that ends badly must still move the
story. A wreck banks half its salvage, deepens the sea-debt arc, and rolls a
wreck storylet — the town reacting to you washing in again.
"""

import pygame

from core.scenes import Scene
from game import profile as profile_mod
from scenes.storylet_scene import maybe_play


class RunEndScene(Scene):
    def __init__(self, game, run, exhausted: bool = False):
        super().__init__(game)
        self.run = run
        self.exhausted = exhausted
        self.summary_spoken = False

    def on_enter(self):
        track = {"wreck": "driftwood", "victory": "lanterns_lit"}.get(
            self.run.outcome, "homecoming")
        self.game.music.play(track)
        if not self.summary_spoken:
            self._settle()
            self.summary_spoken = True
            hook = {"wreck": "wreck", "victory": "victory"}.get(self.run.outcome,
                                                                "homecoming")
            if maybe_play(self.game, hook, on_close=self._speak_summary):
                return
        self._speak_summary()

    def _settle(self):
        profile = self.game.profile
        run = self.run
        outcome = run.outcome
        if outcome == "wreck":
            profile["wrecks"] += 1
            profile_mod.add_quality(profile, "sea_debt", 1)
            self.banked = run.salvage // 2
            renown = run.renown_earned // 2
        else:
            profile["homecomings"] += 1
            self.banked = run.salvage
            renown = run.renown_earned
            if outcome == "victory":
                profile_mod.set_quality(profile, "undertow_faced", 1)
        bonus = 1.0 + 0.1 * profile.get("tide_marks", 0)
        self.banked = int(round(self.banked * bonus))
        profile["pearls"] += self.banked
        profile["renown"] += renown
        self.renown_gained = renown
        profile["stats"]["salvage_lifetime"] += run.salvage
        profile_mod.save(profile)

    def _speak_summary(self):
        run = self.run
        if run.outcome == "wreck":
            opening = ("The sea takes the boat and, out of habit, spits you back. "
                       "You wake on the shingle below Greywater Quay, again, "
                       "with the Undertow's cold receipt in your chest.")
        elif run.outcome == "victory":
            opening = "You came back from the Glass Squall. Nobody does that. You did."
        elif self.exhausted:
            opening = "You limp home on fumes and stubbornness."
        else:
            opening = "You ride the tide home with the catch lashed down and the light failing kindly."
        level = profile_mod.renown_level(self.game.profile)
        self.speech.say(
            f"{opening} Tide {self.game.profile['tides']} is over. "
            f"Salvage banked: {self.banked} pearls. Renown gained: {self.renown_gained}, "
            f"renown level {level}. "
            f"Pearls in hand: {self.game.profile['pearls']}. "
            "Press Enter to return to Greywater Quay.")

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_RETURN, pygame.K_SPACE):
            from scenes.harbor import HarborScene
            self.game.scenes.clear_and_push(HarborScene(self.game))
        elif event.key == pygame.K_r:
            self.speech.repeat_last()
