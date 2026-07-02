"""Ties: where you stand with the people of the quay.

One entry per character you have met, spoken as a named closeness level
rather than a bare number. Enter (or H) reads the detail: the regard the
quay's gossip would put on it, plus any bonds the story has forged.
"""

import pygame

from core.menu import AccessibleMenu, MenuItem, BACK
from core.scenes import Scene
from game import profile as profile_mod

# Affinity floor -> spoken closeness level, highest floor wins.
LEVELS = [
    (8, "family in all but paper"),
    (6, "fast friends"),
    (4, "trusted"),
    (2, "warming to you"),
    (1, "newly acquainted"),
    (0, "strangers, so far"),
]

# id, spoken name, quality gate to appear, and story bonds worth naming.
PEOPLE = [
    ("odessa", "Odessa, the harbormaster", "met_odessa", [
        ("recognized", "She knows who the sea gave back."),
        ("odessa_sworn", "Sworn crew: boards dry, lines free."),
    ]),
    ("mirabel", "Mirabel, behind the bar", "met_mirabel", [
        ("knows_rens_chowder", "She taught you Ren's chowder, off the page."),
        ("mirabel_truth", "She knows the captain, and paid an installment back."),
    ]),
    ("brick", "Brick, the old champion", "met_brick", [
        ("brick_truth", "He told you about year seven."),
        ("brick_coaching", "He coaches you at first light, from the wall."),
        ("brick_riding", "He is back on the water."),
        ("brick_entered", "Entered for the invitational, with you as his second."),
    ]),
    ("nereus", "Nereus, keeper of the Almanac", "met_nereus", [
        ("nereus_diving", "Diving again. The slate tally is climbing."),
        ("nereus_new_book", "Keeping the new book: Greywater, living."),
    ]),
    ("cass", "Cass Veyle, your rival", "met_cass", [
        ("cass_knows", "She knows whose record she has been chasing."),
        ("cass_listening", "Learning to hear the water."),
        ("cass_heard", "She beat you fair, racing the water itself."),
    ]),
    ("sefton", "Sefton, the chandler", "met_sefton", [
        ("sefton_tithe", "You carry his storm tithe."),
        ("brothers_reconciled", "Aldous came home when the season turned."),
    ]),
    ("keeper", "Edras, the Keeper", "met_keeper", [
        ("promised_keeper", "You promised him you would finish the rescue."),
        ("liss_saved", "His daughter is home. The lamp rests."),
    ]),
    ("liss", "Liss, the lamp keeper's girl", "liss_saved", [
        ("key_answered", "The brass key is home in its locker."),
        ("liss_apprentice", "Your apprentice. Her light rides home."),
    ]),
]


def closeness(affinity: int) -> str:
    for floor, name in LEVELS:
        if affinity >= floor:
            return name
    return LEVELS[-1][1]


def relationship_entries(profile: dict) -> list[tuple[str, str]]:
    """(spoken entry, detail help) pairs for everyone you have met."""
    out = []
    for pid, name, gate, bonds in PEOPLE:
        if not profile_mod.get_quality(profile, gate):
            continue
        affinity = profile_mod.get_quality(profile, f"affinity_{pid}")
        details = [f"Regard {affinity}."]
        details += [text for quality, text in bonds
                    if profile_mod.get_quality(profile, quality)]
        out.append((f"{name}: {closeness(affinity)}", " ".join(details)))
    return out


class RelationshipsScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.menu = None

    def on_enter(self):
        entries = relationship_entries(self.game.profile)
        items = [MenuItem(text, value=("entry", text, help_text), help_text=help_text)
                 for text, help_text in entries]
        if not items:
            items.append(MenuItem("Nobody at the quay knows you yet.",
                                  value=None, enabled=False,
                                  help_text="Talk to people at the Brinehouse and "
                                            "around the harbor. Ties grow from there."))
        items.append(MenuItem("Close", value=("back", None, None)))
        self.menu = AccessibleMenu(
            "Ties.", items, self.speech, self.audio,
            intro="How the quay holds you, one person at a time. "
                  "Enter or H for the detail.")
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
