"""The Chronicle: your record across every tide, one entry per menu item.

Arrow through the entries instead of sitting through one long report.
Enter re-reads the focused entry with its flavor line; H does the same.
"Copy to clipboard" at the bottom (or C anywhere in the menu) puts the
whole record on the system clipboard as plain text, ready to paste.
"""

import pygame

from core import clipboard
from core.menu import AccessibleMenu, MenuItem, BACK
from core.scenes import Scene
from game import profile as profile_mod


def chronicle_entries(profile: dict) -> list[tuple[str, str]]:
    """(spoken entry, flavor help) pairs, in reading order."""
    s = profile["stats"]
    level = profile_mod.renown_level(profile)
    to_next = profile_mod.renown_to_next(profile)
    renown_help = (f"{to_next} renown to the next level."
                   if to_next is not None else "The coast has no higher rank to give.")
    return [
        (f"Tides set out: {profile['tides']}",
         "Every time you cast off from Greywater Quay."),
        (f"Homecomings: {profile['homecomings']}",
         "Tides that ended at the dock, catch lashed down."),
        (f"Wrecks: {profile['wrecks']}",
         "Tides the sea ended early. It kept score; so do you."),
        (f"Renown: {profile['renown']}, level {level}", renown_help),
        (f"Pearls in hand: {profile['pearls']}",
         "Spend them at the shipyard and chandlery."),
        (f"Races won: {s['races_won']}",
         "First across the line, wake still settling."),
        (f"Slaloms cleared: {s['slaloms_cleared']}",
         "Buoy lines carved clean."),
        (f"Dives completed: {s['dives_completed']}",
         "Hauls brought up from the green dark."),
        (f"Storms survived: {s['storms_survived']}",
         "Crossings the weather did not win."),
        (f"Fish landed: {s['fish_caught']}",
         "Silver over the rail, supplies in the locker."),
        (f"Souls rescued: {s['rescues']}",
         "Word of a rescue travels farther than any race result."),
        (f"Wardens bested: {s['bosses_beaten']}",
         "Reach wardens met and beaten at the edge of deeper water."),
        (f"Lifetime salvage: {s['salvage_lifetime']}",
         "Everything ever winched aboard, banked or lost."),
        (f"Almanac pages found: {len(profile['almanac'])}",
         "Read them at the quay, in the Drowned Almanac."),
    ]


def chronicle_text(profile: dict) -> str:
    """The whole Chronicle as plain text, one entry per line."""
    lines = [f"Saltwake: the Chronicle of {profile.get('name', 'Tideborn')}."]
    lines += [text for text, _ in chronicle_entries(profile)]
    return "\n".join(lines)


class ChronicleScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.menu = None

    def on_enter(self):
        items = [MenuItem(text, value=("entry", text, help_text), help_text=help_text)
                 for text, help_text in chronicle_entries(self.game.profile)]
        items.append(MenuItem("Copy the Chronicle to the clipboard",
                              value=("copy", None, None),
                              help_text="Puts your whole record on the clipboard "
                                        "as plain text, ready to paste anywhere."))
        items.append(MenuItem("Close the Chronicle", value=("back", None, None)))
        self.menu = AccessibleMenu(
            "The Chronicle.", items, self.speech, self.audio,
            intro="Your record across every tide. C copies it to the clipboard.")
        self.menu.open()

    def _copy(self):
        if clipboard.copy_text(chronicle_text(self.game.profile)):
            self.audio.menu_select()
            self.speech.say("Chronicle copied to the clipboard.")
        else:
            self.speech.say("Copying failed. No clipboard is available here.")

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or self.menu is None:
            return
        if event.key == pygame.K_c:
            self._copy()
            return
        result = self.menu.handle_event(event)
        if result is None:
            return
        if result is BACK or result[0] == "back":
            self.game.scenes.pop()
            return
        if result[0] == "copy":
            self._copy()
            return
        _, text, help_text = result
        self.speech.say(f"{text}. {help_text}")
