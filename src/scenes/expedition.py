"""The expedition: navigating a tide, row by row, out into deeper water."""

import pygame

from core.menu import AccessibleMenu, MenuItem, BACK
from core.scenes import Scene
from game import boons as boons_mod
from game import profile as profile_mod
from game.activities import get_activity_class
from game.activities.boss import get_boss
from game.chart import spoken_name
from game.weather import describe as describe_weather
from scenes.storylet_scene import maybe_play
from scenes import run_end

GENERIC_EVENTS = [
    ("A raft of flotsam knocks along the hull. You fish out the best of it.", {"salvage": 3}),
    ("A cooler bobs past, lid taped shut, contents miraculously dry.", {"supplies": 1}),
    ("Gulls escort you for a while, screaming opinions, taking nothing.", {}),
    ("Something big passes underneath, unhurried. The water stays polite.", {}),
    ("A snagged crab line fouls the prop before you cut it free.", {"hull": -1}),
    ("An old marker buoy clangs its bell once as you pass, though there is no wind.", {}),
]


class ExpeditionScene(Scene):
    def __init__(self, game, run):
        super().__init__(game)
        self.run = run
        self.menu = None
        self.mode = "row"
        self._announced_region = -1

    # --- helpers -------------------------------------------------------------
    def _scout_level(self) -> int:
        return int(boons_mod.total_modifier(self.run, "scout"))

    def _node_label(self, node: dict) -> str:
        name = spoken_name(node)
        if self._scout_level() > 0 and node["type"] == "hazard":
            name += ", and it sounds ugly"
        return name

    def _award(self, renown: int, stat: str | None):
        if renown:
            bonus = int(boons_mod.total_modifier(self.run, "renown_gain"))
            self.run.renown_earned += renown + bonus
        if stat:
            stats = self.game.profile["stats"]
            stats[stat] = stats.get(stat, 0) + 1

    # --- entry / row presentation ---------------------------------------------
    def on_enter(self):
        if self.run.over:
            return
        if self.mode != "row":
            return
        parts = []
        if self._announced_region != self.run.region_index:
            self._announced_region = self.run.region_index
            region = self.run.region
            parts.append(f"{region['name']}. {region['description']}")
        parts.append(describe_weather(self.run.sea_state))
        # Queue: the cast-off announcement or embark beat may still be talking.
        self.speech.say(" ".join(parts), interrupt=False)
        self._present_row()

    def _present_row(self):
        self.mode = "row"
        from core.music import REGION_TRACKS
        self.game.music.play(REGION_TRACKS.get(self.run.region["id"]))
        row = self.run.current_row()
        if row[0]["type"] == "boss":
            self._begin_boss(row[0])
            return
        items = [MenuItem(self._node_label(node), value=i,
                          help_text="T for status, R to repeat. Pick a heading and commit.")
                 for i, node in enumerate(row)]
        self.menu = AccessibleMenu(
            f"Leg {self.run.row_index + 1} of {len(self.run.chart)}. Choose a heading.",
            items, self.speech, self.audio, escapable=False)
        # Callers always speak first (region, weather, event outcomes).
        self.menu.open(interrupt=False)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_t:
            self.speech.say(self.run.status_text())
            return
        if self.menu is not None:
            result = self.menu.handle_event(event)
            if result is None or result is BACK:
                return
            if self.mode == "row":
                self.menu = None
                self._resolve_node(self.run.current_row()[result])
            elif self.mode == "beacon":
                self._beacon_choice(result)
            elif self.mode == "tiding":
                self._tiding_choice(result)
            elif self.mode == "hazard":
                self._hazard_choice(result)
            elif self.mode == "region_end":
                self.menu = None
                if result == "press_on":
                    self.run.advance_region()
                    # on_enter no-ops unless the scene is in row mode.
                    self.mode = "row"
                    self.on_enter()
                else:
                    self._end_run("homecoming")

    # --- node resolution ---------------------------------------------------------
    def _resolve_node(self, node: dict):
        kind = node["type"]
        if kind == "activity":
            scene_cls = get_activity_class(node["kind"])
            self.game.scenes.push(scene_cls(self.game, self.run, self._activity_done))
        elif kind == "event":
            if not maybe_play(self.game, "sea_event", run=self.run,
                              on_close=self._after_node):
                self._generic_event()
        elif kind == "beacon":
            self._begin_beacon()
        elif kind == "cache":
            self._open_cache()
        elif kind == "hazard":
            self._begin_hazard()

    # Chance of a loose Almanac page riding along with a successful haul.
    PAGE_CHANCES = {"dives_completed": 0.35, "fish_caught": 0.2}

    def _maybe_loose_page(self, chance: float):
        """Loose pages surface once Nereus has taught you to notice them."""
        if not profile_mod.get_quality(self.game.profile, "met_nereus"):
            return
        if self.run.rng.random() >= chance:
            return
        from game import almanac
        page = almanac.draw_loose(self.game.profile, self.run.rng)
        if page is not None:
            self.audio.coin()
            self.speech.queue("And something else, wax-sealed and bone dry: "
                              f"a page for the Drowned Almanac. {page['title']}.")

    def _maybe_keepsake(self) -> bool:
        """Rarely, a dive brings up something personal. The sea files
        things behind the wreck; sometimes they are somebody's."""
        if self.run.rng.random() >= 0.12:
            return False
        from game import keepsakes
        keepsake = keepsakes.draw(self.game.profile, self.run.rng)
        if keepsake is None:
            return False
        self.audio.big_success()
        self.speech.queue(f"And behind the wreck, where the sea files things: "
                          f"{keepsake['name']}. {keepsake['hint']} "
                          "It rides home in your sea chest.")
        return True

    def _activity_done(self, result):
        from game import achievements
        self._award(result.renown, result.stat)
        self.run.log.append(result.headline)
        if result.success:
            # A personal find preempts the post: one discovery per haul.
            if not (result.stat == "dives_completed" and self._maybe_keepsake()):
                self._maybe_loose_page(self.PAGE_CHANCES.get(result.stat, 0.0))
        achievements.announce(self.game)
        self._after_node()

    def _generic_event(self):
        text, effects = self.run.rng.choice(GENERIC_EVENTS)
        from story.effects import apply_effects
        msgs = apply_effects(effects, self.game.profile, self.run)
        self.speech.say(" ".join([text] + msgs))
        self._after_node()

    def _open_cache(self):
        amount = self.run.rng.randint(3, 7) + int(self.run.difficulty() * 2)
        self.run.add_salvage(amount)
        self.audio.coin()
        self.speech.say(f"A drifting cache, lashed to a pallet and half sunk. "
                        f"You winch it aboard. {amount} salvage.")
        self._maybe_loose_page(0.15)
        self._after_node()

    # --- beacon -----------------------------------------------------------------
    def _begin_beacon(self, interrupt: bool = True):
        self.mode = "beacon"
        items = [
            MenuItem("Rest a while", "rest", "Recover grit."),
            MenuItem("Patch the hull", "patch",
                     "Spend one supply to repair three hull."),
            MenuItem("Listen to the water", "tiding",
                     "The sea offers a Tiding: a boon for the rest of this tide."),
            MenuItem("Push off", "leave", "Back to open water."),
        ]
        self.menu = AccessibleMenu("A friendly beacon. Lamplit, sheltered, briefly safe.",
                                   items, self.speech, self.audio, escapable=False)
        self.menu.open(interrupt=interrupt)

    def _beacon_choice(self, choice):
        if choice == "rest":
            self.run.rest()
            self.speech.say(f"You sleep without dreaming. Grit restored to {self.run.grit}.")
        elif choice == "patch":
            if self.run.supplies >= 1:
                self.run.supplies -= 1
                self.run.repair(3)
                self.speech.say(f"Tar, canvas, and an hour of swearing. Hull at {self.run.hull}.")
            else:
                self.speech.say("No supplies left to patch with.")
                return
        elif choice == "tiding":
            self._begin_tiding()
            return
        elif choice == "leave":
            self.menu = None
            if maybe_play(self.game, "beacon", run=self.run, on_close=self._after_node):
                return
            self._after_node()
            return
        self.menu.speak_current(interrupt=False)

    def _begin_tiding(self):
        offers = boons_mod.grant_random(self.run, self.run.rng,
                                        rarity_bias=self.run.region.get("tier", 0) / 3)
        if not offers:
            self.speech.say("The water has nothing more to offer this tide.")
            self._begin_beacon(interrupt=False)
            return
        self.mode = "tiding"
        self._offers = offers
        items = [MenuItem(f"{b['name']}, {b['rarity']}", value=i, help_text=b["description"])
                 for i, b in enumerate(offers)]
        items.append(MenuItem("Take nothing", value="none",
                              help_text="Some gifts are loans. Decline politely."))
        self.menu = AccessibleMenu("The water speaks. Choose a Tiding. Press H to hear what each does.",
                                   items, self.speech, self.audio, escapable=False)
        self.menu.open()

    def _tiding_choice(self, choice):
        self.menu = None
        if choice != "none":
            boon = self._offers[choice]
            self.run.boons.append(boon)
            hull_bonus = boon.get("modifiers", {}).get("hull_bonus", 0)
            if hull_bonus:
                self.run.hull_max += int(hull_bonus)
                self.run.hull += int(hull_bonus)
            self.audio.big_success()
            self.speech.say(f"{boon['name']}. {boon['description']}")
        else:
            self.speech.say("You let the offer sink. Somewhere below, something shrugs.")
        self._begin_beacon(interrupt=False)

    # --- hazard -------------------------------------------------------------------
    def _begin_hazard(self):
        self.mode = "hazard"
        items = [
            MenuItem("Punch through", "through",
                     "Fastest way is straight. Risks hull, storm skill helps."),
            MenuItem("Go the long way around", "around",
                     "Costs one supply, or two grit if the lockers are empty."),
        ]
        if boons_mod.has_tag(self.run, "escape_squall"):
            items.insert(0, MenuItem("Fire the flare kit", "flare",
                                     "Burn the kit. A patrol launch guides you through untouched."))
        self.menu = AccessibleMenu("Rough water dead ahead, a squall chewing the swell to rags.",
                                   items, self.speech, self.audio, escapable=False)
        self.menu.open()

    def _hazard_choice(self, choice):
        self.menu = None
        rng = self.run.rng
        if choice == "flare":
            boons_mod.consume_tag(self.run, "escape_squall")
            self.speech.say("The flare climbs, dyes the rain red, and a patrol launch "
                            "appears to walk you through the worst of it. The kit is spent.")
        elif choice == "through":
            skill = boons_mod.total_modifier(self.run, "storm_skill")
            roll = rng.random() + skill
            if roll > 0.55:
                self.speech.say("You read the gaps and thread them. The squall spits you "
                                "out the far side, soaked and untouched.")
            else:
                from game.weather import damage_mult
                damage = max(1, int(round(rng.randint(2, 3) * damage_mult(self.run.sea_state))))
                damage = max(0, damage - int(boons_mod.total_modifier(self.run, "damage_soak")))
                self.run.take_damage(damage)
                self.audio.damage()
                self.speech.say(f"The squall lands one good hit. {damage} hull damage. "
                                f"Hull at {self.run.hull}.")
        elif choice == "around":
            if self.run.supplies >= 1:
                self.run.supplies -= 1
                self.speech.say("The long way costs an afternoon and a supply crate, "
                                "and not one drop of blood.")
            else:
                self.run.spend_grit(2)
                self.speech.say("The long way, on an empty stomach. Two grit spent.")
        self._after_node()

    # --- boss ------------------------------------------------------------------------
    def _begin_boss(self, node: dict):
        boss = get_boss(node["kind"])
        self._boss = boss
        self._boss_kind = node["kind"]

        def start_fight():
            scene_cls = boss["scene"]
            scene = scene_cls(self.game, self.run, self._boss_done,
                              difficulty_mult=boss["mult"], title=boss["title"])
            scene.music_track = boss.get("music")
            self.game.scenes.push(scene)
        if not maybe_play(self.game, f"boss_{node['kind']}", run=self.run,
                          on_close=start_fight):
            self.speech.say(f"The end of the reach. {boss['title']} stands between you "
                            "and deeper water.")
            start_fight()

    def _boss_done(self, result):
        boss = self._boss
        if self.run.over:
            self._end_run("wreck")
            return
        if result.success:
            profile_mod.set_quality(self.game.profile, boss["quality"], 1)
            self.game.profile["stats"]["bosses_beaten"] += 1
            self._award(boss["renown"], result.stat)
            self.run.add_salvage(boss["salvage"])
            self.game.profile["deepest_region"] = max(
                self.game.profile.get("deepest_region", 0), self.run.region_index + 1)
            if self._boss_kind == "the_undertow":
                self._end_run("victory")
                return
            self._region_end_menu()
        else:
            self._award(result.renown, result.stat)
            self.speech.say("The reach holds. There is no shame in turning for home with "
                            "what you carry.")
            self._end_run("homecoming")

    def _region_end_menu(self):
        next_exists = self.run.region_index + 1 < len(self.run.region_ids)
        if not next_exists:
            self._end_run("homecoming")
            return
        self.mode = "region_end"
        from game import data_loader
        next_region = data_loader.region_by_id(
            self.run.region_ids[self.run.region_index + 1])
        items = [
            MenuItem(f"Press on into {next_region['name']}", "press_on",
                     "Deeper water, richer salvage, and the story waits out there."),
            MenuItem("Turn for home and bank it all", "home",
                     "Every point of salvage converts to pearls. A wreck only banks half."),
        ]
        self.menu = AccessibleMenu(
            f"The reach is yours. Salvage aboard: {self.run.salvage}. "
            f"Hull {self.run.hull} of {self.run.hull_max}.",
            items, self.speech, self.audio, escapable=False)
        self.menu.open(interrupt=False)

    # --- transitions --------------------------------------------------------------------
    def _after_node(self):
        if self.run.over:
            self._end_run("wreck")
            return
        if self.run.grit <= 0:
            self.speech.queue("Your arms are gone and the horizon will not argue. "
                              "Exhaustion makes the choice for you.")
            self._end_run("homecoming", exhausted=True)
            return
        self.run.advance_row()
        # Queue behind the node's outcome text instead of cutting it off.
        self.speech.queue(describe_weather(self.run.sea_state))
        self._present_row()

    def _end_run(self, outcome: str, exhausted: bool = False):
        self.run.over = True
        self.run.outcome = outcome
        self.game.scenes.replace(run_end.RunEndScene(self.game, self.run,
                                                     exhausted=exhausted))
