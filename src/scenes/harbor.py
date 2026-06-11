"""Greywater Quay: the hub between tides.

Everything meta lives here — the tavern crowd whose arcs deepen with every
run, the shipyard and chandlery that spend pearls, the Almanac that collects
the story, and the dock where the next tide starts.
"""

import pygame

from core.menu import AccessibleMenu, MenuItem, BACK
from core.scenes import Scene
from game import data_loader
from game import profile as profile_mod
from game.run import RunState
from scenes.storylet_scene import maybe_play

VESSEL_REQUIREMENTS = {
    "skiff": {},
    "wavecutter": {"renown_level": 1},
    "pelican": {"renown_level": 2},
    "dredger": {"renown_level": 3},
    "swift": {"quality": "cleared_shallows"},
    "lantern_jane": {"quality": "jane_raised", "no_buy": True},
}

NPCS = [
    ("odessa", "Odessa, the harbormaster"),
    ("mirabel", "Mirabel, behind the bar"),
    ("brick", "Brick, by the window with his trophies"),
    ("nereus", "Nereus, ink-stained, surrounded by charts"),
    ("cass", "Cass Veyle, your rival, pretending not to wait for you"),
    ("sefton", "Sefton, the chandler, muttering over knots"),
]


class HarborScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.menu = None
        self.mode = "main"
        self._items_cache = []

    # --- entry -------------------------------------------------------------
    def on_enter(self):
        profile = self.game.profile
        if profile["tides"] == 0 and profile["seen_storylets"].get("arrival_01", 0) == 0:
            if maybe_play(self.game, "quay_arrival"):
                return
        self._main_menu()

    def on_resume(self):
        # Rebuild whichever menu the player was in when a sub-scene popped.
        rebuild = {
            "main": self._main_menu,
            "tavern": self._tavern_menu,
            "shipyard": self._shipyard_menu,
            "chandlery": self._chandlery_menu,
        }.get(self.mode)
        if rebuild:
            rebuild()

    def _main_menu(self):
        self.mode = "main"
        profile = self.game.profile
        level = profile_mod.renown_level(profile)
        items = [
            MenuItem("Set out on the tide", "embark",
                     "Begin a run. What you bank comes home; what you carry can sink."),
            MenuItem("The Brinehouse tavern", "tavern",
                     "Talk to the regulars. Their stories grow with your renown and your deeds."),
            MenuItem("Harbormaster's office", "docks",
                     "Odessa keeps the ledgers, the grudges, and the loaner skiff."),
        ]
        if profile_mod.get_quality(profile, "lighthouse_open"):
            items.append(MenuItem("The lighthouse stair", "lighthouse",
                                  "The Keeper sees further than the lamp does."))
        items += [
            MenuItem("Shipyard", "shipyard", "Buy and choose vessels."),
            MenuItem("Chandlery", "chandlery", "Permanent gear, bought with pearls."),
            MenuItem("The Drowned Almanac", "almanac",
                     "Read the recovered pages of the book the sea is writing about you."),
            MenuItem("Chronicle", "chronicle", "Your record across every tide."),
            MenuItem("Settings", "settings", "Speech rate, audio, difficulty, save."),
            MenuItem("Leave the quay and rest", "quit", "Saves and exits the game."),
        ]
        vessel = data_loader.vessels()[self._active_vessel()]["name"]
        self.menu = AccessibleMenu(
            "Greywater Quay.",
            items, self.speech, self.audio,
            intro=(f"Pearls: {profile['pearls']}. Renown level {level}. "
                   f"Vessel: {vessel}."),
            escapable=False)
        self.menu.open()

    def _active_vessel(self) -> str:
        vid = self.game.profile.get("active_vessel", "skiff")
        if vid not in self.game.profile["unlocked_vessels"]:
            vid = "skiff"
        return vid

    # --- events ----------------------------------------------------------------
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or self.menu is None:
            return
        result = self.menu.handle_event(event)
        if result is None:
            return
        if result is BACK:
            if self.mode != "main":
                self._main_menu()
            return
        handler = {
            "main": self._main_choice,
            "tavern": self._tavern_choice,
            "shipyard": self._shipyard_choice,
            "chandlery": self._chandlery_choice,
        }[self.mode]
        handler(result)

    def _main_choice(self, choice):
        if choice == "embark":
            self._embark()
        elif choice == "tavern":
            self._tavern_menu()
        elif choice == "docks":
            self.menu = None
            if not maybe_play(self.game, "talk_odessa"):
                self.speech.say("Odessa glances up from the ledger. \"Nothing new on my desk. "
                                "Go make something happen, Tideborn.\"")
                self._main_menu()
        elif choice == "lighthouse":
            self.menu = None
            if not maybe_play(self.game, "lighthouse"):
                self.speech.say("The lamp turns. The Keeper does not. \"Come back when the "
                                "sea has said something worth repeating.\"")
                self._main_menu()
        elif choice == "shipyard":
            self._shipyard_menu()
        elif choice == "chandlery":
            self._chandlery_menu()
        elif choice == "almanac":
            from scenes.almanac_scene import AlmanacScene
            self.menu = None
            self.game.scenes.push(AlmanacScene(self.game))
        elif choice == "chronicle":
            self._chronicle()
        elif choice == "settings":
            from scenes.settings_scene import SettingsScene
            self.menu = None
            self.game.scenes.push(SettingsScene(self.game))
        elif choice == "quit":
            profile_mod.save(self.game.profile)
            self.speech.say("Saved. The quay lights stay on for you. Goodbye.")
            self.game.scenes.quit()

    # --- tavern ----------------------------------------------------------------
    def _tavern_menu(self):
        self.mode = "tavern"
        items = [MenuItem(label, value=npc_id) for npc_id, label in NPCS]
        items.append(MenuItem("Back to the quay", value="back"))
        self.menu = AccessibleMenu(
            "The Brinehouse. Low beams, lamp smoke, the day's arguments in progress.",
            items, self.speech, self.audio)
        self.menu.open()

    def _tavern_choice(self, choice):
        if choice == "back":
            self._main_menu()
            return
        self.menu = None
        npc_id = choice
        if not maybe_play(self.game, f"talk_{npc_id}"):
            fallbacks = {
                "odessa": "Odessa raises one finger: wait. Then, eventually: \"Still floating? Good. Keep doing that.\"",
                "mirabel": "Mirabel slides you something warm without being asked. \"On the house. You look like a chapter that hasn't been written yet.\"",
                "brick": "Brick polishes a trophy with his sleeve. \"Tide's wrong for talking. Go ride something.\"",
                "nereus": "Nereus doesn't look up from his charts. \"Unless you've brought me a page, I am professionally asleep.\"",
                "cass": "Cass looks you over like a race she's already won. \"Rest day? Didn't think you believed in those.\"",
                "sefton": "Sefton ties a knot, unties it, ties it better. \"Sea's holding its breath. Bad sign or no sign at all.\"",
            }
            self.speech.say(fallbacks.get(npc_id, "They have nothing new to say, yet."))
            self._tavern_menu()

    # --- shipyard ----------------------------------------------------------------
    def _vessel_available(self, vid: str) -> tuple[bool, str]:
        req = VESSEL_REQUIREMENTS.get(vid, {})
        profile = self.game.profile
        if "renown_level" in req and profile_mod.renown_level(profile) < req["renown_level"]:
            return False, f"Requires renown level {req['renown_level']}."
        if "quality" in req and not profile_mod.get_quality(profile, req["quality"]):
            return False, "The story has not unlocked this hull yet."
        return True, ""

    def _shipyard_menu(self):
        self.mode = "shipyard"
        profile = self.game.profile
        active = self._active_vessel()
        items = []
        for vid, vessel in data_loader.vessels().items():
            owned = vid in profile["unlocked_vessels"]
            if owned:
                mark = "your vessel" if vid == active else "owned"
                items.append(MenuItem(f"{vessel['name']}, {mark}", value=("select", vid),
                                      help_text=vessel["description"]))
            else:
                ok, why = self._vessel_available(vid)
                if VESSEL_REQUIREMENTS.get(vid, {}).get("no_buy"):
                    continue
                label = f"{vessel['name']}, {vessel['cost']} pearls"
                help_text = f"{vessel['description']} {why or vessel['unlock_hint']}"
                items.append(MenuItem(label, value=("buy", vid), help_text=help_text,
                                      enabled=ok and profile["pearls"] >= vessel["cost"]))
        items.append(MenuItem("Back to the quay", value=("back", None)))
        self.menu = AccessibleMenu(
            f"The shipyard. Pearls: {profile['pearls']}. Press H on any hull for details.",
            items, self.speech, self.audio)
        self.menu.open()

    def _shipyard_choice(self, choice):
        action, vid = choice
        profile = self.game.profile
        if action == "back":
            self._main_menu()
            return
        vessel = data_loader.vessels()[vid]
        if action == "select":
            profile["active_vessel"] = vid
            profile_mod.save(profile)
            self.speech.say(f"{vessel['name']} is now your vessel. {vessel['description']}")
        elif action == "buy":
            profile["pearls"] -= vessel["cost"]
            profile["unlocked_vessels"].append(vid)
            profile["active_vessel"] = vid
            profile_mod.save(profile)
            self.audio.big_success()
            self.speech.say(f"Sold. {vessel['name']} is yours and waiting at the dock. "
                            f"{profile['pearls']} pearls remain.")
        self._shipyard_menu()

    # --- chandlery ----------------------------------------------------------------
    def _chandlery_menu(self):
        self.mode = "chandlery"
        profile = self.game.profile
        items = []
        for gid, item in data_loader.gear().items():
            if gid in profile["owned_gear"]:
                items.append(MenuItem(f"{item['name']}, owned", value=("none", gid),
                                      help_text=item["description"], enabled=False))
            else:
                items.append(MenuItem(f"{item['name']}, {item['cost']} pearls",
                                      value=("buy", gid), help_text=item["description"],
                                      enabled=profile["pearls"] >= item["cost"]))
        items.append(MenuItem("Talk to Sefton", value=("talk", None)))
        items.append(MenuItem("Back to the quay", value=("back", None)))
        self.menu = AccessibleMenu(
            f"Sefton's chandlery. Rope, tar, and opinions. Pearls: {profile['pearls']}. "
            "Press H for what each item does.",
            items, self.speech, self.audio)
        self.menu.open()

    def _chandlery_choice(self, choice):
        action, gid = choice
        if action == "back":
            self._main_menu()
            return
        if action == "talk":
            self.menu = None
            if not maybe_play(self.game, "talk_sefton"):
                self.speech.say("Sefton shrugs. \"Stock's what you hear. Sea's what you get.\"")
                self._chandlery_menu()
            return
        if action == "buy":
            profile = self.game.profile
            item = data_loader.gear()[gid]
            profile["pearls"] -= item["cost"]
            profile["owned_gear"].append(gid)
            profile_mod.save(profile)
            self.audio.coin()
            self.speech.say(f"{item['name']} bought and stowed. It works on every tide from "
                            f"now on. {profile['pearls']} pearls remain.")
        self._chandlery_menu()

    # --- chronicle ---------------------------------------------------------------------
    def _chronicle(self):
        p = self.game.profile
        s = p["stats"]
        self.speech.say(
            f"The Chronicle. Tides set out: {p['tides']}. Homecomings: {p['homecomings']}. "
            f"Wrecks: {p['wrecks']}. Races won: {s['races_won']}. "
            f"Slaloms cleared: {s['slaloms_cleared']}. Dives completed: {s['dives_completed']}. "
            f"Storms survived: {s['storms_survived']}. Fish landed: {s['fish_caught']}. "
            f"Souls rescued: {s['rescues']}. Wardens bested: {s['bosses_beaten']}. "
            f"Lifetime salvage: {s['salvage_lifetime']}. "
            f"Almanac pages found: {len(p['almanac'])}. "
            f"Renown {p['renown']}, level {profile_mod.renown_level(p)}.")

    # --- embark -----------------------------------------------------------------------
    def _unlocked_region_ids(self) -> list[str]:
        profile = self.game.profile
        out = []
        for region in data_loader.regions():
            unlock = region.get("unlock", {})
            if "renown_level" in unlock and \
                    profile_mod.renown_level(profile) < unlock["renown_level"]:
                continue
            if "quality" in unlock and not profile_mod.get_quality(profile, unlock["quality"]):
                continue
            out.append(region["id"])
        return out

    def _embark(self):
        from scenes.expedition import ExpeditionScene
        profile = self.game.profile
        regions = self._unlocked_region_ids()
        profile["tides"] += 1
        profile_mod.save(profile)
        run = RunState(profile, self._active_vessel(), regions)
        self.game.run = run
        self.menu = None
        self.mode = "embarking"  # keep on_resume quiet while the embark beat plays
        vessel = data_loader.vessels()[run.vessel_id]["name"]

        def start():
            self.game.scenes.replace(ExpeditionScene(self.game, run))
        self.speech.say(f"Tide {profile['tides']}. You cast off in the {vessel}. "
                        f"{len(regions)} reaches lie open before you.")
        if not maybe_play(self.game, "embark", run=run, on_close=start):
            start()
