"""Shared frame for all watersports activities.

Every activity follows the same accessible shape:
  1. intro    — name, stakes, and controls are spoken; Enter starts, H re-reads.
  2. countdown — three tones, rising.
  3. play     — the activity's real-time loop (subclass responsibility).
  4. done     — result spoken; Enter returns to the chart.

Universal keys during play: R repeats last speech, T speaks status,
Escape abandons the attempt (counts as a failure, never a softlock).
"""

import pygame

from core.scenes import Scene
from game import boons as boons_mod
from game.weather import difficulty as weather_difficulty, damage_mult


class ActivityResult:
    def __init__(self, success: bool, score: float = 0.0, salvage: int = 0,
                 damage: int = 0, grit_cost: int = 1, renown: int = 0,
                 headline: str = "", detail: str = "", stat: str | None = None,
                 abandoned: bool = False):
        self.success = success
        self.score = score
        self.salvage = salvage
        self.damage = damage
        self.grit_cost = grit_cost
        self.renown = renown
        self.headline = headline
        self.detail = detail
        self.stat = stat
        self.abandoned = abandoned


class ActivityScene(Scene):
    NAME = "activity"
    SKILL_KEY = None          # e.g. "race_speed"; adds to player competence
    INTRO = ""                # spoken once at start
    CONTROLS = ""             # spoken with the intro and on H
    MUSIC = None              # soundtrack id; bosses override via music_track

    def __init__(self, game, run, on_complete, difficulty_mult: float = 1.0):
        super().__init__(game)
        self.run = run
        self.on_complete = on_complete
        self.phase = "intro"
        self.elapsed = 0.0
        self.countdown_step = 0
        self.difficulty = run.difficulty() * weather_difficulty(run.sea_state) * difficulty_mult
        self.dmg_mult = damage_mult(run.sea_state)
        self.result: ActivityResult | None = None

    # --- skill helpers -------------------------------------------------------
    def skill(self) -> float:
        if not self.SKILL_KEY:
            return 0.0
        return boons_mod.total_modifier(self.run, self.SKILL_KEY)

    def window_scale(self) -> float:
        """Response windows grow with cue_time boons and shrink with difficulty."""
        scale = (1.0 + boons_mod.total_modifier(self.run, "cue_time")) / max(0.5, self.difficulty)
        return max(0.45, min(1.6, scale))

    def soak(self, damage: int) -> int:
        soak = int(boons_mod.total_modifier(self.run, "damage_soak"))
        return max(0, int(round(damage * self.dmg_mult)) - soak)

    # --- lifecycle ----------------------------------------------------------
    def on_enter(self):
        self.game.music.play(getattr(self, "music_track", None) or self.MUSIC)
        self.speech.say(f"{self.NAME}. {self.INTRO}")
        self.speech.queue(f"{self.CONTROLS} Press Enter when ready. "
                          "During play: R repeats, T for status, Escape to abandon.")

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_r:
            self.speech.repeat_last()
            return
        if event.key == pygame.K_t:
            self.speech.say(self.run.status_text())
            return
        if self.phase == "intro":
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.phase = "countdown"
                self.elapsed = 0.0
                self.countdown_step = 0
            elif event.key == pygame.K_h:
                self.speech.say(f"{self.INTRO} {self.CONTROLS}")
            elif event.key == pygame.K_ESCAPE:
                self._abandon()
        elif self.phase == "play":
            if event.key == pygame.K_ESCAPE:
                self._abandon()
            else:
                self.handle_play_key(event)
        elif self.phase == "done":
            if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                self.game.scenes.pop()
                self.on_complete(self.result)

    def update(self, dt: float):
        if self.phase == "countdown":
            self.elapsed += dt
            while self.countdown_step < 3 and self.elapsed >= self.countdown_step * 0.7:
                self.audio.tone(440 + self.countdown_step * 120, 140)
                self.countdown_step += 1
            if self.elapsed >= 2.1:
                self.audio.tone(880, 250)
                self.phase = "play"
                self.elapsed = 0.0
                self.start_play()
        elif self.phase == "play":
            self.elapsed += dt
            self.update_play(dt)

    def _abandon(self):
        result = ActivityResult(False, abandoned=True, grit_cost=1,
                                headline="You break off and let the water settle.",
                                detail="No reward, no shame. The sea keeps no score you can hear.")
        self.finish(result)

    def finish(self, result: ActivityResult):
        # Mirror Calm: one failed contest per tide simply does not count.
        if not result.success and not result.abandoned and boons_mod.has_tag(self.run, "reroll_fail"):
            boons_mod.consume_tag(self.run, "reroll_fail")
            self.speech.say("The water shivers, and the moment un-happens. Mirror Calm is spent. Try again.")
            self.audio.big_success()
            self.phase = "intro"
            self.elapsed = 0.0
            return
        self.result = result
        self.phase = "done"
        if result.success:
            self.audio.success()
        elif not result.abandoned:
            self.audio.fail()
        parts = [result.headline]
        if result.detail:
            parts.append(result.detail)
        if result.salvage:
            parts.append(f"Salvage gained: {result.salvage}.")
        if result.damage:
            parts.append(f"Hull damage: {result.damage}.")
        parts.append("Press Enter to continue.")
        self.speech.say(" ".join(parts))

    # --- subclass hooks -------------------------------------------------------
    def start_play(self):
        pass

    def update_play(self, dt: float):
        pass

    def handle_play_key(self, event):
        pass
