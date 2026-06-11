"""Soundtrack playback through BASS (sound_lib), as in Freight Fate.

Tracks are rendered from data/music.json by core.composer on first use and
cached as WAVs under assets/music/ (gitignored — the soundtrack's source of
truth is the spec file, not the audio). Playback prefers a looping BASS
stream with volume slides for fades; pygame.mixer.music is the automatic
fallback, and ``SALTWAKE_AUDIO_BACKEND=pygame`` skips BASS entirely.
play() is idempotent so scenes can restate their theme freely.

Music sits deliberately under the speech and cue layer: it is scene-setting,
never information. Everything it signals is also spoken.
"""

from __future__ import annotations

import logging
import os

from core.paths import DATA_DIR, PROJECT_ROOT

log = logging.getLogger(__name__)

MUSIC_CACHE = os.path.join(PROJECT_ROOT, "assets", "music")

SCENE_TRACKS = {
    "title": "saltwake_theme",
    "harbor": "greywater_quay",
    "almanac": "quiet_lines",
    "wreck": "driftwood",
    "homecoming": "homecoming",
    "victory": "lanterns_lit",
}

REGION_TRACKS = {
    "shallows": "the_shallows",
    "chop": "the_chop",
    "wreckwater": "wreckwater",
    "glass_squall": "glass_squall",
}

ACTIVITY_TRACKS = {
    "boat_race": "open_throttle",
    "jetski_slalom": "buoy_dance",
    "dive_salvage": "beneath",
    "storm_run": "teeth_of_the_wind",
    "fishing": "line_and_lure",
    "rescue_tow": "heave_to",
}

BOSS_TRACKS = {
    "regatta_champion": "warden",
    "ferry_ghost": "warden",
    "leviathan_wake": "warden",
    "the_undertow": "undertow",
}


def load_specs() -> dict[str, dict]:
    import json
    with open(os.path.join(DATA_DIR, "music.json"), encoding="utf-8") as f:
        return {t["id"]: t for t in json.load(f)["tracks"]}


