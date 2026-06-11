"""Synthesized audio cues.

All sounds are generated at runtime with numpy (sine, square, noise) so the
game needs no sound assets. Stereo panning carries spatial information:
pan -1.0 is hard left, 0.0 center, 1.0 hard right. Pitch carries distance,
speed, or tension depending on the activity.
"""

import math
from typing import Optional

import numpy as np

SAMPLE_RATE = 44100


def _envelope(samples: np.ndarray, fade_ms: int = 6) -> np.ndarray:
    n = len(samples)
    fade = min(int(SAMPLE_RATE * fade_ms / 1000), n // 2)
    if fade > 0:
        ramp = np.linspace(0.0, 1.0, fade)
        samples[:fade] *= ramp
        samples[-fade:] *= ramp[::-1]
    return samples


def _wave(freq: float, ms: int, shape: str) -> np.ndarray:
    n = int(SAMPLE_RATE * ms / 1000)
    t = np.arange(n) / SAMPLE_RATE
    if shape == "sine":
        w = np.sin(2 * math.pi * freq * t)
    elif shape == "square":
        w = np.sign(np.sin(2 * math.pi * freq * t)) * 0.6
    elif shape == "triangle":
        w = 2.0 * np.abs(2.0 * ((t * freq) % 1.0) - 1.0) - 1.0
    elif shape == "noise":
        rng = np.random.default_rng(int(freq))
        w = rng.uniform(-1.0, 1.0, n)
        # crude lowpass: rolling mean smooths the hiss into a wash
        kernel = max(2, int(SAMPLE_RATE / max(freq, 50.0)))
        w = np.convolve(w, np.ones(kernel) / kernel, mode="same")
        peak = np.max(np.abs(w)) or 1.0
        w = w / peak
    else:
        raise ValueError(f"unknown wave shape: {shape}")
    return _envelope(w.astype(np.float32))


class AudioManager:
    """Plays synthesized tones and earcons through pygame.mixer."""

    def __init__(self, volume: float = 0.5, enabled: bool = True):
        self.volume = volume
        self.enabled = False
        self._cache: dict = {}
        if not enabled:
            return
        try:
            import pygame
            self._pygame = pygame
            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(SAMPLE_RATE, -16, 2, 512)
                pygame.mixer.init()
            pygame.mixer.set_num_channels(16)
            self.enabled = True
        except Exception as exc:
            print(f"Audio: mixer unavailable ({exc}); running silent.")

    def _build(self, freq: float, ms: int, pan: float, vol: float, shape: str):
        key = (round(freq, 1), ms, round(pan, 2), round(vol, 2), shape)
        snd = self._cache.get(key)
        if snd is not None:
            return snd
        mono = _wave(freq, ms, shape) * vol * self.volume
        left = mono * min(1.0, 1.0 - pan)
        right = mono * min(1.0, 1.0 + pan)
        stereo = np.column_stack((left, right))
        pcm = (stereo * 32767).astype(np.int16)
        snd = self._pygame.sndarray.make_sound(np.ascontiguousarray(pcm))
        if len(self._cache) > 256:
            self._cache.clear()
        self._cache[key] = snd
        return snd

    def tone(self, freq: float, ms: int = 120, pan: float = 0.0,
             vol: float = 0.8, shape: str = "sine") -> None:
        if not self.enabled:
            return
        try:
            self._build(freq, ms, pan, vol, shape).play()
        except Exception:
            pass

    def chord(self, freqs, ms: int = 160, pan: float = 0.0, vol: float = 0.6) -> None:
        for f in freqs:
            self.tone(f, ms, pan, vol)

    # --- Earcons -----------------------------------------------------------
    def menu_move(self) -> None:
        self.tone(660, 40, vol=0.35)

    def menu_select(self) -> None:
        self.chord((523, 784), 90, vol=0.4)

    def menu_back(self) -> None:
        self.tone(330, 70, vol=0.35)

    def menu_edge(self) -> None:
        self.tone(220, 60, vol=0.35, shape="triangle")

    def success(self) -> None:
        self.chord((523, 659, 784), 200, vol=0.45)

    def big_success(self) -> None:
        self.chord((523, 659, 784, 1047), 350, vol=0.5)

    def fail(self) -> None:
        self.chord((233, 175), 250, vol=0.5)

    def warning(self) -> None:
        self.tone(880, 90, vol=0.5, shape="square")

    def splash(self) -> None:
        self.tone(300, 220, vol=0.5, shape="noise")

    def wave_wash(self, pan: float = 0.0) -> None:
        self.tone(150, 500, pan=pan, vol=0.3, shape="noise")

    def coin(self) -> None:
        self.tone(1175, 60, vol=0.4)
        self.tone(1568, 90, vol=0.4)

    def damage(self) -> None:
        self.tone(110, 200, vol=0.7, shape="square")

    def heartbeat(self) -> None:
        self.tone(70, 110, vol=0.8, shape="sine")


class NullAudio(AudioManager):
    """Silent audio manager for tests."""

    def __init__(self):
        self.volume = 0.0
        self.enabled = False
        self._cache = {}

    def tone(self, *args, **kwargs) -> None:
        pass
