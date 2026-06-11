"""Synthesized audio cues, played through BASS (sound_lib) like Freight Fate.

All sounds are generated at runtime with numpy (sine, square, noise) so the
game needs no sound assets. Stereo position carries spatial information:
pan -1.0 is hard left, 0.0 center, 1.0 hard right. Pitch carries distance,
speed, or tension depending on the activity.

Two interchangeable backends sit behind the :class:`AudioManager` facade,
mirroring Freight Fate's audio engine:

* **BASS** (via ``sound_lib``) — the preferred backend. Tones are cached as
  mono WAVs in memory and streamed with BASS pan/volume attributes. With no
  audio device (headless CI) it initializes BASS's "no sound" device, so the
  full code path still runs silently.
* **pygame.mixer** — automatic fallback when sound_lib/BASS cannot
  initialize, baking pan and volume into stereo sample buffers.

Set ``SALTWAKE_AUDIO_BACKEND=pygame`` to skip BASS entirely. If nothing can
initialize, every method becomes a no-op.
"""

from __future__ import annotations

import io
import logging
import math
import os
import wave

import numpy as np

log = logging.getLogger(__name__)

SAMPLE_RATE = 44100
BASS_NO_SOUND_DEVICE = 0

_bass_output = None


def get_bass_output():
    """The process-wide BASS output; shared by cues and music."""
    global _bass_output
    if _bass_output is None:
        from sound_lib.main import BassError
        from sound_lib.output import Output
        if os.environ.get("SDL_AUDIODRIVER", "").lower() == "dummy":
            _bass_output = Output(device=BASS_NO_SOUND_DEVICE)
        else:
            try:
                _bass_output = Output()
            except BassError:
                log.warning("No audio device; using the BASS no-sound device")
                _bass_output = Output(device=BASS_NO_SOUND_DEVICE)
    return _bass_output


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


def mono_wav_bytes(mono: np.ndarray) -> bytes:
    """Packs a float mono buffer into an in-memory 16-bit WAV."""
    pcm = (np.clip(mono, -1.0, 1.0) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(np.ascontiguousarray(pcm).tobytes())
    return buf.getvalue()


class _BassBackend:
    """sound_lib (BASS) tones: memory streams with pan/volume attributes.

    Raises on construction if sound_lib cannot import or BASS cannot
    initialize at all; the facade then falls back to pygame.mixer.
    """

    name = "bass"

    def __init__(self) -> None:
        from sound_lib.main import BassError
        from sound_lib.stream import FileStream

        self._FileStream = FileStream
        self._BassError = BassError
        self._output = get_bass_output()
        self._cache: dict[tuple, bytes] = {}
        # Channel.__del__ frees the BASS handle when the Python object is
        # garbage collected, which would cut one-shots short the moment the
        # last reference drops — and memory streams additionally need their
        # source bytes kept alive. Finished entries are pruned on each play.
        self._retained: list[tuple[object, bytes]] = []

    def _wav_for(self, freq: float, ms: int, shape: str) -> bytes:
        key = (round(freq, 1), ms, shape)
        data = self._cache.get(key)
        if data is None:
            data = mono_wav_bytes(_wave(freq, ms, shape))
            if len(self._cache) > 256:
                self._cache.clear()
            self._cache[key] = data
        return data

    def _retain(self, stream, data: bytes) -> None:
        alive = []
        for s, d in self._retained:
            try:
                if s.is_playing:
                    alive.append((s, d))
            except self._BassError:
                pass  # already stopped and autofreed
        alive.append((stream, data))
        self._retained = alive

    def play_tone(self, freq: float, ms: int, pan: float, vol: float, shape: str) -> None:
        data = self._wav_for(freq, ms, shape)
        try:
            stream = self._FileStream(mem=True, file=data, length=len(data),
                                      autofree=True, unicode=False)
            stream.set_pan(max(-1.0, min(1.0, pan)))
            stream.set_volume(max(0.0, min(1.0, vol)))
            stream.play()
        except self._BassError:
            log.warning("Could not play tone", exc_info=True)
            return
        self._retain(stream, data)


class _PygameBackend:
    """pygame.mixer fallback: pan and volume baked into stereo buffers."""

    name = "pygame"

    def __init__(self) -> None:
        import pygame
        self._pygame = pygame
        if not pygame.mixer.get_init():
            pygame.mixer.pre_init(SAMPLE_RATE, -16, 2, 512)
            pygame.mixer.init()
        pygame.mixer.set_num_channels(16)
        self._cache: dict[tuple, object] = {}

    def play_tone(self, freq: float, ms: int, pan: float, vol: float, shape: str) -> None:
        key = (round(freq, 1), ms, round(pan, 2), round(vol, 2), shape)
        snd = self._cache.get(key)
        if snd is None:
            mono = _wave(freq, ms, shape) * vol
            left = mono * min(1.0, 1.0 - pan)
            right = mono * min(1.0, 1.0 + pan)
            pcm = (np.column_stack((left, right)) * 32767).astype(np.int16)
            snd = self._pygame.sndarray.make_sound(np.ascontiguousarray(pcm))
            if len(self._cache) > 256:
                self._cache.clear()
            self._cache[key] = snd
        try:
            snd.play()
        except self._pygame.error:
            pass


class AudioManager:
    """Facade over the active backend; the game talks only to this."""

    def __init__(self, volume: float = 0.5, enabled: bool = True):
        self.volume = volume
        self.enabled = False
        self._impl = None
        if not enabled:
            return
        pref = os.environ.get("SALTWAKE_AUDIO_BACKEND", "").strip().lower()
        if pref in ("", "bass"):
            try:
                self._impl = _BassBackend()
            except Exception:
                log.warning("sound_lib/BASS unavailable; falling back to "
                            "pygame.mixer", exc_info=True)
        if self._impl is None:
            try:
                self._impl = _PygameBackend()
            except Exception:
                log.warning("Audio unavailable; running silent", exc_info=True)
                return
        self.enabled = True
        log.info("Audio backend: %s", self._impl.name)

    @property
    def backend_name(self) -> str:
        return self._impl.name if self._impl else "none"

    def set_volume(self, volume: float) -> float:
        self.volume = max(0.0, min(1.0, volume))
        return self.volume

    def tone(self, freq: float, ms: int = 120, pan: float = 0.0,
             vol: float = 0.8, shape: str = "sine") -> None:
        if not self.enabled:
            return
        try:
            self._impl.play_tone(freq, ms, pan, vol * self.volume, shape)
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
        self._impl = None

    def tone(self, *args, **kwargs) -> None:
        pass
