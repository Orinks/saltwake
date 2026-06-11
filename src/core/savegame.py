"""Profile persistence: atomic JSON save/load with versioning."""

import json
import os
import tempfile

from core.paths import SAVE_DIR, ensure_save_dir

SAVE_VERSION = 1
PROFILE_FILE = "profile.json"


def profile_path() -> str:
    return os.path.join(SAVE_DIR, PROFILE_FILE)


def save_profile(data: dict) -> None:
    ensure_save_dir()
    payload = {"version": SAVE_VERSION, "profile": data}
    fd, tmp = tempfile.mkstemp(dir=SAVE_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp, profile_path())
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def load_profile() -> dict | None:
    path = profile_path()
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if payload.get("version") != SAVE_VERSION:
            return _migrate(payload)
        return payload.get("profile")
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Save: could not load profile ({exc}).")
        return None


def _migrate(payload: dict) -> dict | None:
    # Single version so far; future migrations slot in here.
    return payload.get("profile")
