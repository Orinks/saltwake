"""Title menu."""

import pygame

from core.menu import AccessibleMenu, MenuItem, BACK
from core.scenes import Scene


class MainMenuScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.menu = None

    def on_enter(self):
        self.game.music.play("saltwake_theme")
        profile = self.game.profile
        returning = profile["tides"] > 0 or profile["seen_storylets"]
        first = MenuItem("Continue" if returning else "Begin", "start",
                         "Greywater Quay is waiting.")
        items = [
            first,
            MenuItem("How to play", "help",
                     "The manual: nine pages, read by page or line by line."),
            MenuItem("Settings", "settings", "Speech, audio, difficulty."),
            MenuItem("Exit", "exit"),
        ]
        self.menu = AccessibleMenu(
            "Saltwake.", items, self.speech, self.audio,
            intro="A watersports roguelite where the sea remembers.",
            escapable=False)
        self.menu.open()

    def on_resume(self):
        self.on_enter()

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or self.menu is None:
            return
        result = self.menu.handle_event(event)
        if result is None or result is BACK:
            return
        if result == "start":
            from scenes.harbor import HarborScene
            self.game.scenes.push(HarborScene(self.game))
        elif result == "help":
            from scenes.help_scene import HelpScene
            self.game.scenes.push(HelpScene(self.game))
        elif result == "settings":
            from scenes.settings_scene import SettingsScene
            self.game.scenes.push(SettingsScene(self.game))
        elif result == "exit":
            from game import profile as profile_mod
            profile_mod.save(self.game.profile)
            self.speech.say("Goodbye.")
            self.game.scenes.quit()
