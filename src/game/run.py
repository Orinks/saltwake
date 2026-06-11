"""State for a single tide (one roguelite run)."""

import copy
import random
import time

from game import data_loader
from game.chart import generate_region_chart
from game.weather import roll_sea_state


class RunState:
    def __init__(self, profile: dict, vessel_id: str, region_ids: list[str],
                 seed: int | None = None):
        self.seed = seed if seed is not None else int(time.time() * 1000) % (2 ** 31)
        self.rng = random.Random(self.seed)

        vessels = data_loader.vessels()
        self.vessel_id = vessel_id
        self.vessel = copy.deepcopy(vessels[vessel_id])

        gear_data = data_loader.gear()
        self.gear = [copy.deepcopy(gear_data[g]) for g in profile.get("owned_gear", [])
                     if g in gear_data]

        tide_marks = profile.get("tide_marks", 0)
        self.tide_marks = tide_marks
        hull_bonus = sum(g.get("modifiers", {}).get("hull_max", 0) for g in self.gear)
        grit_bonus = sum(g.get("modifiers", {}).get("grit_max", 0) for g in self.gear)
        self.hull_max = self.vessel["hull"] + int(hull_bonus)
        self.hull = self.hull_max
        self.grit_max = self.vessel.get("grit", 10) + int(grit_bonus)
        self.grit = self.grit_max
        self.supplies = 3
        self.salvage = 0
        self.renown_earned = 0
        self.boons: list[dict] = []

        self.region_ids = region_ids
        self.region_index = 0
        self.row_index = 0
        self.chart: list[list[dict]] = []
        self.sea_state = "chop"
        self.log: list[str] = []
        self.over = False
        self.outcome = None  # "wreck" | "homecoming" | "victory"
        self._enter_region()

    # --- Region / chart -----------------------------------------------------
    @property
    def region(self) -> dict:
        return data_loader.region_by_id(self.region_ids[self.region_index])

    def _enter_region(self) -> None:
        region = self.region
        self.chart = generate_region_chart(region, self.rng)
        self.row_index = 0
        self.roll_weather()
        self.log.append(f"Entered {region['name']}.")

    def roll_weather(self) -> None:
        self.sea_state = roll_sea_state(self.region.get("tier", 0), self.rng)

    def current_row(self) -> list[dict]:
        return self.chart[self.row_index]

    def is_last_row(self) -> bool:
        return self.row_index >= len(self.chart) - 1

    def advance_row(self) -> None:
        self.row_index += 1
        self.roll_weather()

    def advance_region(self) -> bool:
        """Move to the next region. Returns False if there are no more."""
        if self.region_index + 1 >= len(self.region_ids):
            return False
        self.region_index += 1
        self._enter_region()
        return True

    # --- Resources ------------------------------------------------------------
    def difficulty(self) -> float:
        base = self.region.get("difficulty", 1.0)
        return base * (1.0 + 0.08 * self.tide_marks)

    def take_damage(self, amount: int) -> int:
        amount = max(0, amount)
        self.hull = max(0, self.hull - amount)
        if self.hull == 0:
            self.over = True
            self.outcome = "wreck"
        return amount

    def repair(self, amount: int) -> None:
        self.hull = min(self.hull_max, self.hull + amount)

    def spend_grit(self, amount: int) -> None:
        self.grit = max(0, self.grit - amount)

    def rest(self) -> None:
        self.grit = min(self.grit_max, self.grit + max(2, self.grit_max // 2))

    def add_salvage(self, amount: int) -> None:
        bonus = 1.0
        for b in self.boons:
            bonus += b.get("modifiers", {}).get("salvage_gain", 0.0)
        for g in self.gear:
            bonus += g.get("modifiers", {}).get("salvage_gain", 0.0)
        self.salvage += max(0, int(round(amount * bonus)))

    # --- Speech helpers ---------------------------------------------------------
    def status_text(self) -> str:
        region = self.region
        return (f"Hull {self.hull} of {self.hull_max}. Grit {self.grit} of {self.grit_max}. "
                f"Salvage {self.salvage}. Supplies {self.supplies}. "
                f"{region['name']}, leg {self.row_index + 1} of {len(self.chart)}.")
