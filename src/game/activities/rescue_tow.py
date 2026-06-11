"""Rescue tow: find the swimmer by ear, then hold the tow line home."""

import pygame

from game.activities.base import ActivityScene, ActivityResult


class RescueTowScene(ActivityScene):
    NAME = "Rescue"
    SKILL_KEY = "rescue_skill"
    INTRO = ("A whistle on the water, somebody in trouble. First, home in: a call sounds "
             "from a direction, answer with that arrow, left, right, or up for dead ahead. "
             "Three good turns puts you alongside. Then the tow: keep the drifting tone "
             "centered with left and right, and brace with down when they panic.")
    CONTROLS = "Arrows steer toward the call, then balance the tow. Down braces a panic."

    def __init__(self, game, run, on_complete, difficulty_mult: float = 1.0,
                 title: str | None = None):
        super().__init__(game, run, on_complete, difficulty_mult)
        if title:
            self.NAME = title
        self.stage = "locate"
        self.locks = 0
        self.call_dir = None
        self.call_timer = 0.0
        # tow state
        self.drift = 0.0
        self.drift_rate = 0.0
        self.strain = 0.0
        self.tow_progress = 0.0
        self.panic = False
        self.panic_timer = 0.0
        self.tone_timer = 0.0

    def start_play(self):
        self._new_call()

    # --- stage 1: locate ----------------------------------------------------
    def _new_call(self):
        self.call_dir = self.run.rng.choice(("left", "right", "center"))
        self.call_timer = 0.0

    def _call_cue(self):
        pan = {"left": -0.85, "right": 0.85, "center": 0.0}[self.call_dir]
        self.audio.tone(1000, 250, pan=pan, vol=0.7)

    def _locate_key(self, key):
        expected = {"left": pygame.K_LEFT, "right": pygame.K_RIGHT,
                    "center": pygame.K_UP}[self.call_dir]
        if key == expected:
            self.locks += 1
            self.audio.tone(700 + self.locks * 100, 90, vol=0.5)
            if self.locks >= 3:
                self.stage = "tow"
                self.drift_rate = 0.25 * self.difficulty * (1.0 - self.skill() * 0.4)
                self.speech.say("You haul them over the transom, coughing and alive. "
                                "Now the tow home. Keep the tone centered.")
            else:
                self.speech.say("Closer.", interrupt=False)
                self._new_call()
        elif key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP):
            self.strain += 10.0
            self.audio.splash()
            self.speech.say("Wrong heading. The whistle is fading.", interrupt=False)
            self._new_call()

    # --- stage 2: tow -------------------------------------------------------
    def _tow_key(self, key):
        if self.panic:
            if key in (pygame.K_DOWN, pygame.K_SPACE):
                self.panic = False
                self.audio.tone(500, 120, vol=0.5)
                self.speech.say("They settle.", interrupt=False)
            else:
                self.strain += 8.0
            return
        if key == pygame.K_LEFT:
            self.drift -= 0.35
        elif key == pygame.K_RIGHT:
            self.drift += 0.35

    def handle_play_key(self, event):
        if self.stage == "locate":
            self._locate_key(event.key)
        else:
            self._tow_key(event.key)

    def update_play(self, dt):
        if self.stage == "locate":
            self.call_timer += dt
            if self.call_timer >= 1.4:
                self.call_timer = 0.0
                self._call_cue()
            return
        # tow stage
        rng = self.run.rng
        self.tow_progress += dt * 8.0
        self.drift += self.drift_rate * dt * (1 if rng.random() > 0.5 else -1) * 2.0
        self.tone_timer += dt
        if self.tone_timer >= 0.7:
            self.tone_timer = 0.0
            pan = max(-1.0, min(1.0, self.drift))
            self.audio.tone(600, 120, pan=pan, vol=0.6)
        if abs(self.drift) > 1.0:
            self.strain += dt * 12.0
        if not self.panic and rng.random() < dt * 0.12:
            self.panic = True
            self.panic_timer = 0.0
            self.audio.warning()
            self.speech.say("They panic! Brace!", interrupt=True)
        if self.panic:
            self.panic_timer += dt
            if self.panic_timer > 2.5:
                self.panic = False
                self.strain += 15.0
                self.audio.splash()
        if self.strain >= 100.0:
            self.run.spend_grit(2)
            damage = self.soak(1)
            self.run.take_damage(damage)
            self.finish(ActivityResult(
                False, self.tow_progress / 100, damage=damage, grit_cost=2, renown=1,
                headline="The line parts. A patrol launch sweeps in and takes them aboard.",
                detail="They are safe, no thanks to the knots. A little renown for trying."))
        elif self.tow_progress >= 100.0:
            salvage = int(round(4 * (0.8 + self.difficulty * 0.4)))
            self.run.add_salvage(salvage)
            self.run.spend_grit(2)
            self.finish(ActivityResult(
                True, 1.0, salvage=salvage, renown=3, stat="rescues", grit_cost=2,
                headline="You bring them in breathing. The quay crowd makes the sound quays make.",
                detail="Word of a rescue travels farther than any race result."))
