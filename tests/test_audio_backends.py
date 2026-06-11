"""Audio/music backend selection and the BASS integration.

conftest sets SDL_AUDIODRIVER=dummy, so the BASS backend initializes the
no-sound device and the whole pipeline runs headless, exactly as in CI.
"""

import numpy as np
import pytest

from core import audio as audio_mod
from core.audio import AudioManager, NullAudio, mono_wav_bytes, _wave
from core.music import MusicManager, NullMusic


def test_mono_wav_bytes_is_valid_wav():
    data = mono_wav_bytes(_wave(440, 50, "sine"))
    assert data[:4] == b"RIFF" and data[8:12] == b"WAVE"
    import io
    import wave
    with wave.open(io.BytesIO(data)) as f:
        assert f.getnchannels() == 1
        assert f.getsampwidth() == 2
        assert f.getframerate() == audio_mod.SAMPLE_RATE


def test_bass_backend_is_preferred_and_plays():
    manager = AudioManager(volume=0.5)
    assert manager.enabled
    assert manager.backend_name == "bass"
    # The full cue vocabulary runs without raising on the no-sound device.
    manager.tone(440, 30, pan=-0.5)
    manager.chord((440, 660), 30)
    manager.menu_move()
    manager.success()
    manager.splash()


def test_env_override_forces_pygame(monkeypatch):
    monkeypatch.setenv("SALTWAKE_AUDIO_BACKEND", "pygame")
    manager = AudioManager(volume=0.5)
    assert manager.backend_name == "pygame"
    manager.tone(440, 30, pan=0.5)
    music = MusicManager(volume=0.2)
    assert music.backend_name == "pygame"


def test_bass_tone_cache_excludes_pan_and_volume():
    manager = AudioManager(volume=0.5)
    if manager.backend_name != "bass":
        pytest.skip("BASS not available")
    manager.tone(440, 30, pan=-1.0, vol=0.1)
    manager.tone(440, 30, pan=1.0, vol=0.9)
    assert len(manager._impl._cache) == 1  # pan/vol are BASS attributes


def test_music_manager_uses_bass_and_loops(tmp_path):
    music = MusicManager(volume=0.2, cache_dir=str(tmp_path))
    assert music.backend_name == "bass"
    music.play("quiet_lines", fade_ms=10)
    assert music.current == "quiet_lines"
    assert (tmp_path / "quiet_lines.wav").is_file()
    music.play("quiet_lines")  # idempotent
    music.set_volume(0.4)
    music.stop(fade_ms=10)
    assert music.current is None


def test_music_toggle_resumes_track(tmp_path):
    music = MusicManager(volume=0.2, cache_dir=str(tmp_path))
    music.play("driftwood", fade_ms=10)
    assert music.toggle() is False
    music.current = "driftwood"  # remembered preference survives the off state
    assert music.toggle() is True
    assert music.current == "driftwood"


def test_audio_set_volume_clamps():
    manager = NullAudio()
    assert manager.set_volume(1.7) == 1.0
    assert manager.set_volume(-2) == 0.0


def test_null_managers_stay_silent():
    audio = NullAudio()
    audio.tone(440)
    music = NullMusic()
    music.play("warden")
    assert music.current == "warden"
    assert music.backend_name == "none"
