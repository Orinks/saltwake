"""Procedural music composer.

Every track in Saltwake's soundtrack is synthesized from a small JSON spec
(data/music.json): tempo, root, mode, a chord progression in scale degrees,
and a set of voices. Rendering is deterministic per seed, so the soundtrack
is reproducible from source — the same zero-asset philosophy as the sound
effects, scaled up to music.

Voices:
    pad     — sustained detuned chord tones, the harmonic bed
    bass    — plucked roots and fifths on the beat
    arp     — broken-chord sixteenths/eighths, panned side to side
    melody  — a seeded random walk on the scale, phrased with rests
    perc    — kick/hat/crash built from sine drops and noise bursts
    surf    — slow interpolated-noise swells, the sea under everything
"""

import wave

import numpy as np

SR = 44100

MODES = {
    "major":      [0, 2, 4, 5, 7, 9, 11],
    "minor":      [0, 2, 3, 5, 7, 8, 10],
    "dorian":     [0, 2, 3, 5, 7, 9, 10],
    "lydian":     [0, 2, 4, 6, 7, 9, 11],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "phrygian":   [0, 1, 3, 5, 7, 8, 10],
    "whole":      [0, 2, 4, 6, 8, 10],
}


def midi_to_freq(midi: float) -> float:
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


def degree_to_midi(root: int, mode: str, degree: int, octave: int = 0) -> int:
    scale = MODES[mode]
    idx = degree % len(scale)
    shift = degree // len(scale)
    return root + scale[idx] + 12 * (octave + shift)


def _tone(freq: float, n: int, kind: str = "sine", vibrato: float = 0.0) -> np.ndarray:
    t = np.arange(n, dtype=np.float32) / SR
    phase = 2 * np.pi * freq * t
    if vibrato:
        phase = phase + vibrato * np.sin(2 * np.pi * 5.0 * t)
    if kind == "warm":
        w = (np.sin(phase) + 0.35 * np.sin(2 * phase) + 0.12 * np.sin(3 * phase)) / 1.4
    elif kind == "soft":
        w = (np.sin(phase) + 0.2 * np.sin(2 * phase)) / 1.2
    else:
        w = np.sin(phase)
    return w.astype(np.float32)


def _decay_env(n: int, attack_s: float = 0.004, half_life_s: float = 0.18) -> np.ndarray:
    t = np.arange(n, dtype=np.float32) / SR
    env = np.exp(-t / max(half_life_s, 1e-3) * 0.6931)
    a = max(1, int(attack_s * SR))
    if a < n:
        env[:a] *= np.linspace(0.0, 1.0, a, dtype=np.float32)
    return env.astype(np.float32)


def _sustain_env(n: int, attack_s: float, release_s: float) -> np.ndarray:
    env = np.ones(n, dtype=np.float32)
    a = min(max(1, int(attack_s * SR)), n)
    env[:a] = np.linspace(0.0, 1.0, a, dtype=np.float32)
    r = min(max(1, int(release_s * SR)), n)
    env[-r:] *= np.linspace(1.0, 0.0, r, dtype=np.float32)
    return env


class _Mix:
    """Stereo accumulation buffer with equal-power panning."""

    def __init__(self, n: int):
        self.n = n
        self.buf = np.zeros((n, 2), dtype=np.float32)

    def add(self, mono: np.ndarray, start: int, pan: float = 0.0, gain: float = 1.0):
        if start >= self.n or gain == 0.0:
            return
        end = min(self.n, start + len(mono))
        if end <= start:
            return
        seg = mono[: end - start] * gain
        theta = (np.clip(pan, -1.0, 1.0) + 1.0) * np.pi / 4.0
        self.buf[start:end, 0] += seg * np.cos(theta)
        self.buf[start:end, 1] += seg * np.sin(theta)


def _chord_degrees(degree: int) -> list[int]:
    return [degree, degree + 2, degree + 4]


