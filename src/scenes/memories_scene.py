"""Memories: the story so far, re-readable.

Every storylet you have seen stays available here, grouped by who told it.
Pick a teller, pick a moment, and read it again page by page with the same
controls as the Almanac: Enter or Down for the next paragraph, Up for the
previous, R repeats, Escape backs out a level. Replays are the telling
only; they never re-apply effects or reopen choices.
"""

import pygame

from core.menu import AccessibleMenu, MenuItem, BACK
from core.scenes import Scene

# Arc id -> spoken group label, in reading order.
ARC_GROUPS = [
    ("main", "The tide that turned: the main story"),
    ("jane", "The Lantern Jane"),
    ("odessa", "Odessa"),
    ("mirabel", "Mirabel"),
    ("brick", "Brick"),
    ("nereus", "Nereus"),
    ("cass", "Cass Veyle"),
    ("sefton", "Sefton and Aldous"),
    ("keeper", "Edras, the Keeper"),
    ("liss", "Liss"),
    ("undertow", "The sea itself"),
    ("lore", "Small tides: moments in the reaches"),
]
OTHER_LABEL = "Other moments"


def seen_by_group(profile: dict, story) -> list[tuple[str, list]]:
    """(group label, [storylets]) for everything seen, corpus order kept."""
    seen = profile["seen_storylets"]
    grouped: dict[str, list] = {}
    for storylet in story.storylets.values():
        if seen.get(storylet.id, 0) <= 0 or not storylet.pages:
            continue
        grouped.setdefault(storylet.arc, []).append(storylet)
    out = []
    for arc, label in ARC_GROUPS:
        if grouped.get(arc):
            out.append((label, grouped.pop(arc)))
    leftovers = [s for storylets in grouped.values() for s in storylets]
    if leftovers:
        out.append((OTHER_LABEL, leftovers))
    return out


class MemoriesScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.menu = None
        self.mode = "groups"
        self.group_label = ""
        self.reading = None
        self.page_index = 0

    def on_enter(self):
        self._groups_menu()

    # --- menus -----------------------------------------------------------
    def _groups_menu(self, interrupt: bool = True):
        self.mode = "groups"
        self.reading = None
        groups = seen_by_group(self.game.profile, self.game.story)
        items = []
        for label, storylets in groups:
            count = len(storylets)
            plural = "memory" if count == 1 else "memories"
            items.append(MenuItem(f"{label}. {count} {plural}",
                                  value=("group", label, storylets),
                                  help_text="Enter to browse what you heard."))
        if not items:
            items.append(MenuItem("Nothing to remember yet.",
                                  value=None, enabled=False,
                                  help_text="The story collects here as you live "
                                            "it: tides, tavern talk, deep water."))
        items.append(MenuItem("Close", value=("back", None, None)))
        self.menu = AccessibleMenu(
            "Memories.", items, self.speech, self.audio,
            intro="The story so far, as you heard it. What people said stays said.")
        self.menu.open(interrupt=interrupt)

    def _list_menu(self, label: str, storylets: list, interrupt: bool = True):
        self.mode = "list"
        self.reading = None
        self.group_label = label
        seen = self.game.profile["seen_storylets"]
        items = []
        for storylet in storylets:
            title = storylet.title or "A moment on the water."
            times = seen.get(storylet.id, 0)
            help_text = ("Enter to hear it again."
                         if times <= 1 else f"Heard {times} times. Enter to hear it again.")
            items.append(MenuItem(title, value=("read", storylet, None),
                                  help_text=help_text))
        items.append(MenuItem("Back to the tellers", value=("back", None, None)))
        self.menu = AccessibleMenu(f"{label}.", items, self.speech, self.audio)
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
            if self.mode == "list":
                self._groups_menu()
            else:
                self.game.scenes.pop()
            return
        if result[0] == "group":
            _, label, storylets = result
            self._list_menu(label, storylets)
        elif result[0] == "read":
            self._start_reading(result[1])

    def _start_reading(self, storylet):
        self.reading = storylet
        self.page_index = 0
        header = storylet.title or "A moment on the water."
        if storylet.speaker:
            header = f"{storylet.speaker}. {header}"
        self.speech.say(f"{header} {storylet.pages[0]}")
        self.speech.queue("Enter for more, Escape to close."
                          if len(storylet.pages) > 1 else "Enter or Escape to close.")

    def _reading_keys(self, key):
        pages = self.reading.pages
        if key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_DOWN):
            self.page_index += 1
            if self.page_index < len(pages):
                self.speech.say(pages[self.page_index])
            else:
                self.speech.say("End of the memory.")
                self._list_menu(self.group_label,
                                self._current_group(), interrupt=False)
        elif key == pygame.K_UP:
            self.page_index = max(0, self.page_index - 1)
            self.speech.say(pages[self.page_index])
        elif key == pygame.K_r:
            self.speech.repeat_last()
        elif key == pygame.K_ESCAPE:
            self._list_menu(self.group_label, self._current_group())

    def _current_group(self) -> list:
        for label, storylets in seen_by_group(self.game.profile, self.game.story):
            if label == self.group_label:
                return storylets
        return []
