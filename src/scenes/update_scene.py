"""Update screens: check, prompt, what's-new reader, and download.

All fully spoken, matching the rest of the game's menus. The check and the
download run on background threads; the scenes poll them every frame and
speak progress, so the pygame loop (and the screen reader) never blocks on
the network.
"""

import logging
import threading

import pygame

from core import updater
from core.menu import AccessibleMenu, MenuItem, BACK
from core.scenes import Scene
from game import profile as profile_mod

log = logging.getLogger(__name__)


class UpdateChecker:
    """Background release check; poll ``done``/``result`` from the loop."""

    def __init__(self, settings: dict):
        self.done = threading.Event()
        self.result = None
        self.error = None
        build = updater.load_build_info()
        channel = updater.resolve_channel(
            settings.get("update_channel", ""), build)
        self._thread = threading.Thread(
            target=self._run, args=(channel, build), daemon=True)
        self._thread.start()

    def _run(self, channel, build):
        try:
            self.result = updater.check_for_update(channel, build)
        except Exception as exc:  # offline, rate-limited, GitHub down...
            log.info("Update check failed: %s", exc)
            self.error = "Could not reach the update server."
        finally:
            self.done.set()


class UpdateCheckScene(Scene):
    """Manual 'Check for updates' from the Settings menu."""

    def __init__(self, game):
        super().__init__(game)
        self.checker = None
        self.message = ""

    def on_enter(self):
        if not updater.is_frozen():
            self.message = ("Updates are only available in the packaged game. "
                            "This copy runs from source; update it with git.")
            self.speech.say(self.message + " Press Escape to go back.")
            return
        if self.checker is None:
            self.speech.say("Checking for updates...")
            self.checker = UpdateChecker(self.game.profile["settings"])

    def update(self, dt):
        c = self.checker
        if c is None or not c.done.is_set() or self.message:
            return
        if c.error:
            self.message = c.error + " Check your internet connection and try again."
        elif c.result is None:
            build = updater.load_build_info()
            version = build.version if build else "unknown"
            self.message = f"You are up to date. Saltwake version {version}."
        else:
            self.game.scenes.replace(UpdatePromptScene(self.game, c.result))
            return
        self.speech.say(self.message + " Press Escape to go back.")

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
            self.audio.menu_back()
            self.game.scenes.pop()


class UpdatePromptScene(Scene):
    """Asks whether to download a newly found update."""

    def __init__(self, game, info):
        super().__init__(game)
        self.info = info
        self.menu = None

    def on_enter(self):
        mb = self.info.asset_size / 1e6
        size = f" The download is {mb:.0f} megabytes." if mb else ""
        items = [
            MenuItem("Download and restart", "download",
                     "Download the update, then restart the game with the "
                     "new version in place."),
            MenuItem("What's new", "notes",
                     "Read the changes in this update, line by line."),
            MenuItem("Remind me later", "later",
                     "Ask again the next time the game starts."),
            MenuItem("Skip this version", "skip",
                     "Do not ask about this update again. Later updates "
                     "will still be offered."),
        ]
        self.menu = AccessibleMenu(
            "Update available.", items, self.speech, self.audio,
            intro=f"{self.info.title} is ready to install.{size}")
        self.menu.open()

    def on_resume(self):
        self.menu.speak_current()

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or self.menu is None:
            return
        result = self.menu.handle_event(event)
        if result is None:
            return
        if result is BACK or result == "later":
            self.game.scenes.pop()
        elif result == "download":
            if not updater.is_frozen():
                self.speech.say("Updates can only be installed in the "
                                "packaged game. This copy runs from source.")
                return
            self.game.scenes.replace(UpdateDownloadScene(self.game, self.info))
        elif result == "notes":
            self.game.scenes.push(WhatsNewScene(self.game, self.info))
        elif result == "skip":
            self.game.profile["settings"]["skipped_update"] = self.info.tag
            profile_mod.save(self.game.profile)
            self.speech.say(f"Skipping {self.info.title}. You will be asked "
                            "again when the next update comes out.")
            self.game.scenes.pop()


class WhatsNewScene(Scene):
    """Line-by-line reader for the update's release notes."""

    def __init__(self, game, info):
        super().__init__(game)
        self.info = info
        self.notes = info.notes or ["No change notes were provided."]
        self.line = -1

    def on_enter(self):
        self.speech.say(f"What's new in {self.info.title}. "
                        f"{len(self.notes)} lines. Up and Down arrows read "
                        "line by line, Enter reads everything, Escape goes back.")

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.audio.menu_back()
            self.game.scenes.pop()
        elif event.key == pygame.K_DOWN:
            self.line = min(self.line + 1, len(self.notes) - 1)
            self.speech.say(self.notes[self.line])
        elif event.key == pygame.K_UP:
            self.line = max(self.line - 1, 0)
            self.speech.say(self.notes[self.line])
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.speech.say(" ".join(self.notes))


class UpdateDownloadScene(Scene):
    """Downloads and stages the update, then restarts the game."""

    def __init__(self, game, info):
        super().__init__(game)
        self.info = info
        self.cancelled = threading.Event()
        self.done = threading.Event()
        self.new_root = None
        self.staging = None
        self.error = None
        self.progress = 0.0       # 0..1, written by the worker thread
        self._spoken_quarter = 0
        self._finished = False
        self._thread = None

    def on_enter(self):
        if self._thread is not None:
            return
        mb = self.info.asset_size / 1e6
        size = f", {mb:.0f} megabytes" if mb else ""
        self.speech.say(f"Downloading {self.info.title}{size}. The game will "
                        "restart when the download finishes. "
                        "Press Escape to cancel.")
        self._thread = threading.Thread(target=self._work, daemon=True)
        self._thread.start()

    def _work(self):
        try:
            self.staging = updater.make_staging_dir()
            archive = updater.download(
                self.info, self.staging,
                progress=self._on_progress, cancelled=self.cancelled)
            self.new_root = updater.extract(archive, self.staging / "unpacked")
            archive.unlink(missing_ok=True)
        except updater.UpdateCancelled:
            pass
        except Exception as exc:
            log.warning("Update download failed: %s", exc)
            self.error = ("The download failed. Check your internet "
                          "connection and try again later.")
        finally:
            self.done.set()

    def _on_progress(self, done, total):
        if total > 0:
            self.progress = done / total

    def update(self, dt):
        if self._finished:
            return
        quarter = int(self.progress * 4)
        if quarter > self._spoken_quarter and quarter < 4:
            self._spoken_quarter = quarter
            self.speech.queue(f"{quarter * 25} percent.")
        if not self.done.is_set():
            return
        self._finished = True
        if self.cancelled.is_set():
            self.game.scenes.pop()
        elif self.error or self.new_root is None:
            self.speech.say(self.error or "The download failed.")
            self.audio.menu_edge()
            self.game.scenes.pop()
        else:
            self.speech.say("Download complete. Restarting the game to "
                            "finish the update. See you in a moment.")
            profile_mod.save(self.game.profile)
            updater.apply_and_restart(self.new_root, self.staging)
            self.game.scenes.quit()

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or self._finished:
            return
        if event.key == pygame.K_ESCAPE:
            self.cancelled.set()
            self.speech.say("Update cancelled.")
            self.audio.menu_back()
            if self.done.is_set():
                self._finished = True
                self.game.scenes.pop()
            # otherwise update() pops once the worker notices the flag
        elif event.key == pygame.K_TAB:
            self.speech.say(f"{self.progress * 100:.0f} percent downloaded.")
