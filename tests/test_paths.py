"""Portable path resolution for source checkouts and frozen builds."""

import os
import sys

from core import paths


def test_source_checkout_roots():
    assert paths.portable_root() == paths._SOURCE_ROOT or \
        os.environ.get("SALTWAKE_DATA_DIR")
    assert paths.resource_root() == paths._SOURCE_ROOT
    assert os.path.isdir(paths.DATA_DIR)


def test_env_override_wins(monkeypatch):
    monkeypatch.setenv("SALTWAKE_DATA_DIR", r"D:\PortableGames\Saltwake")
    assert paths.portable_root() == r"D:\PortableGames\Saltwake"


def test_frozen_build_saves_next_to_executable(monkeypatch):
    monkeypatch.delenv("SALTWAKE_DATA_DIR", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable",
                        os.path.join("C:", os.sep, "Games", "Saltwake", "saltwake.exe"))
    assert paths.portable_root() == os.path.join("C:", os.sep, "Games", "Saltwake")


def test_frozen_build_reads_bundled_data(monkeypatch):
    bundle = os.path.join("C:", os.sep, "Temp", "_MEI12345")
    monkeypatch.setattr(sys, "_MEIPASS", bundle, raising=False)
    assert paths.resource_root() == bundle


def test_saves_live_under_portable_root():
    assert paths.SAVE_DIR == os.path.join(paths.PROJECT_ROOT, "saves")


def test_suite_never_touches_the_real_save_dir():
    """Tests exercise scenes that call profile save for real (RunEndScene
    settles, harbor embarks), so a test run against the checkout's own
    saves/ pollutes the developer's actual profile — a leaked homecoming
    once unlocked an achievement on a brand-new game."""
    assert paths.SAVE_DIR != os.path.join(paths._SOURCE_ROOT, "saves")
