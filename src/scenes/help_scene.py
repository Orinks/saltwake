"""Page-by-page, line-by-line spoken manual, after Freight Fate's HelpState.

Left and Right arrows change pages (wrapping), Up and Down read line by
line, Enter reads the whole page, R repeats, Escape goes back.
"""

import pygame

from core.scenes import Scene

HELP_PAGES = [
    ("The goal", [
        "You are the Tideborn: washed up at Greywater Quay with no memory,",
        "a brass key, and a habit of not drowning.",
        "Set out on tides, expeditions across reaches of open water,",
        "and bring salvage home, where it becomes pearls.",
        "Every run moves the story: the people of the quay have more to say,",
        "and the Drowned Almanac fills with pages about who you were.",
        "Wrecking is never the end. The sea returns you, and the story goes on.",
    ]),
    ("Menus", [
        "All menus use Up and Down arrows, Enter to select, Escape to go back.",
        "Home and End jump to the first and last option.",
        "Type a letter to jump to options starting with that letter.",
        "Press H on any option for what it does. Press R to repeat the last speech.",
    ]),
    ("Setting out", [
        "Embark from the quay to start a tide in your active vessel.",
        "Each leg of the chart offers two or three headings:",
        "a contest, something on the water, a friendly beacon,",
        "drifting salvage, or rough water. Choose one and commit.",
        "Press T at any time at sea for hull, grit, salvage, and position.",
        "Weather changes leg by leg and makes everything easier or harder.",
        "Beacons are safe water: rest, patch the hull for a supply,",
        "or accept a Tiding, a boon that lasts the rest of the tide.",
    ]),
    ("Contests, the shared shape", [
        "Every contest starts with spoken rules. Enter begins, H repeats the rules.",
        "Three rising tones count you in.",
        "Cues come as panned sound plus a spoken word:",
        "answer with the matching arrow key inside the window.",
        "R repeats speech, T speaks status, Escape abandons with no reward",
        "and no shame. You are never trapped in a contest.",
    ]),
    ("Racing and slalom", [
        "Boat race: gates call from a side. Left, right, or up for dead ahead.",
        "Clean gates build speed. Beat the pacer across the line.",
        "Jet ski slalom: buoys alternate sides and the tempo climbs.",
        "Carve around each with left and right. Three misses washes you out.",
    ]),
    ("Storms, diving, fishing, rescue", [
        "Storm crossing: steer INTO the gusts. Gust on the left, press right.",
        "Gust on the right, press left. Deep tone ahead, brace with down.",
        "Every mistake costs hull.",
        "Dive salvage: sonar pings lean toward the cache, lower pitch means",
        "deeper than you. Down descends, up ascends, left and right swim,",
        "space grabs. Surface at depth zero before your breath runs out.",
        "Fishing: when the line sings high, reel with space. When the tone",
        "drops low, hands off, or give line with down. Reel against a run",
        "and the line snaps.",
        "Rescue: answer the whistle's direction three times to come alongside,",
        "then keep the drifting tow tone centered. Brace with down when",
        "they panic.",
    ]),
    ("Wreck and homecoming", [
        "Turn for home after a reach warden falls, or press deeper for more.",
        "Salvage converts to pearls in full when you make it home.",
        "A wreck banks half, and costs nothing else: renown, story,",
        "almanac pages, and friendships all survive.",
        "The sea keeps score of what it lends you. Wrecks have their own story.",
    ]),
    ("Greywater Quay", [
        "The Brinehouse tavern: talk to the regulars. Their stories deepen",
        "with your renown, your deeds, and how often you visit.",
        "The harbormaster's office: Odessa, the ledgers, and the main story.",
        "Shipyard: buy and choose vessels. Each handles contests differently.",
        "Chandlery: permanent gear that works on every tide.",
        "The Drowned Almanac: read the recovered pages.",
        "Chronicle: your record across every tide.",
        "Renown opens deeper water. The story opens the deepest water of all.",
    ]),
    ("Sound and speech", [
        "Everything the sound tells you is also spoken. Nothing is audio-only.",
        "Pan means position: left, center, right. Pitch means depth or tension.",
        "Page Up and Page Down change speech rate anywhere.",
        "F2 toggles music. F3 and F4 lower and raise music volume.",
        "Music is atmosphere only; it never carries information.",
        "Speech follows your screen reader through Prism: NVDA, JAWS, SAPI,",
        "and more. Audio volume and the rest live in Settings.",
    ]),
]


class HelpScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.page = 0
        self.line = -1  # -1 = page title

    def on_enter(self):
        self.speech.say(
            "How to play. Left and Right arrows change pages. Up and Down arrows "
            "read line by line. Enter reads the whole page. Escape goes back. "
            + self._page_title())

    def _page_title(self) -> str:
        title, lines = HELP_PAGES[self.page]
        return f"Page {self.page + 1} of {len(HELP_PAGES)}: {title}. {len(lines)} lines."

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        title, lines = HELP_PAGES[self.page]
        if event.key == pygame.K_ESCAPE:
            self.audio.menu_back()
            self.game.scenes.pop()
        elif event.key in (pygame.K_RIGHT, pygame.K_PAGEDOWN):
            self.page = (self.page + 1) % len(HELP_PAGES)
            self.line = -1
            self.audio.menu_move()
            self.speech.say(self._page_title())
        elif event.key in (pygame.K_LEFT, pygame.K_PAGEUP):
            self.page = (self.page - 1) % len(HELP_PAGES)
            self.line = -1
            self.audio.menu_move()
            self.speech.say(self._page_title())
        elif event.key == pygame.K_DOWN:
            self.line = min(self.line + 1, len(lines) - 1)
            self.speech.say(lines[self.line])
        elif event.key == pygame.K_UP:
            self.line = max(self.line - 1, 0)
            self.speech.say(lines[self.line])
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.speech.say(f"{title}. " + " ".join(lines))
        elif event.key == pygame.K_r:
            self.speech.repeat_last()
