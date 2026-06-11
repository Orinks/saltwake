"""Storm run: counter-steer the gusts, brace for the waves, keep the hull."""

from game.activities.base import ActivityScene, ActivityResult
from game.activities.cue_runner import CueRunner


class StormRunScene(ActivityScene):
    NAME = "Storm crossing"
    SKILL_KEY = "storm_skill"
    MUSIC = "teeth_of_the_wind"
    INTRO = ("A wall of weather between you and the far side. Gusts hit from the sides: "
             "steer INTO them, press the arrow opposite the gust. When a wave rises dead "
             "ahead, brace with the down arrow. Every mistake costs hull.")
    CONTROLS = ("Gust on the left: press right. Gust on the right: press left. "
                "Deep tone ahead: press down to brace.")

    N_CUES = 10

    def __init__(self, game, run, on_complete, difficulty_mult: float = 1.0,
                 title: str | None = None):
        super().__init__(game, run, on_complete, difficulty_mult)
        if title:
            self.NAME = title
        self.runner = None
        self.hull_lost = 0

    def start_play(self):
        rng = self.run.rng
        cues = [rng.choice(("gust_left", "gust_right", "brace", "gust_left", "gust_right"))
                for _ in range(self.N_CUES)]
        window = 1.6 * self.window_scale() * (1.0 + self.skill())
        self.runner = CueRunner(self.audio, self.speech, cues, window,
                                gap_for=lambda i: max(0.8, 1.6 - i * 0.05))

    def handle_play_key(self, event):
        outcome = self.runner.handle_key(event.key)
        if outcome == "hit":
            self.audio.wave_wash()
        elif outcome == "wrong":
            self._hit_hull()

    def update_play(self, dt):
        before = self.runner.misses
        self.runner.update(dt)
        if self.runner.misses > before:
            self._hit_hull()
        if self.run.over:
            self.finish(ActivityResult(
                False, 0.0, damage=self.hull_lost, grit_cost=2,
                headline="The storm takes the hull apart around you.",
                detail="Cold water closes over the deck."))
            return
        if self.runner.done:
            self._score()

    def _hit_hull(self):
        damage = self.soak(2)
        if damage:
            self.run.take_damage(damage)
            self.hull_lost += damage
        self.audio.damage()
        self.speech.say(f"Hull {self.run.hull}.", interrupt=False)

    def _score(self):
        accuracy = self.runner.accuracy()
        self.run.spend_grit(2)
        success = accuracy >= 0.6
        if success:
            salvage = int(round((6 + 5 * accuracy) * (0.8 + self.difficulty * 0.4)))
            self.run.add_salvage(salvage)
            self.finish(ActivityResult(
                True, accuracy, salvage=salvage, damage=self.hull_lost, renown=3,
                stat="storms_survived", grit_cost=2,
                headline="You punch through the back of the storm into stunned, quiet air.",
                detail=f"{self.runner.hits} of {self.runner.total} answered clean."))
        else:
            self.finish(ActivityResult(
                False, accuracy, damage=self.hull_lost, grit_cost=2,
                headline="You fall back out the way you came, beaten but floating.",
                detail="The storm holds its ground."))
