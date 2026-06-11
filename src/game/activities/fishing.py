"""Fishing: a tension duel. Reel when the fish tires, never when it runs."""

import pygame

from game.activities.base import ActivityScene, ActivityResult


class FishingScene(ActivityScene):
    NAME = "Fishing"
    SKILL_KEY = "fishing_skill"
    MUSIC = "line_and_lure"
    INTRO = ("Something heavy noses the bait. When the line sings high, the fish is tired: "
             "reel with space. When the tone drops low, it is running: hands off, or give "
             "line with the down arrow to ease the strain. Reel against a run and the line snaps.")
    CONTROLS = "Space reels. Down arrow gives line. Listen for the high and low tones."

    def __init__(self, game, run, on_complete, difficulty_mult: float = 1.0,
                 title: str | None = None):
        super().__init__(game, run, on_complete, difficulty_mult)
        if title:
            self.NAME = title
        self.progress = 0.0      # 100 lands the fish
        self.tension = 20.0      # 100 snaps the line
        self.state = "tire"
        self.state_timer = 0.0
        self.state_len = 3.0
        self.tone_timer = 0.0
        self.fish_size = 1.0

    def start_play(self):
        rng = self.run.rng
        self.fish_size = 0.8 + rng.random() * 0.6 + self.difficulty * 0.2
        self._set_state("tire", rng)

    def _set_state(self, state, rng=None):
        rng = rng or self.run.rng
        self.state = state
        self.state_timer = 0.0
        self.state_len = rng.uniform(2.0, 3.5) if state == "tire" else rng.uniform(1.5, 3.0)
        if state == "run":
            self.speech.say("It runs!", interrupt=True)
        else:
            self.speech.say("It tires. Reel!", interrupt=True)

    def handle_play_key(self, event):
        if event.key == pygame.K_SPACE:
            if self.state == "tire":
                gain = 6.0 * (1.0 + self.skill())
                self.progress += gain
                self.tension += 2.0
                self.audio.tone(900, 50, vol=0.4)
            else:
                self.tension += 18.0 * self.fish_size
                self.audio.warning()
        elif event.key == pygame.K_DOWN:
            self.tension = max(0.0, self.tension - 8.0)
            self.progress = max(0.0, self.progress - 1.5)
            self.audio.tone(330, 60, vol=0.35)

    def update_play(self, dt):
        self.state_timer += dt
        self.tone_timer += dt
        if self.tone_timer >= 0.8:
            self.tone_timer = 0.0
            freq = 880 if self.state == "tire" else 200
            self.audio.tone(freq, 200, vol=0.5,
                            shape="sine" if self.state == "tire" else "square")
        if self.state == "run":
            self.tension += dt * 4.0 * self.fish_size * (1.0 - self.skill() * 0.5)
        else:
            self.tension = max(0.0, self.tension - dt * 5.0)
        if self.state_timer >= self.state_len:
            self._set_state("run" if self.state == "tire" else "tire")
        if self.tension >= 100.0:
            self.run.spend_grit(1)
            self.finish(ActivityResult(
                False, self.progress / 100,
                headline="The line parts with a crack like a struck match.",
                detail="The water goes still and smug."))
        elif self.progress >= 100.0:
            salvage = int(round(6 * self.fish_size * (0.8 + self.difficulty * 0.4)))
            self.run.add_salvage(salvage)
            self.run.supplies += 1
            self.run.spend_grit(1)
            self.finish(ActivityResult(
                True, 1.0, salvage=salvage, renown=1, stat="fish_caught",
                headline="It comes over the rail in a silver arc, heavy as an argument won.",
                detail="One supply gained, and salvage from the trade stalls."))
