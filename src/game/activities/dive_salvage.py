"""Dive salvage: sonar-guided free dive with push-your-luck depth.

The cache pings every second: the pan tells you which way it lies, the pitch
tells you how it sits against your depth (lower pitch means it is deeper than
you). Find it, grab it, then choose — surface with what you have, or chase
the second, richer ping while your breath runs out.
"""

import pygame

from game.activities.base import ActivityScene, ActivityResult
from game import boons as boons_mod


class DiveSalvageScene(ActivityScene):
    NAME = "Dive salvage"
    SKILL_KEY = "dive_skill"
    INTRO = ("Something worth having sits on the bottom. Sonar pings mark it: the side "
             "the ping leans is the way to swim, and a deeper voice means it lies below "
             "you. Get on top of it and grab it, then get back to air before your breath runs out.")
    CONTROLS = ("Down arrow descends, up arrow ascends. Left and right swim sideways. "
                "Space grabs when the ping rings true. Surface at depth zero to finish.")

    def __init__(self, game, run, on_complete, difficulty_mult: float = 1.0,
                 title: str | None = None):
        super().__init__(game, run, on_complete, difficulty_mult)
        if title:
            self.NAME = title
        self.depth = 0
        self.lateral = 0
        self.breath = 0.0
        self.breath_max = 0.0
        self.ping_timer = 0.0
        self.haul = 0
        self.stage = 1
        self.target_depth = 0
        self.target_lateral = 0
        self.surfacing_prompted = False

    def start_play(self):
        rng = self.run.rng
        self.breath_max = 28.0 + boons_mod.total_modifier(self.run, "breath")
        self.breath = self.breath_max
        self._place_target(rng, depth_range=(3, 4 + int(self.difficulty)))

    def _place_target(self, rng, depth_range):
        self.target_depth = rng.randint(*depth_range)
        self.target_lateral = rng.randint(-2, 2)

    def _on_target(self) -> bool:
        return self.depth == self.target_depth and self.lateral == self.target_lateral

    def _ping(self):
        if self.target_depth is None:
            return
        d_lat = self.target_lateral - self.lateral
        d_dep = self.target_depth - self.depth
        pan = max(-1.0, min(1.0, d_lat * 0.45))
        freq = 700 - d_dep * 90  # deeper target = lower voice
        freq = max(180, min(1200, freq))
        if self._on_target():
            self.audio.chord((880, 1320), 180, vol=0.7)
        else:
            self.audio.tone(freq, 130, pan=pan, vol=0.7)

    def handle_play_key(self, event):
        key = event.key
        moved = False
        if key == pygame.K_DOWN:
            self.depth += 1
            moved = True
        elif key == pygame.K_UP and self.depth > 0:
            self.depth -= 1
            moved = True
        elif key == pygame.K_LEFT:
            self.lateral -= 1
            moved = True
        elif key == pygame.K_RIGHT:
            self.lateral += 1
            moved = True
        elif key == pygame.K_SPACE:
            self._grab()
            return
        elif key == pygame.K_t:
            self.speech.say(f"Depth {self.depth}. Breath {int(self.breath)} seconds.")
            return
        if moved:
            self.audio.tone(220 + self.depth * 10, 50, vol=0.3, shape="triangle")
            if self.depth == 0 and self.haul and not self.surfacing_prompted:
                self._surface()

    def _grab(self):
        if self.target_depth is not None and self._on_target():
            base = 5 + self.target_depth * 2
            gained = int(round(base * (1.0 + self.skill()) * (0.8 + self.difficulty * 0.3)))
            self.haul += gained
            self.audio.coin()
            if self.stage == 1 and self.breath > self.breath_max * 0.35:
                self.stage = 2
                self._place_target(self.run.rng,
                                   depth_range=(self.depth + 2, self.depth + 4))
                self.speech.say(f"Got it. {gained} salvage in the bag. Another ping sounds, "
                                "deeper and richer. Chase it, or take the up arrow home.")
            else:
                self.target_depth = None
                self.speech.say(f"Got it. {gained} salvage. Nothing else down here. "
                                "Surface, depth zero, before your breath runs out.")
        else:
            self.audio.splash()
            self.speech.say("Your hands close on cold water.", interrupt=False)

    def _surface(self):
        self.surfacing_prompted = True
        self.run.add_salvage(self.haul)
        self.run.spend_grit(2)
        self.finish(ActivityResult(
            True, min(1.0, self.haul / 20), salvage=self.haul, renown=2,
            stat="dives_completed", grit_cost=2,
            headline="You break the surface and the sky pours back in.",
            detail=f"Hauled {self.haul} salvage up from the dark."))

    def update_play(self, dt):
        self.breath -= dt * (1.0 + self.depth * 0.06)
        self.ping_timer += dt
        if self.ping_timer >= 1.1:
            self.ping_timer = 0.0
            self._ping()
            if self.breath < self.breath_max * 0.25:
                self.audio.heartbeat()
        if int(self.breath) in (10, 5) and abs(self.breath - int(self.breath)) < dt:
            self.speech.say(f"{int(self.breath)} seconds of breath.", interrupt=False)
        if self.breath <= 0:
            kept = self.haul // 2
            self.run.add_salvage(kept)
            damage = self.soak(2)
            self.run.take_damage(damage)
            self.run.spend_grit(3)
            self.finish(ActivityResult(
                False, 0.0, salvage=kept, damage=damage, grit_cost=3,
                headline="The dark takes the edges of things. You come to draped over your own gunwale.",
                detail=f"Half the haul slipped away. You kept {kept} salvage."))
