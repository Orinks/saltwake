"""Build a standalone Saltwake distribution with PyInstaller.

Produces a one-directory build (fast startup, antivirus-friendly) and
archives it for release:

* Windows: ``dist/Saltwake-<label>-windows-portable.zip``
* Linux:   ``dist/Saltwake-<label>-linux-x64.tar.gz``
* macOS:   ``dist/Saltwake-<label>-macos.zip``

``<label>`` is the project version from pyproject.toml, or the value of
``--tag`` (used for nightly developer snapshots). The bundle collects the
game's data, the BASS libraries shipped inside sound_lib, Prism's native
speech library, and the soundtrack pre-rendered into ``assets/music`` so
first launch never has to compose.

Run from the repository root: ``uv run python tools/build_release.py``
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
APP_NAME = "Saltwake"


def project_version() -> str:
    with open(ROOT / "pyproject.toml", "rb") as f:
        return tomllib.load(f)["project"]["version"]


def run_pyinstaller() -> Path:
    """Freeze the game; returns the onedir build directory."""
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--name", APP_NAME,
        "--distpath", str(DIST),
        "--workpath", str(ROOT / "build"),
        "--specpath", str(ROOT / "build"),
        "--paths", str(ROOT / "src"),
        # game content: storylets, vessels, regions, boons, gear, music specs
        "--add-data", f"{ROOT / 'data'}{os.pathsep}data",
        # native libraries loaded at runtime via ctypes
        "--collect-all", "sound_lib",
        "--collect-all", "prism",
    ]
    if sys.platform == "win32":
        cmd.append("--windowed")
    cmd.append(str(ROOT / "src" / "main.py"))
    subprocess.run(cmd, check=True)
    return DIST / APP_NAME


def prerender_soundtrack(build_dir: Path) -> None:
    """Render all 18 tracks into the bundle so players never wait on it."""
    env = {**os.environ, "SALTWAKE_DATA_DIR": str(build_dir)}
    subprocess.run([sys.executable, str(ROOT / "tools" / "render_soundtrack.py")],
                   check=True, env=env)
    rendered = list((build_dir / "assets" / "music").glob("*.wav"))
    if not rendered:
        raise RuntimeError("soundtrack pre-render produced no files")
    print(f"Soundtrack pre-rendered: {len(rendered)} tracks bundled.")


def stamp_build_info(build_dir: Path, label: str) -> None:
    """Record what this build is, for the in-game updater.

    ``label`` is either a nightly tag (``nightly-20260611``) or a plain
    version (``0.1.0``); the release tag for the latter is ``v``-prefixed.
    """
    nightly = label.startswith("nightly-")
    info = {
        "tag": label if nightly else f"v{label}",
        "channel": "dev" if nightly else "stable",
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "version": project_version(),
    }
    with open(build_dir / "build_info.json", "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)


def smoke_check(build_dir: Path) -> None:
    """Boot the frozen game headless and let it assemble everything."""
    exe = build_dir / (APP_NAME + (".exe" if sys.platform == "win32" else ""))
    env = {
        **os.environ,
        "SDL_VIDEODRIVER": "dummy",
        "SDL_AUDIODRIVER": "dummy",
        "SALTWAKE_NO_SPEECH": "1",
    }
    subprocess.run([str(exe), "--self-test"], check=True, env=env, timeout=120)
    print("Smoke check passed: the frozen build boots.")


def archive(build_dir: Path, label: str) -> Path:
    if sys.platform == "win32":
        out = DIST / f"{APP_NAME}-{label}-windows-portable.zip"
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for path in sorted(build_dir.rglob("*")):
                z.write(path, Path(APP_NAME) / path.relative_to(build_dir))
    elif sys.platform == "darwin":
        out = DIST / f"{APP_NAME}-{label}-macos.zip"
        subprocess.run(["ditto", "-c", "-k", "--keepParent",
                        str(build_dir), str(out)], check=True)
    else:
        out = DIST / f"{APP_NAME}-{label}-linux-x64.tar.gz"
        with tarfile.open(out, "w:gz") as tar:
            tar.add(build_dir, arcname=APP_NAME)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default="",
                        help="release label override, e.g. nightly-20260611")
    parser.add_argument("--skip-smoke", action="store_true",
                        help="skip booting the frozen build")
    args = parser.parse_args()

    label = args.tag or project_version()
    if (ROOT / "build").exists():
        shutil.rmtree(ROOT / "build")
    build_dir = run_pyinstaller()
    stamp_build_info(build_dir, label)
    prerender_soundtrack(build_dir)
    if not args.skip_smoke:
        smoke_check(build_dir)
    out = archive(build_dir, label)
    print(f"Built {out} ({out.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
