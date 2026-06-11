"""Path resolution, portable-build aware.

Saltwake is distributed as a portable game: everything it writes (saves,
the rendered music cache) lives in the game's own main directory, never in
per-user system folders. Two roots cover source checkouts and frozen
(PyInstaller) builds:

* :func:`portable_root` — the writable main directory. The project root
  when running from source; the executable's directory when frozen.
  Override with the ``SALTWAKE_DATA_DIR`` environment variable (tests).
* :func:`resource_root` — bundled read-only content (``data/``). The same
  project root from source; PyInstaller's extraction dir when frozen.
"""

import os
import sys

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SOURCE_ROOT = os.path.dirname(SRC_DIR)


def portable_root() -> str:
    override = os.environ.get("SALTWAKE_DATA_DIR")
    if override:
        return override
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return _SOURCE_ROOT


def resource_root() -> str:
    return getattr(sys, "_MEIPASS", _SOURCE_ROOT)


PROJECT_ROOT = portable_root()
DATA_DIR = os.path.join(resource_root(), "data")
STORY_DIR = os.path.join(DATA_DIR, "story")
SAVE_DIR = os.path.join(PROJECT_ROOT, "saves")


def ensure_save_dir() -> str:
    os.makedirs(SAVE_DIR, exist_ok=True)
    return SAVE_DIR
