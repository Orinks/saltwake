"""Settings: speech rate, audio volume, tide marks difficulty, save wipe."""

import pygame

from core.menu import AccessibleMenu, MenuItem, BACK
from core.scenes import Scene
from game import profile as profile_mod


class SettingsScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.menu = None
        self.confirm_wipe = False

    def on_enter(self):
        self._build_menu()

    def _build_menu(self):
        self.confirm_wipe = False
        profile = self.game.profile
        settings = profile["settings"]
        items = [
            MenuItem(f"Speech rate: {settings['speech_rate']}", "rate",
                     "Left and right arrows adjust while focused, or Enter to step up."),
            MenuItem(f"Audio volume: {int(settings['audio_volume'] * 100)} percent", "volume",
                     "Left and right arrows adjust while focused."),
            MenuItem(f"Music volume: {int(settings.get('music_volume', 0.35) * 100)} percent",
                     "music", "Left and right arrows adjust while focused. "
                     "F3 and F4 do the same anywhere in the game."),
            MenuItem(f"Music: {'on' if settings.get('music_enabled', True) else 'off'}",
                     "music_toggle", "Enter toggles. F2 does the same anywhere."),
        ]
        if profile["stats"].get("bosses_beaten", 0) > 0:
            items.append(MenuItem(
                f"Tide marks: {profile['tide_marks']}", "marks",
                "Difficulty. Each mark makes contests harder and pays ten percent "
                "more pearls. Left and right adjust."))
        items.append(MenuItem("Erase all progress", "wipe",
                              "Starts the story over from the first arrival. Asks twice."))
        items.append(MenuItem("Back", "back"))
        self.menu = AccessibleMenu("Settings.", items, self.speech, self.audio)
        self.menu.open()

    def _adjust(self, what: str, delta: int):
        profile = self.game.profile
        settings = profile["settings"]
        if what == "rate":
            rate = self.speech.adjust_rate(delta * 5)
            settings["speech_rate"] = rate
            self.speech.say(f"Speech rate {rate}.")
        elif what == "volume":
            vol = self.audio.set_volume(settings["audio_volume"] + delta * 0.1)
            settings["audio_volume"] = round(vol, 2)
            self.audio.menu_select()
            self.speech.say(f"Volume {int(vol * 100)} percent.")
        elif what == "music":
            vol = self.game.music.set_volume(
                settings.get("music_volume", 0.35) + delta * 0.05)
            settings["music_volume"] = round(vol, 2)
            self.speech.say(f"Music volume {int(vol * 100)} percent.")
        elif what == "marks":
            max_marks = 5
            profile["tide_marks"] = max(0, min(max_marks, profile["tide_marks"] + delta))
            self.speech.say(f"Tide marks {profile['tide_marks']}.")
        profile_mod.save(profile)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        focused = self.menu.items[self.menu.index].value if self.menu.items else None
        adjustable = ("rate", "volume", "music", "marks")
        if event.key == pygame.K_LEFT and focused in adjustable:
            self._adjust(focused, -1)
            return
        if event.key == pygame.K_RIGHT and focused in adjustable:
            self._adjust(focused, 1)
            return
        result = self.menu.handle_event(event)
        if result is None:
            return
        if result is BACK or result == "back":
            profile_mod.save(self.game.profile)
            self.game.scenes.pop()
        elif result == "music_toggle":
            on = self.game.music.toggle()
            self.game.profile["settings"]["music_enabled"] = on
            profile_mod.save(self.game.profile)
            self.speech.say(f"Music {'on' if on else 'off'}.")
            self._build_menu()
        elif result in adjustable:
            self._adjust(result, 1)
        elif result == "wipe":
            if not self.confirm_wipe:
                self.confirm_wipe = True
                self.speech.say("This erases every tide, every pearl, and every page. "
                                "Select it once more to confirm, or move away to cancel.")
            else:
                self.game.profile = profile_mod.new_profile()
                profile_mod.save(self.game.profile)
                self.speech.say("The slate is wiped. The sea begins again.")
                self._build_menu()
