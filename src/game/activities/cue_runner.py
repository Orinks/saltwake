"""Cue-response engine shared by the steering activities.

A cue is announced by a stereo-panned tone plus a spoken word; the player
answers with an arrow key (or space) inside the response window. Reaction
quality feeds back through earcons immediately and totals at the end.
"""

import pygame

CUE_DEFS = {
    "left":   {"keys": (pygame.K_LEFT,),  "pan": -0.85, "freq": 520, "word": "Left"},
    "right":  {"keys": (pygame.K_RIGHT,), "pan": 0.85,  "freq": 520, "word": "Right"},
    "center": {"keys": (pygame.K_UP,),    "pan": 0.0,   "freq": 660, "word": "Ahead"},
    "brace":  {"keys": (pygame.K_DOWN, pygame.K_SPACE), "pan": 0.0, "freq": 240,
               "word": "Brace"},
    # Counter-steer cues: the gust comes from one side, the answer is the other.
    "gust_left":  {"keys": (pygame.K_RIGHT,), "pan": -0.85, "freq": 300,
                   "word": "Gust left", "shape": "noise"},
    "gust_right": {"keys": (pygame.K_LEFT,),  "pan": 0.85, "freq": 300,
                   "word": "Gust right", "shape": "noise"},
}

RESPONSE_KEYS = (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN, pygame.K_SPACE)


class CueRunner:
    def __init__(self, audio, speech, cues: list[str], window: float,
                 gap_for=None, speak_words: bool = True):
        self.audio = audio
        self.speech = speech
        self.cues = cues
        self.window = window
        self.gap_for = gap_for or (lambda i: 1.3)
        self.speak_words = speak_words

        self.index = -1
        self.timer = 0.0
        self.state = "gap"     # gap -> active -> gap ... -> done
        self.hits = 0
        self.misses = 0
        self.wrongs = 0
        self.events: list[tuple[str, str]] = []  # (outcome, cue_name)

    @property
    def done(self) -> bool:
        return self.state == "done"

    @property
    def total(self) -> int:
        return len(self.cues)

    def _announce(self, name: str):
        cue = CUE_DEFS[name]
        self.audio.tone(cue["freq"], 140, pan=cue["pan"],
                        shape=cue.get("shape", "sine"), vol=0.9)
        if self.speak_words:
            self.speech.say(cue["word"] + "!", interrupt=True)

    def update(self, dt: float):
        if self.done:
            return
        self.timer += dt
        if self.state == "gap":
            gap = 1.0 if self.index < 0 else self.gap_for(self.index)
            if self.timer >= gap:
                self.index += 1
                if self.index >= len(self.cues):
                    self.state = "done"
                    return
                self.state = "active"
                self.timer = 0.0
                self._announce(self.cues[self.index])
        elif self.state == "active":
            if self.timer >= self.window:
                self._resolve("miss")

    def handle_key(self, key) -> str | None:
        """Returns 'hit', 'wrong', or None when no cue is live."""
        if self.state != "active" or key not in RESPONSE_KEYS:
            return None
        cue = CUE_DEFS[self.cues[self.index]]
        outcome = "hit" if key in cue["keys"] else "wrong"
        self._resolve(outcome)
        return outcome

    def _resolve(self, outcome: str):
        name = self.cues[self.index]
        self.events.append((outcome, name))
        if outcome == "hit":
            self.hits += 1
        elif outcome == "wrong":
            self.wrongs += 1
        else:
            self.misses += 1
        self.state = "done" if self.index >= len(self.cues) - 1 else "gap"
        self.timer = 0.0

    def accuracy(self) -> float:
        resolved = self.hits + self.misses + self.wrongs
        return self.hits / resolved if resolved else 0.0
