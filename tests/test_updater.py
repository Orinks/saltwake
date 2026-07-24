"""Update discovery, channel resolution, notes flattening, apply scripts."""

import sys
from pathlib import Path

from core import updater
from core.updater import (
    BuildInfo,
    can_auto_apply,
    dev_update_from,
    flatten_markdown,
    parse_version,
    pick_asset,
    resolve_channel,
    running_appimage,
    stable_update_from,
    write_appimage_swap_script,
    write_apply_script,
)
from game.profile import new_profile


def release(tag, prerelease=False, body="", assets=("-windows-portable.zip",
                                                    "-macos.zip",
                                                    "-linux-x64.tar.gz")):
    return {
        "tag_name": tag,
        "prerelease": prerelease,
        "body": body,
        "assets": [
            {"name": f"Saltwake-{tag}{suffix}",
             "browser_download_url": f"https://example.test/{tag}/{suffix}",
             "size": 80_000_000}
            for suffix in assets
        ],
    }


# -- version parsing and channels --------------------------------------------


def test_parse_version_orders_semver():
    assert parse_version("v0.2.0") > parse_version("0.1.0")
    assert parse_version("0.10.0") > parse_version("0.9.3")
    assert parse_version("garbage") == (0,)


def test_resolve_channel_prefers_explicit_setting():
    nightly = BuildInfo(tag="nightly-20260610", channel="dev",
                        built_at="2026-06-10", version="0.1.0")
    assert resolve_channel("stable", nightly) == "stable"
    assert resolve_channel("dev", None) == "dev"


def test_resolve_channel_follows_build_when_unset():
    nightly = BuildInfo(tag="nightly-20260610", channel="dev",
                        built_at="2026-06-10", version="0.1.0")
    assert resolve_channel("", nightly) == "dev"
    assert resolve_channel("", None) == "stable"


# -- stable channel -----------------------------------------------------------


def test_stable_update_found_when_newer():
    info = stable_update_from(release("v9.9.9", body="- Big stuff"), "0.1.0")
    assert info is not None
    assert info.tag == "v9.9.9"
    assert "9.9.9" in info.title
    assert info.notes == ["Big stuff"]
    assert info.asset_url.startswith("https://example.test/")


def test_stable_no_update_when_current_or_older():
    assert stable_update_from(release("v0.1.0"), "0.1.0") is None
    assert stable_update_from(release("v0.0.9"), "0.1.0") is None


def test_stable_no_update_without_platform_asset():
    assert stable_update_from(release("v9.9.9", assets=()), "0.1.0") is None


# -- dev channel --------------------------------------------------------------


def test_dev_update_skips_non_nightlies_and_finds_newer():
    releases = [
        release("v0.1.0"),                                  # stable, ignored
        release("nightly-20260611", prerelease=True),
        release("nightly-20260610", prerelease=True),
    ]
    build = BuildInfo(tag="nightly-20260610", channel="dev",
                      built_at="2026-06-10", version="0.1.0")
    info = dev_update_from(releases, build)
    assert info is not None
    assert info.tag == "nightly-20260611"
    assert "2026-06-11" in info.title


def test_dev_no_update_when_on_latest_nightly():
    releases = [release("nightly-20260611", prerelease=True)]
    build = BuildInfo(tag="nightly-20260611", channel="dev",
                      built_at="2026-06-11", version="0.1.0")
    assert dev_update_from(releases, build) is None


def test_dev_stable_build_compares_by_build_date():
    releases = [release("nightly-20260611", prerelease=True)]
    older = BuildInfo(tag="v0.1.0", channel="stable",
                      built_at="2026-06-01", version="0.1.0")
    newer = BuildInfo(tag="v0.2.0", channel="stable",
                      built_at="2026-06-11", version="0.2.0")
    assert dev_update_from(releases, older) is not None
    assert dev_update_from(releases, newer) is None


# -- assets and notes ---------------------------------------------------------


def test_pick_asset_matches_platform_suffix():
    rel = release("v0.2.0")
    name, url, size = pick_asset(rel, suffix="-windows-portable.zip")
    assert name.endswith("-windows-portable.zip")
    assert size == 80_000_000
    name, _, _ = pick_asset(rel, suffix="-linux-x64.tar.gz")
    assert name.endswith("-linux-x64.tar.gz")
    assert pick_asset(rel, suffix="-bsd.tar.xz") is None


def test_flatten_markdown_strips_formatting():
    body = ("## Changes\n\n- **The sea remembers.** Wrecks feed storylets.\n"
            "* See [the manual](https://example.test) for `details`.\n"
            "---\n")
    assert flatten_markdown(body) == [
        "Changes",
        "The sea remembers. Wrecks feed storylets.",
        "See the manual for details.",
    ]


def test_flatten_markdown_handles_empty_body():
    assert flatten_markdown("") == []
    assert flatten_markdown(None) == []


# -- apply script -------------------------------------------------------------


def test_write_apply_script_waits_for_pid_and_relaunches(tmp_path):
    staging = tmp_path / "staging"
    staging.mkdir()
    new_root = staging / "Saltwake"
    install = tmp_path / "install"
    script = write_apply_script(new_root, install, staging, pid=4242)
    text = script.read_text(encoding="utf-8")
    assert "4242" in text
    assert str(install) in text
    assert str(new_root) in text
    assert "Saltwake" in text
    assert script.parent == tmp_path  # outside the staging dir it deletes
    # portable saves live inside the install folder; the swap must not
    # touch them (Windows excludes the dir, POSIX never purges the root)
    if sys.platform == "win32":
        assert "/XD _internal saves" in text
    assert "/PURGE" not in text
    assert f"rm -rf \"{install}\"" not in text


