"""Achievements: the coast's marks, browsable by category.

Pick a category, arrow through its marks. Unlocked ones speak their name
and story; locked ones speak their goal, except hidden ones, which stay
"a secret the sea is keeping" until earned. Enter or H reads the detail.
"""

import pygame

from core.menu import AccessibleMenu, MenuItem, BACK
from core.scenes import Scene
from game import achievements


class AchievementsScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.menu = None
        self.mode = "categories"

    def on_enter(self):
        self._categories_menu()

    def _unlocked_count(self, achs) -> int:
        profile = self.game.profile
        return sum(1 for a in achs if achievements.is_unlocked(profile, a["id"]))

    def _categories_menu(self, interrupt: bool = True):
        self.mode = "categories"
        all_achs = achievements.all_achievements()
        items = []
        for category in achievements.categories():
            achs = [a for a in all_achs if a["category"] == category["id"]]
            done = self._unlocked_count(achs)
            items.append(MenuItem(
                f"{category['title']}. {done} of {len(achs)}",
                value=("category", category, achs),
                help_text=category.get("description", "")))
        items.append(MenuItem("Close", value=("back", None, None)))
        total_done = self._unlocked_count(all_achs)
        self.menu = AccessibleMenu(
            "Achievements.", items, self.speech, self.audio,
            intro=f"{total_done} of {len(all_achs)} marks made. "
                  "Enter a category to browse them.")
        self.menu.open(interrupt=interrupt)

    def _entry(self, ach) -> tuple[str, str]:
        """(spoken label, detail) respecting hidden achievements."""
        unlocked = achievements.is_unlocked(self.game.profile, ach["id"])
        if unlocked:
            return f"{ach['name']}, unlocked", ach["description"]
        if ach.get("hidden"):
            return (f"{achievements.HIDDEN_NAME}, locked",
                    achievements.HIDDEN_HELP)
        return f"{ach['name']}, locked", ach["description"]

    def _list_menu(self, category: dict, achs: list, interrupt: bool = True):
        self.mode = "list"
        items = []
        for ach in achs:
            label, detail = self._entry(ach)
            items.append(MenuItem(label, value=("entry", label, detail),
                                  help_text=detail))
        items.append(MenuItem("Back to the categories", value=("back", None, None)))
        done = self._unlocked_count(achs)
        self.menu = AccessibleMenu(
            f"{category['title']}. {done} of {len(achs)} made.",
            items, self.speech, self.audio)
        self.menu.open(interrupt=interrupt)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or self.menu is None:
            return
        result = self.menu.handle_event(event)
        if result is None:
            return
        if result is BACK or result[0] == "back":
            if self.mode == "list":
                self._categories_menu()
            else:
                self.game.scenes.pop()
            return
        if result[0] == "category":
            _, category, achs = result
            self._list_menu(category, achs)
        elif result[0] == "entry":
            _, label, detail = result
            self.speech.say(f"{label}. {detail}")
