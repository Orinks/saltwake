"""The sea chest: keepsakes the water gave back, and who they belong to.

One entry per keepsake. Carried ones speak their find and the hint about
their owner; delivered ones stay in the chest's ledger, marked home.
Enter or H reads the detail, Escape closes.
"""

import pygame

from core.menu import AccessibleMenu, MenuItem, BACK
from core.scenes import Scene
from game import keepsakes


def sea_chest_entries(profile: dict) -> list[tuple[str, str]]:
    """(spoken entry, detail help) pairs: carried first, then delivered."""
    out = []
    for kid in profile.get("keepsakes", []):
        keepsake = keepsakes.by_id(kid)
        if keepsake:
            out.append((keepsake["name"],
                        f"{keepsake['found']} {keepsake['hint']}"))
    for kid in profile.get("keepsakes_delivered", []):
        keepsake = keepsakes.by_id(kid)
        if keepsake:
            out.append((f"{keepsake['name']}, given home",
                        "Delivered. The chest keeps the entry the way "
                        "harbors keep everything: settled, and remembered."))
    return out


class SeaChestScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.menu = None

    def on_enter(self):
        profile = self.game.profile
        entries = sea_chest_entries(profile)
        items = [MenuItem(text, value=("entry", text, help_text), help_text=help_text)
                 for text, help_text in entries]
        if not items:
            items.append(MenuItem("Nothing but dry canvas and possibility.",
                                  value=None, enabled=False,
                                  help_text="The sea returns what it trusts. "
                                            "Dive the wrecks; sometimes what "
                                            "comes up is somebody's."))
        items.append(MenuItem("Close the sea chest", value=("back", None, None)))
        carried = len(profile.get("keepsakes", []))
        delivered = len(profile.get("keepsakes_delivered", []))
        self.menu = AccessibleMenu(
            "The sea chest.", items, self.speech, self.audio,
            intro=f"{carried} carried, {delivered} given home. "
                  "Enter or H for what each one is and who might know it.")
        self.menu.open()

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or self.menu is None:
            return
        result = self.menu.handle_event(event)
        if result is None:
            return
        if result is BACK or result[0] == "back":
            self.game.scenes.pop()
            return
        _, text, help_text = result
        self.speech.say(f"{text}. {help_text}")
