"""Title menu."""

import pygame

from core.menu import AccessibleMenu, MenuItem, BACK
from core.scenes import Scene

HOW_TO_PLAY = (
    "Saltwake is a watersports roguelite played by ear. "
    "You live at Greywater Quay and set out on tides: expeditions across reaches of "
    "open water. At sea you choose headings, and each heading holds a contest, a story, "
    "a hazard, or a haul. Contests are boat races, jet ski slaloms, free dives, storm "
    "crossings, fishing, and rescues, all played with the arrow keys against spoken and "
    "panned sound cues. "
    "Salvage you carry converts to pearls when you make it home; a wreck banks only half, "
    "but a wreck is never the end. The sea returns you to the quay, the town reacts, and "
    "the story grows: every run, the people of the quay have more to say, and the Drowned "
    "Almanac fills with pages about who you were before the water took your memory. "
    "Universal keys: arrow keys navigate, Enter selects, Escape goes back, "
    "R repeats the last speech, T speaks your status at sea, H explains the focused item. "
    "Spend pearls on vessels and gear, earn renown to open deeper water, and when you are "
    "strong enough, follow the story into the Glass Squall."
)


class MainMenuScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.menu = None

    def on_enter(self):
        profile = self.game.profile
        returning = profile["tides"] > 0 or profile["seen_storylets"]
        first = MenuItem("Continue" if returning else "Begin", "start",
                         "Greywater Quay is waiting.")
        items = [
            first,
            MenuItem("How to play", "help", "A spoken guide to everything."),
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
            self.speech.say(HOW_TO_PLAY)
        elif result == "settings":
            from scenes.settings_scene import SettingsScene
            self.game.scenes.push(SettingsScene(self.game))
        elif result == "exit":
            from game import profile as profile_mod
            profile_mod.save(self.game.profile)
            self.speech.say("Goodbye.")
            self.game.scenes.quit()
