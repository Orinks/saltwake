"""Boat race: thread the gates faster than the local pacer."""

from game.activities.base import ActivityScene, ActivityResult
from game.activities.cue_runner import CueRunner


class BoatRaceScene(ActivityScene):
    NAME = "Boat race"
    SKILL_KEY = "race_speed"
    MUSIC = "open_throttle"
    INTRO = ("A course of buoy gates is laid out ahead. Each gate calls from its side of "
             "the water. Hit the matching arrow, left, right, or up for dead ahead, "
             "before the gate passes. Clean gates build speed.")
    CONTROLS = "Left and right arrows steer. Up arrow holds the line through a center gate."

    N_GATES = 12

    def __init__(self, game, run, on_complete, difficulty_mult: float = 1.0,
                 title: str | None = None):
        super().__init__(game, run, on_complete, difficulty_mult)
        if title:
            self.NAME = title
        self.runner = None
        self.streak = 0
        self.best_streak = 0

    def start_play(self):
        rng = self.run.rng
        cues = [rng.choice(("left", "right", "center")) for _ in range(self.N_GATES)]
        window = 1.5 * self.window_scale()
        self.runner = CueRunner(self.audio, self.speech, cues, window,
                                gap_for=lambda i: max(0.7, 1.4 - i * 0.05))

    def handle_play_key(self, event):
        outcome = self.runner.handle_key(event.key)
        if outcome == "hit":
            self.streak += 1
            self.best_streak = max(self.best_streak, self.streak)
            self.audio.tone(700 + min(self.streak, 8) * 60, 70, vol=0.5)
        elif outcome == "wrong":
            self.streak = 0
            self.audio.splash()

    def update_play(self, dt):
        before = self.runner.misses if self.runner else 0
        self.runner.update(dt)
        if self.runner.misses > before:
            self.streak = 0
            self.audio.splash()
        if self.runner.done:
            self._score()

    def _score(self):
        accuracy = self.runner.accuracy()
        score = accuracy + self.skill() * 0.5 + min(self.best_streak, 8) * 0.01
        threshold = 0.62 + 0.06 * (self.difficulty - 1.0) * 4
        win = score >= threshold
        clips = self.runner.misses + self.runner.wrongs
        damage = self.soak(max(0, clips - 1))
        self.run.spend_grit(1)
        if damage:
            self.run.take_damage(damage)
        if win:
            salvage = int(round((5 + 4 * accuracy) * (0.8 + self.difficulty * 0.4)))
            self.run.add_salvage(salvage)
            self.finish(ActivityResult(
                True, score, salvage=salvage, damage=damage, renown=2,
                stat="races_won",
                headline="You cross the line first, engine ticking, wake still settling.",
                detail=f"{self.runner.hits} clean gates of {self.runner.total}, "
                       f"best streak {self.best_streak}."))
        else:
            salvage = 1 if accuracy > 0.4 else 0
            if salvage:
                self.run.add_salvage(salvage)
            self.finish(ActivityResult(
                False, score, salvage=salvage, damage=damage,
                headline="The pacer takes it. Their wake slaps your hull like applause for someone else.",
                detail=f"{self.runner.hits} clean gates of {self.runner.total}."))
