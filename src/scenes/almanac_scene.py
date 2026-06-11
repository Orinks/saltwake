"""The Drowned Almanac: collected lore pages, readable at the quay."""

import json
import os

import pygame

from core.menu import AccessibleMenu, MenuItem, BACK
from core.paths import STORY_DIR
from core.scenes import Scene


def load_pages() -> list[dict]:
    path = os.path.join(STORY_DIR, "almanac_pages.json")
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f).get("pages", [])


class AlmanacScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.menu = None
        self.reading = None
        self.page_index = 0

    def on_enter(self):
        self._build_menu()

    def _build_menu(self):
        self.reading = None
        all_pages = load_pages()
        found = self.game.profile["almanac"]
        items = []
        for page in all_pages:
            if page["id"] in found:
                items.append(MenuItem(page["title"], value=page,
                                      help_text="Enter to read."))
        if not items:
            items.append(MenuItem("Only water stains and empty bindings, so far.",
                                  value=None, enabled=False,
                                  help_text="Pages are found at sea: dive deep, "
                                            "follow the story, listen at beacons."))
        items.append(MenuItem("Close the Almanac", value="back"))
        self.menu = AccessibleMenu(
            f"The Drowned Almanac. {len(found)} of {len(all_pages)} pages recovered.",
            items, self.speech, self.audio)
        self.menu.open()

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if self.reading is not None:
            key = event.key
            paragraphs = self.reading["text"]
            if key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_DOWN):
                self.page_index += 1
                if self.page_index < len(paragraphs):
                    self.speech.say(paragraphs[self.page_index])
                else:
                    self.speech.say("End of the page.")
                    self._build_menu()
            elif key == pygame.K_UP:
                self.page_index = max(0, self.page_index - 1)
                self.speech.say(paragraphs[self.page_index])
            elif key == pygame.K_r:
                self.speech.repeat_last()
            elif key == pygame.K_ESCAPE:
                self._build_menu()
            return
        result = self.menu.handle_event(event)
        if result is None:
            return
        if result is BACK or result == "back":
            self.game.scenes.pop()
        elif isinstance(result, dict):
            self.reading = result
            self.page_index = 0
            text = result["text"]
            self.speech.say(f"{result['title']}. {text[0] if text else ''} "
                            "Enter for more, Escape to close.")
