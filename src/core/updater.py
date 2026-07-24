"""In-game auto-updater.

Checks GitHub releases for a newer build, downloads the right archive for
this platform, and swaps it in with a tiny detached helper script that waits
for the game to exit, copies the new files over the install folder, and
relaunches.

Channels mirror the release pipeline: ``stable`` follows tagged releases
(``v0.2.0``), ``dev`` follows the nightly prerelease snapshots
(``nightly-20260611``). The packaged build carries a ``build_info.json``
next to the executable (written by ``tools/build_release.py``) recording its
tag, channel, version, and build date; that is how a nightly knows a newer
nightly exists even though the project version number has not changed.

Updates only apply to frozen (PyInstaller) builds. Source checkouts are
managed by git and the updater stays out of the way.

The Linux AppImage is a special case: the game runs from a read-only
image, so instead of copying files over an install folder the updater
downloads the new ``.AppImage`` and atomically swaps the file itself
(see :func:`running_appimage` and :func:`write_appimage_swap_script`).
"""

import json
import logging
import os
import re
import shlex
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

log = logging.getLogger(__name__)

REPO = "Orinks/saltwake"
APP_NAME = "Saltwake"
API_BASE = f"https://api.github.com/repos/{REPO}"
USER_AGENT = f"{APP_NAME}-updater"
TIMEOUT = 15  # seconds, per HTTP request

CHANNELS = ("stable", "dev")


# -- build identity ---------------------------------------------------------


@dataclass
class BuildInfo:
    """What this running copy of the game is."""

    tag: str        # "v0.2.0" or "nightly-20260611"
    channel: str    # "stable" or "dev"
    built_at: str   # "2026-06-11" (UTC date); "" when unknown
    version: str    # project version at build time, e.g. "0.1.0"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def install_root() -> Path:
    """The folder holding the executable (and ``_internal``)."""
    return Path(sys.executable).resolve().parent


def running_appimage(appimage_path: str | None = None) -> Path | None:
    """The ``.AppImage`` file this process is running from, or None.

    The AppImage runtime exports ``APPIMAGE`` with the file's absolute
    path. That variable is the only trustworthy signal: the payload itself
    executes from a transient mount or extraction directory under ``/tmp``,
    so path heuristics on ``sys.executable`` would misread the deployment
    (and writing into that payload directory is never possible or useful).
    """
    raw = appimage_path if appimage_path is not None else os.environ.get("APPIMAGE")
    if not raw:
        return None
    path = Path(raw)
    return path if path.is_file() else None


def _dir_writable(directory: Path) -> bool:
    """True when we can create files in ``directory`` (probe, not ACL math)."""
    probe = directory / f".saltwake-update-probe-{os.getpid()}"
    try:
        probe.touch()
        probe.unlink()
        return True
    except OSError:
        return False


def can_auto_apply() -> bool:
    """Whether :func:`apply_and_restart` can actually swap this install.

    AppImage runs need the directory holding the ``.AppImage`` file to be
    writable (the swap is a rename next to it); folder installs need the
    install root itself to be writable. Callers should check this before
    promising a restart, and offer the downloaded file for manual install
    when it returns False.
    """
    if not is_frozen():
        return False
    appimage = running_appimage()
    if appimage is not None:
        return _dir_writable(appimage.parent)
    return _dir_writable(install_root())


@lru_cache(maxsize=1)
def load_build_info() -> BuildInfo | None:
    """Read build_info.json from the install folder; cached, since the
    answer never changes mid-session.

    Returns None when running from source. Frozen builds that predate the
    stamp fall back to an unknown stable identity.
    """
    if not is_frozen():
        return None
    try:
        with open(install_root() / "build_info.json", encoding="utf-8") as f:
            data = json.load(f)
        return BuildInfo(tag=str(data["tag"]), channel=str(data["channel"]),
                         built_at=str(data.get("built_at", "")),
                         version=str(data.get("version", "0.0.0")))
    except (OSError, ValueError, KeyError):
        return BuildInfo(tag="", channel="stable", built_at="", version="0.0.0")


def resolve_channel(setting: str, build: BuildInfo | None) -> str:
    """The effective update channel: the player's explicit choice, else
    whatever channel this build came from."""
    if setting in CHANNELS:
        return setting
    if build is not None and build.channel in CHANNELS:
        return build.channel
    return "stable"


# -- release discovery ------------------------------------------------------


@dataclass
class UpdateInfo:
    tag: str            # release tag to install
    title: str          # spoken name, e.g. "Saltwake version 0.2.0"
    notes: list         # release notes flattened to speakable lines
    asset_name: str
    asset_url: str
    asset_size: int     # bytes


