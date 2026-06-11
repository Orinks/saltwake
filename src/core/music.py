"""Soundtrack playback.

Tracks are rendered from data/music.json by core.composer on first use and
cached as WAVs under assets/music/ (gitignored — the soundtrack's source of
truth is the spec file, not the audio). Playback streams through
pygame.mixer.music with fades; play() is idempotent so scenes can restate
their theme freely.

Music sits deliberately under the speech and cue layer: it is scene-setting,
never information. Everything it signals is also spoken.
"""

import os

from core.paths import DATA_DIR, PROJECT_ROOT

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


class MusicManager:
    def __init__(self, volume: float = 0.35, enabled: bool = True,
                 cache_dir: str = MUSIC_CACHE):
        self.volume = volume
        self.enabled = enabled
        self.cache_dir = cache_dir
        self.current: str | None = None
        self.specs = load_specs()
        self._mixer_ok = False
        try:
            import pygame
            self._pygame = pygame
            self._mixer_ok = bool(pygame.mixer.get_init())
        except Exception:
            self.enabled = False

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
        if track_id is None or not self.enabled or not self._mixer_ok:
            return
        if track_id == self.current and self._pygame.mixer.music.get_busy():
            return
        path = self.ensure(track_id)
        if path is None:
            return
        try:
            music = self._pygame.mixer.music
            if music.get_busy():
                music.fadeout(max(1, fade_ms // 2))
            music.load(path)
            music.set_volume(self.volume)
            music.play(loops=-1, fade_ms=fade_ms)
            self.current = track_id
        except Exception:
            pass

    def stop(self, fade_ms: int = 600) -> None:
        if not self._mixer_ok:
            return
        try:
            self._pygame.mixer.music.fadeout(fade_ms)
        except Exception:
            pass
        self.current = None

    def set_volume(self, volume: float) -> float:
        self.volume = max(0.0, min(1.0, volume))
        if self._mixer_ok:
            try:
                self._pygame.mixer.music.set_volume(self.volume)
            except Exception:
                pass
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
        self._mixer_ok = False

    def ensure(self, track_id: str) -> str | None:
        return None

    def play(self, track_id: str | None, fade_ms: int = 900) -> None:
        self.current = track_id