def render_track(spec: dict) -> np.ndarray:
    """Renders a track spec to a stereo int16 array."""
    tempo = spec.get("tempo", 90)
    root = spec.get("root", 57)  # A3 by default
    mode = spec.get("mode", "minor")
    if mode not in MODES:
        raise ValueError(f"unknown mode: {mode}")
    bars = spec.get("bars", 16)
    bpb = spec.get("beats_per_bar", 4)
    progression = spec.get("progression", [0, 3, 4, 0])
    voices = spec.get("voices", {})
    rng = np.random.default_rng(spec.get("seed", 0))

    beat_s = 60.0 / tempo
    bar_s = beat_s * bpb
    n = int(round(bars * bar_s * SR))
    mix = _Mix(n)

    def bar_start(b: int) -> int:
        return int(round(b * bar_s * SR))

    def beat_start(b: int, beat: float) -> int:
        return int(round((b * bar_s + beat * beat_s) * SR))

    def chord_for(b: int) -> list[int]:
        return _chord_degrees(progression[b % len(progression)])

    # --- pad ---------------------------------------------------------------
    pad = voices.get("pad")
    if pad:
        level = pad.get("level", 0.5)
        detune = pad.get("detune", 0.25)
        bar_n = int(round(bar_s * SR)) + int(0.4 * SR)
        for b in range(bars):
            tones = chord_for(b)
            for i, deg in enumerate(tones):
                freq = midi_to_freq(degree_to_midi(root, mode, deg))
                env = _sustain_env(bar_n, attack_s=bar_s * 0.3, release_s=0.5)
                pan = (-0.4, 0.4, 0.0)[i % 3]
                for sign in (-1.0, 1.0):
                    w = _tone(freq * (1.0 + sign * detune / 1000.0), bar_n, "soft")
                    mix.add(w * env, bar_start(b), pan=pan * sign,
                            gain=level / (len(tones) * 2.2))

    # --- bass --------------------------------------------------------------
    bass = voices.get("bass")
    if bass:
        level = bass.get("level", 0.5)
        pattern = bass.get("pattern", "light")
        steps = {
            "light": [(0.0, 0), (2.0, 0)],
            "drive": [(0.0, 0), (1.0, 0), (2.0, 4), (3.0, 0)],
            "pulse": [(0.0, 0), (1.5, 0), (2.0, 4), (3.5, 4)],
        }.get(pattern, [(0.0, 0), (2.0, 0)])
        note_n = int(beat_s * 1.2 * SR)
        for b in range(bars):
            base = chord_for(b)[0]
            for beat, interval in steps:
                if beat >= bpb:
                    continue
                freq = midi_to_freq(degree_to_midi(root, mode, base + interval, octave=-1))
                w = _tone(freq, note_n, "warm")
                env = _decay_env(note_n, attack_s=0.006, half_life_s=beat_s * 0.6)
                mix.add(w * env, beat_start(b, beat), pan=0.0, gain=level * 0.8)

    # --- arp ---------------------------------------------------------------
    arp = voices.get("arp")
    if arp:
        level = arp.get("level", 0.4)
        rate = arp.get("rate", 2)  # notes per beat
        step_s = beat_s / rate
        note_n = int(step_s * 1.6 * SR)
        side = 1.0
        for b in range(bars):
            tones = chord_for(b)
            order = list(tones) + [tones[1] + 7]
            for s in range(int(bpb * rate)):
                if rng.random() < arp.get("rest", 0.12):
                    continue
                deg = order[s % len(order)]
                freq = midi_to_freq(degree_to_midi(root, mode, deg, octave=1))
                w = _tone(freq, note_n, "sine")
                env = _decay_env(note_n, half_life_s=step_s * 0.9)
                start = int(round((b * bar_s + s * step_s) * SR))
                side = -side
                mix.add(w * env, start, pan=0.45 * side, gain=level * 0.5)

    # --- melody ------------------------------------------------------------
    melody = voices.get("melody")
    if melody:
        level = melody.get("level", 0.5)
        density = melody.get("density", 0.55)
        degree = 7  # start an octave above the root
        grid_s = beat_s / 2.0  # eighths
        steps_total = int(bars * bpb * 2)
        s = 0
        while s < steps_total:
            if rng.random() > density:
                s += 1
                continue
            length = int(rng.choice([1, 1, 2, 2, 3, 4]))
            degree += int(rng.choice([-2, -1, -1, 0, 1, 1, 2]))
            degree = max(4, min(13, degree))
            b = int(s * grid_s // bar_s)
            harmony = chord_for(min(b, bars - 1))
            snapped = min((h + 7 for h in harmony), key=lambda d: abs(d - degree)) \
                if rng.random() < 0.4 else degree
            freq = midi_to_freq(degree_to_midi(root, mode, snapped, octave=1))
            note_n = int(grid_s * length * 1.1 * SR)
            w = _tone(freq, note_n, "soft", vibrato=2.5)
            env = _sustain_env(note_n, attack_s=0.02, release_s=grid_s * 0.5)
            mix.add(w * env, int(round(s * grid_s * SR)), pan=0.12, gain=level * 0.45)
            s += length + (1 if rng.random() < 0.3 else 0)

    # --- percussion ----------------------------------------------------------
    perc = voices.get("perc")
    if perc and perc.get("style", "none") != "none":
        level = perc.get("level", 0.3)
        style = perc["style"]
        kick_beats = {
            "light": [0.0],
            "drive": [0.0, 2.0],
            "storm": [0.0, 1.5, 2.0],
        }.get(style, [0.0])
        kick_n = int(0.13 * SR)
        t = np.arange(kick_n, dtype=np.float32) / SR
        sweep = np.sin(2 * np.pi * (110 * np.exp(-t * 18) + 38) * t)
        kick = (sweep * _decay_env(kick_n, half_life_s=0.06)).astype(np.float32)
        hat_n = int(0.025 * SR)
        for b in range(bars):
            for beat in kick_beats:
                mix.add(kick, beat_start(b, beat), pan=0.0, gain=level)
            if style in ("drive", "storm"):
                for beat in (0.5, 1.5, 2.5, 3.5):
                    if beat >= bpb:
                        continue
                    hat = rng.uniform(-1, 1, hat_n).astype(np.float32)
                    hat = np.diff(hat, prepend=0.0).astype(np.float32)  # brighten
                    hat *= _decay_env(hat_n, half_life_s=0.01)
                    mix.add(hat, beat_start(b, beat), pan=0.25, gain=level * 0.4)
            if style == "storm" and b % 4 == 0:
                crash_n = int(0.9 * SR)
                crash = rng.uniform(-1, 1, crash_n).astype(np.float32)
                kernel = np.ones(24, dtype=np.float32) / 24
                crash = np.convolve(crash, kernel, mode="same")
                crash *= _decay_env(crash_n, attack_s=0.002, half_life_s=0.25)
                mix.add(crash, bar_start(b), pan=float(rng.uniform(-0.5, 0.5)),
                        gain=level * 0.8)

    # --- surf ----------------------------------------------------------------
    surf = voices.get("surf")
    if surf:
        level = surf.get("level", 0.2)
        coarse = rng.uniform(-1, 1, max(4, n // 1024))
        wash = np.interp(np.arange(n), np.arange(len(coarse)) * 1024, coarse)
        t = np.arange(n, dtype=np.float32) / SR
        swell = 0.55 + 0.45 * np.sin(2 * np.pi * t / (bar_s * 2) + rng.uniform(0, 6))
        pan_lfo = 0.5 * np.sin(2 * np.pi * t / (bar_s * 4))
        mono = (wash * swell).astype(np.float32) * level * 0.6
        theta = (pan_lfo + 1.0) * np.pi / 4.0
        mix.buf[:, 0] += mono * np.cos(theta)
        mix.buf[:, 1] += mono * np.sin(theta)

    # --- master ------------------------------------------------------------------
    out = np.tanh(mix.buf * 1.3)
    peak = float(np.max(np.abs(out))) or 1.0
    out *= 0.88 / peak
    fade = min(int(0.04 * SR), n // 4)
    ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)[:, None]
    out[:fade] *= ramp
    out[-fade:] *= ramp[::-1]
    return (out * 32767).astype(np.int16)


def write_wav(path: str, pcm: np.ndarray) -> None:
    with wave.open(path, "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(np.ascontiguousarray(pcm).tobytes())


def duration_seconds(pcm: np.ndarray) -> float:
    return len(pcm) / SR