class _BassMusic:
    """Looping BASS stream with attribute-slide fades."""

    name = "bass"

    def __init__(self) -> None:
        from sound_lib.external.pybass import (BASS_ATTRIB_VOL,
                                               BASS_ChannelSlideAttribute)
        from sound_lib.main import BassError, bass_call
        from sound_lib.stream import FileStream

        from core.audio import get_bass_output
        self._FileStream = FileStream
        self._BassError = BassError
        self._bass_call = bass_call
        self._slide = BASS_ChannelSlideAttribute
        self._ATTRIB_VOL = BASS_ATTRIB_VOL
        self._output = get_bass_output()
        self._stream = None
        # Channel.__del__ frees the BASS handle on garbage collection, which
        # would cut fade-outs short; keep fading streams alive until done.
        self._retained: list = []

    def _retain(self, stream) -> None:
        alive = []
        for s in self._retained:
            try:
                if s.is_playing:
                    alive.append(s)
            except self._BassError:
                pass
        alive.append(stream)
        self._retained = alive

    def _fade_out(self, stream, fade_ms: int) -> None:
        """Slide volume to -1: BASS stops (and autofrees) the channel at 0."""
        try:
            self._bass_call(self._slide, stream.handle, self._ATTRIB_VOL,
                            -1.0, max(0, int(fade_ms)))
        except self._BassError:
            return
        self._retain(stream)

    def play(self, path: str, volume: float, fade_ms: int) -> bool:
        if self._stream is not None:
            self._fade_out(self._stream, max(1, fade_ms // 2))
            self._stream = None
        try:
            stream = self._FileStream(file=path, autofree=True)
            stream.set_looping(True)
            stream.set_volume(0.0)
            stream.play()
            self._bass_call(self._slide, stream.handle, self._ATTRIB_VOL,
                            max(0.0, min(1.0, volume)), max(0, int(fade_ms)))
        except self._BassError:
            log.warning("Could not play music %s", path, exc_info=True)
            return False
        self._stream = stream
        return True

    def stop(self, fade_ms: int) -> None:
        if self._stream is not None:
            self._fade_out(self._stream, fade_ms)
            self._stream = None

    def set_volume(self, volume: float) -> None:
        if self._stream is not None:
            try:
                self._stream.set_volume(max(0.0, min(1.0, volume)))
            except self._BassError:
                self._stream = None


class _PygameMusic:
    """pygame.mixer.music fallback."""

    name = "pygame"

    def __init__(self) -> None:
        import pygame
        self._pygame = pygame
        if not pygame.mixer.get_init():
            pygame.mixer.pre_init(44100, -16, 2, 512)
            pygame.mixer.init()

    def play(self, path: str, volume: float, fade_ms: int) -> bool:
        try:
            music = self._pygame.mixer.music
            if music.get_busy():
                music.fadeout(max(1, fade_ms // 2))
            music.load(path)
            music.set_volume(volume)
            music.play(loops=-1, fade_ms=fade_ms)
            return True
        except self._pygame.error:
            log.warning("Could not play music %s", path, exc_info=True)
            return False

    def stop(self, fade_ms: int) -> None:
        try:
            self._pygame.mixer.music.fadeout(max(1, fade_ms))
        except self._pygame.error:
            pass

    def set_volume(self, volume: float) -> None:
        try:
            self._pygame.mixer.music.set_volume(volume)
        except self._pygame.error:
            pass


class MusicManager:
    def __init__(self, volume: float = 0.35, enabled: bool = True,
                 cache_dir: str = MUSIC_CACHE):
        self.volume = volume
        self.enabled = enabled
        self.cache_dir = cache_dir
        self.current: str | None = None
        self.specs = load_specs()
        self._impl = None
        if not enabled:
            return
        pref = os.environ.get("SALTWAKE_AUDIO_BACKEND", "").strip().lower()
        if pref in ("", "bass"):
            try:
                self._impl = _BassMusic()
            except Exception:
                log.warning("sound_lib/BASS unavailable for music; falling "
                            "back to pygame.mixer.music", exc_info=True)
        if self._impl is None:
            try:
                self._impl = _PygameMusic()
            except Exception:
                log.warning("Music unavailable; running silent", exc_info=True)
                self.enabled = False
                return
        log.info("Music backend: %s", self._impl.name)

    @property
    def backend_name(self) -> str:
        return self._impl.name if self._impl else "none"

    # --- rendering -----------------------------------------------------------
    def path_for(self, track_id: str) -> str:
        return os.path.join(self.cache_dir, f"{track_id}.wav")

    def ensure(self, track_id: str) -> str | None:
        if track_id not in self.specs:
            return None
        path = self.path_for(track_id)
        if not os.path.isfile(path):
            from core.composer import render_track, write_wav
            os.makedirs(self.cache_dir, exist_ok=True)
            write_wav(path, render_track(self.specs[track_id]))
        return path

    def render_all(self, progress=None) -> list[str]:
        paths = []
        for track_id in self.specs:
            if progress:
                progress(track_id)
            paths.append(self.ensure(track_id))
        return paths

    # --- playback ----------------------------------------------------------------
    def play(self, track_id: str | None, fade_ms: int = 900) -> None:
        if track_id is None or not self.enabled or self._impl is None:
            return
        if track_id == self.current:
            return
        path = self.ensure(track_id)
        if path is None:
            return
        if self._impl.play(path, self.volume, fade_ms):
            self.current = track_id

    def stop(self, fade_ms: int = 600) -> None:
        if self._impl is not None:
            self._impl.stop(fade_ms)
        self.current = None

    def set_volume(self, volume: float) -> float:
        self.volume = max(0.0, min(1.0, volume))
        if self._impl is not None:
            self._impl.set_volume(self.volume)
        return self.volume

    def toggle(self) -> bool:
        self.enabled = not self.enabled
        if not self.enabled:
            self.stop(300)
        elif self.current:
            track, self.current = self.current, None
            self.play(track)
        return self.enabled


class NullMusic(MusicManager):
    """Silent music manager for tests and headless runs."""

    def __init__(self):
        self.volume = 0.0
        self.enabled = False
        self.cache_dir = MUSIC_CACHE
        self.current = None
        self.specs = load_specs()
        self._impl = None

    def ensure(self, track_id: str) -> str | None:
        return None

    def play(self, track_id: str | None, fade_ms: int = 900) -> None:
        self.current = track_id