def _api_get(path: str):
    req = urllib.request.Request(
        API_BASE + path,
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.load(resp)


def parse_version(text: str) -> tuple:
    """'v0.2.0' -> (0, 2, 0). Unparseable text compares lowest."""
    nums = re.findall(r"\d+", text)
    return tuple(int(n) for n in nums) if nums else (0,)


def _platform_suffix() -> str:
    if sys.platform == "win32":
        return "-windows-portable.zip"
    if sys.platform == "darwin":
        return "-macos.zip"
    # An AppImage updates to the next AppImage; folder installs keep the
    # tarball they came from.
    if running_appimage() is not None:
        return "-linux-x86_64.AppImage"
    return "-linux-x64.tar.gz"


def pick_asset(release: dict, suffix: str = ""):
    """The (name, url, size) of this platform's archive, or None."""
    suffix = suffix or _platform_suffix()
    for asset in release.get("assets", ()):
        name = asset.get("name", "")
        if name.endswith(suffix):
            return name, asset["browser_download_url"], int(asset.get("size", 0))
    return None


def flatten_markdown(body: str) -> list:
    """Release-notes markdown as plain, speakable lines."""
    lines = []
    for raw in (body or "").splitlines():
        line = raw.strip()
        if not line or set(line) <= {"-", "=", "*", "_"}:
            continue
        line = re.sub(r"^#{1,6}\s+", "", line)               # headings
        line = re.sub(r"^[-*+]\s+", "", line)                 # bullets
        line = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", line)  # links
        line = re.sub(r"(\*\*|__|\*|_|`)", "", line)          # emphasis/code
        if line:
            lines.append(line)
    return lines


def _nightly_date(tag: str) -> str:
    """'nightly-20260611' -> '20260611'; '' when not a nightly tag."""
    m = re.fullmatch(r"nightly-(\d{8})", tag)
    return m.group(1) if m else ""


def _update_from_release(release: dict, title: str):
    asset = pick_asset(release)
    if asset is None:
        return None
    name, url, size = asset
    return UpdateInfo(tag=release["tag_name"], title=title,
                      notes=flatten_markdown(release.get("body", "")),
                      asset_name=name, asset_url=url, asset_size=size)


def stable_update_from(release: dict, current_version: str):
    tag = release.get("tag_name", "")
    if parse_version(tag) <= parse_version(current_version):
        return None
    return _update_from_release(release, f"Saltwake version {tag.lstrip('v')}")


def dev_update_from(releases: list, build: BuildInfo | None):
    for release in releases:
        tag = release.get("tag_name", "")
        if not release.get("prerelease") or not _nightly_date(tag):
            continue
        if build is not None:
            if tag == build.tag:
                return None
            build_date = (_nightly_date(build.tag)
                          or build.built_at.replace("-", ""))
            if build_date and _nightly_date(tag) <= build_date:
                return None
        date = _nightly_date(tag)
        spoken = f"{date[:4]}-{date[4:6]}-{date[6:]}"
        return _update_from_release(
            release, f"Saltwake developer snapshot {spoken}")
    return None


def check_for_update(channel: str, build: BuildInfo | None):
    """Query GitHub for a newer release on ``channel``. Raises OSError on
    network trouble; returns None when already up to date."""
    if channel == "dev":
        return dev_update_from(_api_get("/releases?per_page=20"), build)
    try:
        release = _api_get("/releases/latest")
    except urllib.error.HTTPError as e:
        if e.code == 404:  # no stable release published yet
            return None
        raise
    current = build.version if build is not None else "0.0.0"
    return stable_update_from(release, current)


# -- download and apply -----------------------------------------------------


class UpdateCancelled(Exception):
    pass


def download(info: UpdateInfo, dest_dir: Path, progress=None,
             cancelled=None) -> Path:
    """Fetch the release archive into ``dest_dir``.

    ``progress(done_bytes, total_bytes)`` is called as data arrives;
    ``cancelled`` is a ``threading.Event`` checked between chunks.
    """
    dest = dest_dir / info.asset_name
    req = urllib.request.Request(info.asset_url, headers={"User-Agent": USER_AGENT})
    done = 0
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp, open(dest, "wb") as f:
        total = int(resp.headers.get("Content-Length") or info.asset_size or 0)
        while True:
            if cancelled is not None and cancelled.is_set():
                raise UpdateCancelled
            chunk = resp.read(65536)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if progress is not None:
                progress(done, total)
    return dest


def extract(archive: Path, staging: Path) -> Path:
    """Unpack the release archive; returns the new app folder inside it."""
    staging.mkdir(parents=True, exist_ok=True)
    if archive.name.endswith(".tar.gz"):
        import tarfile

        with tarfile.open(archive, "r:gz") as tar:
            tar.extractall(staging, filter="data")
    elif sys.platform == "darwin":
        # ditto preserves the executable bits that zipfile would drop
        subprocess.run(["ditto", "-x", "-k", str(archive), str(staging)],
                       check=True)
    else:
        import zipfile

        with zipfile.ZipFile(archive) as z:
            z.extractall(staging)
    new_root = staging / APP_NAME
    if not new_root.is_dir():
        raise FileNotFoundError(f"{APP_NAME} folder missing from {archive.name}")
    return new_root


def make_staging_dir() -> Path:
    return Path(tempfile.mkdtemp(prefix=f"{APP_NAME.lower()}-update-"))


_WINDOWS_SCRIPT = """@echo off
:wait
tasklist /FI "PID eq {pid}" 2>NUL | find "{pid}" >NUL
if not errorlevel 1 (
  ping -n 2 127.0.0.1 >NUL
  goto wait
)
robocopy "{src}\\_internal" "{dst}\\_internal" /MIR /R:10 /W:1 >NUL
robocopy "{src}" "{dst}" /E /XD _internal saves /R:10 /W:1 >NUL
start "" "{dst}\\{exe}"
rmdir /s /q "{staging}"
del "%~f0"
"""

_POSIX_SCRIPT = """#!/bin/sh
# the release archive never contains a saves folder, so the player's
# portable saves under {dst}/saves survive the copy untouched
while kill -0 {pid} 2>/dev/null; do sleep 1; done
rm -rf "{dst}/_internal"
cp -a "{src}/." "{dst}/"
rm -rf "{staging}"
"{dst}/{exe}" &
rm -f "$0"
"""

_APPIMAGE_SCRIPT = """#!/bin/sh
# Swap the running AppImage for the downloaded one once the game exits.
# The new file is staged NEXT TO the target first so the final mv is an
# atomic rename on the same filesystem; a half-written game is never left
# behind. The relaunched AppImage's own AppRun re-derives the data
# directory, so nothing here depends on inherited environment.
PID={pid}
NEW={new}
TARGET={target}
STAGING={staging}
while kill -0 "$PID" 2>/dev/null; do sleep 1; done
STAGED="$TARGET.update-new"
cp "$NEW" "$STAGED" || exit 1
chmod +x "$STAGED"
mv -f "$STAGED" "$TARGET" || exit 1
rm -rf "$STAGING"
"$TARGET" &
rm -f "$0"
"""


def write_apply_script(new_root: Path, install: Path, staging: Path,
                       pid: int) -> Path:
    """The helper script that swaps in the update once the game exits."""
    exe = APP_NAME + (".exe" if sys.platform == "win32" else "")
    template = _WINDOWS_SCRIPT if sys.platform == "win32" else _POSIX_SCRIPT
    text = template.format(pid=pid, src=new_root, dst=install,
                           staging=staging, exe=exe)
    suffix = ".bat" if sys.platform == "win32" else ".sh"
    script = staging.parent / f"{APP_NAME.lower()}-apply-{pid}{suffix}"
    script.write_text(text, encoding="utf-8")
    if sys.platform != "win32":
        script.chmod(0o755)
    return script


def write_appimage_swap_script(new_appimage: Path, target: Path,
                               staging: Path, pid: int) -> Path:
    """The helper script that replaces the running ``.AppImage`` file.

    Paths are shell-quoted so spaces or metacharacters in the player's
    folder names cannot break the swap.
    """
    text = _APPIMAGE_SCRIPT.format(pid=pid,
                                   new=shlex.quote(str(new_appimage)),
                                   target=shlex.quote(str(target)),
                                   staging=shlex.quote(str(staging)))
    script = staging.parent / f"{APP_NAME.lower()}-appimage-apply-{pid}.sh"
    script.write_text(text, encoding="utf-8")
    script.chmod(0o755)
    return script


def _spawn_detached(script: Path) -> None:
    if sys.platform == "win32":
        flags = (subprocess.CREATE_NO_WINDOW
                 | subprocess.CREATE_NEW_PROCESS_GROUP)
        subprocess.Popen(["cmd", "/c", str(script)], creationflags=flags,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, close_fds=True)
    else:
        subprocess.Popen(["/bin/sh", str(script)], start_new_session=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, close_fds=True)


def apply_and_restart(new_root: Path, staging: Path) -> None:
    """Spawn the detached apply script. The caller must then quit the game;
    the script waits for this process to exit before touching files.

    ``new_root`` is the unpacked game folder for archive installs, or the
    downloaded ``.AppImage`` file when running as an AppImage.
    """
    appimage = running_appimage()
    if (appimage is not None and new_root.is_file()
            and new_root.name.endswith(".AppImage")):
        script = write_appimage_swap_script(new_root, appimage, staging,
                                            os.getpid())
    else:
        script = write_apply_script(new_root, install_root(), staging,
                                    os.getpid())
    _spawn_detached(script)
    log.info("Update staged; apply script %s spawned", script)


def keep_for_manual_install(update_file: Path) -> Path:
    """Park a downloaded update somewhere the player can find it.

    Used when :func:`can_auto_apply` says the install can't be swapped
    automatically (for example a folder install in a read-only location).
    Prefers ``~/Downloads``, falls back to home, and leaves the file where
    it is when neither is writable. Returns the file's final location.
    """
    for candidate in (Path.home() / "Downloads", Path.home()):
        if candidate.is_dir() and _dir_writable(candidate):
            dest = candidate / update_file.name
            try:
                if dest.exists():
                    dest.unlink()
                update_file.replace(dest)
                return dest
            except OSError:
                try:
                    import shutil

                    shutil.copy2(update_file, dest)
                    update_file.unlink(missing_ok=True)
                    return dest
                except OSError:
                    continue
    return update_file
