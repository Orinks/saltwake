"""Accessible menu widget.

Conventions shared by every menu in the game:
- Up/Down move and speak the focused item ("label, x of y").
- Enter or Space activates. Escape backs out (returns BACK).
- Home/End jump. Typing a letter jumps to the next item starting with it.
- H speaks the focused item's help text, R repeats the last speech.
- The menu announces its title and item count when opened.
"""

from typing import Callable, List, Optional

import pygame

BACK = object()  # sentinel returned when the player backs out


class MenuItem:
    def __init__(self, label: str, value=None, help_text: str = "",
                 enabled: bool = True, speak_label: Optional[str] = None):
        self.label = label
        self.value = value if value is not None else label
        self.help_text = help_text
        self.enabled = enabled
        self.speak_label = speak_label or label


class AccessibleMenu:
    def __init__(self, title: str, items: List[MenuItem], speech, audio,
                 intro: str = "", wrap: bool = True, escapable: bool = True):
        self.title = title
        self.items = items
        self.speech = speech
        self.audio = audio
        self.intro = intro
        self.wrap = wrap
        self.escapable = escapable
        self.index = 0

    def open(self) -> None:
        parts = [self.title]
        if self.intro:
            parts.append(self.intro)
        parts.append(f"{len(self.items)} options. Use up and down arrows, Enter to select.")
        self.speech.say(" ".join(parts))
        if self.items:
            self.speech.queue(self._item_text())

    def _item_text(self) -> str:
        item = self.items[self.index]
        suffix = "" if item.enabled else ", unavailable"
        return f"{item.speak_label}{suffix}. {self.index + 1} of {len(self.items)}."

    def speak_current(self) -> None:
        if self.items:
            self.speech.say(self._item_text())

    def _move(self, delta: int) -> None:
        if not self.items:
            return
        new = self.index + delta
        if self.wrap:
            new %= len(self.items)
        else:
            if new < 0 or new >= len(self.items):
                self.audio.menu_edge()
                return
        self.index = new
        self.audio.menu_move()
        self.speak_current()

    def _jump_letter(self, char: str) -> None:
        n = len(self.items)
        for offset in range(1, n + 1):
            i = (self.index + offset) % n
            if self.items[i].label.lower().startswith(char):
                self.index = i
                self.audio.menu_move()
                self.speak_current()
                return

    def handle_event(self, event):
        """Returns the selected item's value, BACK, or None if still browsing."""
        if event.type != pygame.KEYDOWN:
            return None
        key = event.key
        if key == pygame.K_UP:
            self._move(-1)
        elif key == pygame.K_DOWN:
            self._move(1)
        elif key == pygame.K_HOME:
            self.index = 0
            self.speak_current()
        elif key == pygame.K_END:
            self.index = len(self.items) - 1
            self.speak_current()
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            if not self.items:
                return None
            item = self.items[self.index]
            if not item.enabled:
                self.audio.menu_edge()
                self.speech.say(f"{item.label} is unavailable. {item.help_text}".strip())
                return None
            self.audio.menu_select()
            return item.value
        elif key == pygame.K_ESCAPE and self.escapable:
            self.audio.menu_back()
            return BACK
        elif key == pygame.K_h:
            item = self.items[self.index] if self.items else None
            if item and item.help_text:
                self.speech.say(item.help_text)
            else:
                self.speech.say("No help for this item.")
        elif key == pygame.K_r:
            self.speech.repeat_last()
        elif event.unicode and event.unicode.isalnum():
            self._jump_letter(event.unicode.lower())
        return None