# -- AppImage self-update -----------------------------------------------------


def fake_appimage(tmp_path):
    appimage = tmp_path / "Saltwake-0.1.0-linux-x86_64.AppImage"
    appimage.write_bytes(b"old build")
    return appimage


def test_running_appimage_requires_env_and_existing_file(tmp_path, monkeypatch):
    monkeypatch.delenv("APPIMAGE", raising=False)
    assert running_appimage() is None

    monkeypatch.setenv("APPIMAGE", str(tmp_path / "missing.AppImage"))
    assert running_appimage() is None

    appimage = fake_appimage(tmp_path)
    monkeypatch.setenv("APPIMAGE", str(appimage))
    assert running_appimage() == appimage


def test_platform_suffix_prefers_appimage_when_running_as_one(
        tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("APPIMAGE", raising=False)
    assert updater._platform_suffix() == "-linux-x64.tar.gz"

    monkeypatch.setenv("APPIMAGE", str(fake_appimage(tmp_path)))
    assert updater._platform_suffix() == "-linux-x86_64.AppImage"


def test_pick_asset_finds_the_appimage():
    rel = release("v0.2.0", assets=("-linux-x64.tar.gz",
                                    "-linux-x86_64.AppImage"))
    name, _, _ = pick_asset(rel, suffix="-linux-x86_64.AppImage")
    assert name.endswith("-linux-x86_64.AppImage")


def test_can_auto_apply_only_when_frozen_and_writable(tmp_path, monkeypatch):
    monkeypatch.delenv("APPIMAGE", raising=False)
    assert can_auto_apply() is False  # source checkout

    monkeypatch.setattr(updater, "is_frozen", lambda: True)
    monkeypatch.setenv("APPIMAGE", str(fake_appimage(tmp_path)))
    assert can_auto_apply() is True  # tmp_path is writable

    monkeypatch.setattr(updater, "_dir_writable", lambda _d: False)
    assert can_auto_apply() is False  # AppImage parked somewhere read-only


def test_appimage_swap_script_stages_next_to_target(tmp_path):
    target = tmp_path / "dir with space" / "Saltwake.AppImage"
    target.parent.mkdir()
    target.write_bytes(b"old")
    staging = tmp_path / "staging"
    staging.mkdir()
    new = staging / "Saltwake-0.2.0-linux-x86_64.AppImage"
    new.write_bytes(b"new")

    script = write_appimage_swap_script(new, target, staging, pid=4242)
    text = script.read_text(encoding="utf-8")

    assert script.parent == tmp_path  # outside the staging dir it deletes
    assert "4242" in text
    assert "'" in text                # spaced paths are shell-quoted
    assert ".update-new" in text      # staged beside the target
    assert "chmod +x" in text         # downloads arrive without the exec bit
    assert 'mv -f "$STAGED" "$TARGET"' in text  # atomic same-fs rename
    assert 'rm -f "$0"' in text       # the script cleans itself up


def test_apply_and_restart_routes_appimage_to_swap_script(
        tmp_path, monkeypatch):
    appimage = fake_appimage(tmp_path)
    monkeypatch.setenv("APPIMAGE", str(appimage))
    staging = tmp_path / "staging"
    staging.mkdir()
    new = staging / "Saltwake-0.2.0-linux-x86_64.AppImage"
    new.write_bytes(b"new")
    spawned = []
    monkeypatch.setattr(updater, "_spawn_detached", spawned.append)

    updater.apply_and_restart(new, staging)

    assert len(spawned) == 1
    assert "appimage-apply" in spawned[0].name
    assert "$TARGET" in spawned[0].read_text(encoding="utf-8")


def test_apply_and_restart_keeps_folder_installs_on_the_copy_script(
        tmp_path, monkeypatch):
    monkeypatch.delenv("APPIMAGE", raising=False)
    staging = tmp_path / "staging"
    staging.mkdir()
    new_root = staging / "Saltwake"
    new_root.mkdir()
    spawned = []
    monkeypatch.setattr(updater, "_spawn_detached", spawned.append)

    updater.apply_and_restart(new_root, staging)

    assert len(spawned) == 1
    assert "appimage" not in spawned[0].name


def test_keep_for_manual_install_moves_into_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    download = tmp_path / "staging" / "Saltwake-0.2.0-linux-x64.tar.gz"
    download.parent.mkdir()
    download.write_bytes(b"payload")

    dest = updater.keep_for_manual_install(download)

    assert dest == home / download.name  # no Downloads folder: home itself
    assert dest.read_bytes() == b"payload"
    assert not download.exists()


def test_keep_for_manual_install_prefers_downloads(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / "Downloads").mkdir(parents=True)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    download = tmp_path / "u.tar.gz"
    download.write_bytes(b"payload")

    dest = updater.keep_for_manual_install(download)

    assert dest == home / "Downloads" / "u.tar.gz"


# -- defaults -----------------------------------------------------------------


def test_profile_defaults_include_update_settings():
    settings = new_profile()["settings"]
    assert settings["update_channel"] == ""
    assert settings["skipped_update"] == ""


def test_build_info_none_when_not_frozen():
    assert not updater.is_frozen()
    assert updater.load_build_info() is None


def test_install_root_is_executable_dir():
    assert updater.install_root() == Path(sys.executable).resolve().parent
