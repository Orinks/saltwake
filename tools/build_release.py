"""Build a standalone Saltwake distribution with PyInstaller.

Produces a one-directory build (fast startup, antivirus-friendly) and
archives it for release:

* Windows: ``dist/Saltwake-<label>-windows-portable.zip``
* Linux:   ``dist/Saltwake-<label>-linux-x64.tar.gz``
* macOS:   ``dist/Saltwake-<label>-macos.zip``

``<label>`` is the project version from pyproject.toml, or the value of
``--tag`` (used for nightly developer snapshots). The bundle collects the
game's data, the BASS libraries shipped inside sound_lib, Prism's native
speech library, the player docs, and the soundtrack pre-rendered into
``assets/music`` so first launch never has to compose.

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


NATIVE_EXTS = {".dll", ".dylib", ".so"}


def _native_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*")
            if p.is_file() and p.suffix.lower() in NATIVE_EXTS]


def verify_release_dependencies() -> None:
    """Fail early when this platform's build would ship broken.

    A wheel that installed without its native libraries produces a build
    that freezes fine and then has no speech or no audio on players'
    machines. Catch that before spending the build time, and check the
    game data the bundle step copies wholesale.
    """
    import importlib

    for module in ("pygame", "numpy", "prism", "sound_lib"):
        importlib.import_module(module)

    for module, label in (("sound_lib", "sound_lib BASS audio"),
                          ("prism", "Prism speech")):
        pkg_root = Path(importlib.import_module(module).__file__).parent
        if not _native_files(pkg_root):
            raise RuntimeError(
                f"{label} native libraries are missing for this platform "
                f"under {pkg_root}")

    for required in ("story", "music.json", "vessels.json", "regions.json",
                     "boons.json", "gear.json", "achievements.json"):
        if not (ROOT / "data" / required).exists():
            raise RuntimeError(f"release data is missing: data/{required}")

    for required in (ROOT / "docs" / "Manual.html", ROOT / "LICENSE"):
        if not required.exists():
            raise RuntimeError(
                f"release documentation is missing: {required.relative_to(ROOT)}")


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


def bundle_player_docs(build_dir: Path) -> None:
    """Copy ``docs/`` next to the executable, for players and game managers.

    Game managers such as AGNow offer a game's documentation by scanning
    the installed folder for ``docs``, so the manual has to land there and
    not inside PyInstaller's ``_internal``. Everything in ``docs/`` is
    player-facing by contract — design notes live in ``DESIGN.md`` at the
    repository root, and the licences ship extensionless at the bundle
    root — so the folder is copied wholesale and a player never opens it
    onto something only a developer would read.
    """
    source = ROOT / "docs"
    manual = source / "Manual.html"
    if not manual.exists():
        raise RuntimeError(f"player manual is missing: {manual}")
    shutil.copytree(source, build_dir / "docs", dirs_exist_ok=True)
    shutil.copy2(ROOT / "LICENSE", build_dir / "LICENSE")
    shipped = sorted(p.name for p in (build_dir / "docs").rglob("*") if p.is_file())
    print(f"Player docs bundled: {', '.join(shipped)}")


# What a documentation scanner will offer a player if it finds it.
READER_SUFFIXES = {".txt", ".html", ".htm", ".md", ".rst"}
# Names that mark a file as a licence rather than packaging bookkeeping.
LICENSE_STEMS = ("LICENSE", "LICENCE", "COPYING", "NOTICE", "AUTHORS")


def _is_license(path: Path) -> bool:
    """Is this a licence text, as opposed to code or package data?

    Checked against the suffix first: a module named ``authors.py`` is
    not a notice, and this decides what gets deleted.
    """
    if path.suffix.lower() not in READER_SUFFIXES | {"", ".terms"}:
        return False
    if any(part.lower() == "licenses" for part in path.parts[:-1]):
        return True
    return any(stem in path.stem.upper() for stem in LICENSE_STEMS)


def consolidate_third_party_licenses(build_dir: Path) -> None:
    """Leave the manual as the only thing a scanner calls documentation.

    Game managers such as AGNow list a game's documentation by scanning
    the installed folder, and PyInstaller drags every dependency's
    packaging metadata into ``_internal``: licence texts nested inside
    ``.dist-info``, ``entry_points.txt``, ``top_level.txt``, a vendored
    lorem ipsum. A player opening that list should find the manual and
    nothing else — none of it is written for them.

    The licences themselves have to ship — MIT, BSD and Apache all
    require the notice to travel with the binary — so they are merged
    into one ``Third-Party-Licenses`` file at the bundle root and the
    originals removed. That name carries no extension on purpose:
    AGNow lists ``.txt`` and ``.html``, so an extensionless file stays
    in the bundle for anyone who goes looking without being offered to
    a player as reading. The rest of the metadata is deleted outright;
    nothing under ``_internal`` is read by the game at runtime, and the
    smoke check boots the pruned build before it is archived.
    """
    internal = build_dir / "_internal"
    licenses: list[tuple[str, str]] = []
    pruned = 0

    for path in sorted(internal.rglob("*")):
        if not path.is_file():
            continue
        if _is_license(path):
            text = path.read_text(encoding="utf-8", errors="replace").strip()
            if text:
                name = path.relative_to(internal).as_posix()
                licenses.append((name, text))
        elif path.suffix.lower() not in READER_SUFFIXES:
            continue
        path.unlink()
        pruned += 1

    for path in sorted(internal.rglob("*"), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()

    if not licenses:
        raise RuntimeError(
            f"no third-party licences found under {internal}; the bundle "
            f"would ship without the notices its dependencies require")

    out = build_dir / "Third-Party-Licenses"
    with open(out, "w", encoding="utf-8") as f:
        f.write("Saltwake bundles the libraries below. Their licences follow\n"
                "in full; Saltwake's own licence is in the LICENSE file.\n")
        for name, text in licenses:
            f.write(f"\n\n{'=' * 70}\n{name}\n{'=' * 70}\n\n{text}\n")
    print(f"Player-facing docs pruned: {pruned} files removed from _internal, "
          f"{len(licenses)} notices kept in {out.name}.")


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
    parser.add_argument("--check-dependencies", action="store_true",
                        help="only verify release-critical runtime dependencies")
    args = parser.parse_args()

    if args.check_dependencies:
        verify_release_dependencies()
        print("Release dependency check passed.")
        return 0

    label = args.tag or project_version()
    verify_release_dependencies()
    if (ROOT / "build").exists():
        shutil.rmtree(ROOT / "build")
    build_dir = run_pyinstaller()
    stamp_build_info(build_dir, label)
    bundle_player_docs(build_dir)
    consolidate_third_party_licenses(build_dir)
    prerender_soundtrack(build_dir)
    if not args.skip_smoke:
        smoke_check(build_dir)
    out = archive(build_dir, label)
    print(f"Built {out} ({out.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
