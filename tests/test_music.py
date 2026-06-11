"""Composer rendering and soundtrack coverage."""

import numpy as np
import pytest

from core import composer
from core.music import (ACTIVITY_TRACKS, BOSS_TRACKS, REGION_TRACKS,
                        SCENE_TRACKS, NullMusic, load_specs)

SHORT_SPEC = {
    "id": "test_track", "tempo": 120, "root": 60, "mode": "minor",
    "bars": 2, "seed": 5, "progression": [0, 4],
    "voices": {
        "pad": {"level": 0.5}, "bass": {"level": 0.5, "pattern": "drive"},
        "arp": {"level": 0.4, "rate": 2}, "melody": {"level": 0.5},
        "perc": {"level": 0.3, "style": "storm"}, "surf": {"level": 0.3},
    },
}


def test_render_shape_and_dtype():
    pcm = composer.render_track(SHORT_SPEC)
    expected = int(round(2 * 4 * (60 / 120) * composer.SR))
    assert pcm.shape == (expected, 2)
    assert pcm.dtype == np.int16
    assert np.max(np.abs(pcm)) > 1000  # actually contains audio
    assert np.max(np.abs(pcm)) <= 32767


def test_render_deterministic_per_seed():
    a = composer.render_track(SHORT_SPEC)
    b = composer.render_track(SHORT_SPEC)
    assert np.array_equal(a, b)
    different = composer.render_track({**SHORT_SPEC, "seed": 6})
    assert not np.array_equal(a, different)


def test_render_rejects_unknown_mode():
    with pytest.raises(ValueError):
        composer.render_track({**SHORT_SPEC, "mode": "klingon"})


def test_degree_to_midi_octave_wrap():
    assert composer.degree_to_midi(60, "major", 0) == 60
    assert composer.degree_to_midi(60, "major", 7) == 72   # next octave
    assert composer.degree_to_midi(60, "major", 2, octave=1) == 76


def test_all_specs_are_renderable_modes_and_unique():
    specs = load_specs()
    assert len(specs) >= 18
    for spec in specs.values():
        assert spec["mode"] in composer.MODES
        assert spec["bars"] > 0 and spec["tempo"] > 0
        assert all(isinstance(d, int) for d in spec["progression"])


def test_every_hook_maps_to_a_real_track():
    specs = load_specs()
    for mapping in (SCENE_TRACKS, REGION_TRACKS, ACTIVITY_TRACKS, BOSS_TRACKS):
        for track_id in mapping.values():
            assert track_id in specs, f"missing track {track_id}"


def test_hooks_cover_all_game_content():
    from game.data_loader import regions
    from game.chart import ACTIVITY_KINDS
    from game.activities.boss import BOSSES
    assert {r["id"] for r in regions()} <= set(REGION_TRACKS)
    assert set(ACTIVITY_KINDS) <= set(ACTIVITY_TRACKS)
    assert set(BOSSES) <= set(BOSS_TRACKS)


def test_activity_scene_music_attrs_match_mapping():
    from game.activities import get_activity_class
    for kind, track in ACTIVITY_TRACKS.items():
        assert get_activity_class(kind).MUSIC == track


def test_null_music_tracks_current():
    music = NullMusic()
    music.play("greywater_quay")
    assert music.current == "greywater_quay"
    assert music.ensure("greywater_quay") is None
