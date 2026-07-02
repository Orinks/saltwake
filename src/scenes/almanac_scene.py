"""The Drowned Almanac: collected lore pages, readable at the quay.

Nereus's binding order: five volumes, each a menu of recovered pages.
Pick a volume, pick a page, read it paragraph by paragraph with the usual
controls: Enter or Down for the next, Up for the previous, R repeats,
Escape backs out a level.
"""

import pygame

from core.menu import AccessibleMenu, MenuItem, BACK
from core.scenes import Scene
from game import almanac


class AlmanacScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.menu = None
        self.mode = "volumes"
        self.volume = None
        self.reading = None
        self.page_index = 0

    def on_enter(self):
        self.game.music.play("quiet_lines")
        self._volumes_menu()

    def _found_in(self, volume_id: str) -> list[dict]:
        found = self.game.profile["almanac"]
        return [p for p in almanac.pages()
                if p["volume"] == volume_id and p["id"] in found]

    # --- menus -----------------------------------------------------------
    def _volumes_menu(self, interrupt: bool = True):
        self.mode = "volumes"
        self.reading = None
        self.volume = None
        found_total = len(self.game.profile["almanac"])
        total = len(almanac.pages())
        items = []
        for volume in almanac.volumes():
            in_volume = [p for p in almanac.pages() if p["volume"] == volume["id"]]
            found = self._found_in(volume["id"])
            items.append(MenuItem(
                f"{volume['title']}. {len(found)} of {len(in_volume)} pages",
                value=("volume", volume), enabled=bool(found),
                help_text=volume.get("description", "")
                if found else "Nothing recovered for this volume yet."))
        if found_total == 0:
            items = [MenuItem("Only water stains and empty bindings, so far.",
                              value=None, enabled=False,
                              help_text="Pages are found at sea: dive deep, fish "
                                        "well, follow the story, listen at beacons.")]
        items.append(MenuItem("Close the Almanac", value=("back", None)))
        self.menu = AccessibleMenu(
            f"The Drowned Almanac. {found_total} of {total} pages recovered.",
            items, self.speech, self.audio)
        self.menu.open(interrupt=interrupt)

    def _pages_menu(self, volume: dict, interrupt: bool = True):
        self.mode = "pages"
        self.reading = None
        self.volume = volume
        items = [MenuItem(page["title"], value=("page", page),
                          help_text="Enter to read.")
                 for page in self._found_in(volume["id"])]
        items.append(MenuItem("Back to the bindings", value=("back", None)))
        self.menu = AccessibleMenu(f"{volume['title']}.", items,
                                   self.speech, self.audio)
        self.menu.open(interrupt=interrupt)

    # --- events ----------------------------------------------------------
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if self.reading is not None:
            self._reading_keys(event.key)
            return
        result = self.menu.handle_event(event)
        if result is None:
            return
        if result is BACK or result[0] == "back":
            if self.mode == "pages":
                self._volumes_menu()
            else:
                self.game.scenes.pop()
            return
        if result[0] == "volume":
            self._pages_menu(result[1])
        elif result[0] == "page":
            self.reading = result[1]
            self.page_index = 0
            text = self.reading["text"]
            self.speech.say(f"{self.reading['title']}. {text[0] if text else ''} "
                            "Enter for more, Escape to close.")

    def _reading_keys(self, key):
        paragraphs = self.reading["text"]
        if key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_DOWN):
            self.page_index += 1
            if self.page_index < len(paragraphs):
                self.speech.say(paragraphs[self.page_index])
            else:
                self.speech.say("End of the page.")
                self._pages_menu(self.volume, interrupt=False)
        elif key == pygame.K_UP:
            self.page_index = max(0, self.page_index - 1)
            self.speech.say(paragraphs[self.page_index])
        elif key == pygame.K_r:
            self.speech.repeat_last()
        elif key == pygame.K_ESCAPE:
            self._pages_menu(self.volume)
