"""Jet ski slalom: weave the buoy line as the tempo climbs."""

from game.activities.base import ActivityScene, ActivityResult
from game.activities.cue_runner import CueRunner
from game import boons as boons_mod


class JetskiSlalomScene(ActivityScene):
    NAME = "Jet ski slalom"
    SKILL_KEY = "slalom_skill"
    INTRO = ("A slalom line of buoys, each calling from the side you must cut around. "
             "The line starts easy and tightens. Three missed buoys and you wash out.")
    CONTROLS = "Left and right arrows carve around each buoy as it calls."

    N_BUOYS = 14
    MAX_MISSES = 3

    def __init__(self, game, run, on_complete, difficulty_mult: float = 1.0,
                 title: str | None = None):
        super().__init__(game, run, on_complete, difficulty_mult)
        if title:
            self.NAME = title
        self.runner = None
        self.free_miss_used = False

    def start_play(self):
        rng = self.run.rng
        cues = []
        side = rng.choice(("left", "right"))
        for _ in range(self.N_BUOYS):
            cues.append(side)
            # mostly alternating, with occasional repeats to punish autopilot
            side = ("right" if side == "left" else "left") if rng.random() > 0.2 else side
        window = 1.2 * self.window_scale() * (1.0 + self.skill())
        self.runner = CueRunner(self.audio, self.speech, cues, window,
                                gap_for=lambda i: max(0.45, 1.2 - i * 0.06))

    def _effective_misses(self) -> int:
        misses = self.runner.misses + self.runner.wrongs
        if misses > 0 and not self.free_miss_used and boons_mod.has_tag(self.run, "free_miss"):
            return misses - 1
        return misses

    def handle_play_key(self, event):
        outcome = self.runner.handle_key(event.key)
        if outcome == "hit":
            self.audio.tone(800, 60, vol=0.45)
        elif outcome == "wrong":
            self._note_miss()

    def update_play(self, dt):
        before = self.runner.misses
        self.runner.update(dt)
        if self.runner.misses > before:
            self._note_miss()
        if self._effective_misses() >= self.MAX_MISSES or self.runner.done:
            self._score()

    def _note_miss(self):
        misses = self.runner.misses + self.runner.wrongs
        if misses == 1 and not self.free_miss_used and boons_mod.has_tag(self.run, "free_miss"):
            self.free_miss_used = True
            boons_mod.consume_tag(self.run, "free_miss")
            self.speech.say("Otter's Grace. The miss is forgiven.", interrupt=False)
            self.audio.tone(950, 120, vol=0.4)
        else:
            self.audio.splash()

    def _score(self):
        if self.runner.state != "done":
            self.runner.state = "done"
        misses = self._effective_misses()
        cleared = self.runner.hits
        success = misses < self.MAX_MISSES and cleared >= self.N_BUOYS - self.MAX_MISSES
        self.run.spend_grit(2)
        damage = self.soak(1) if misses >= self.MAX_MISSES else 0
        if damage:
            self.run.take_damage(damage)
        if success:
            salvage = int(round((4 + cleared * 0.4) * (0.8 + self.difficulty * 0.4)))
            self.run.add_salvage(salvage)
            self.finish(ActivityResult(
                True, cleared / self.N_BUOYS, salvage=salvage, renown=2,
                stat="slaloms_cleared", grit_cost=2,
                headline="You spit spray off the last buoy and idle out clean.",
                detail=f"{cleared} buoys carved, {misses} missed."))
        else:
            self.finish(ActivityResult(
                False, cleared / self.N_BUOYS, damage=damage, grit_cost=2,
                headline="The line wins this one. You wash out in a sheet of foam.",
                detail=f"{cleared} buoys before the line got away from you."))
