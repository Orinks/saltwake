"""Quality-based storylet engine.

The narrative model follows the approach proven by Sunless Sea (storylets
gated on qualities) and Hades (priority-picked, once-only beats keyed to run
count, deaths, and relationships, so the story deepens with every run).

A storylet is a unit of story defined in data/story/*.json:

    {
      "id": "odessa_03",
      "arc": "odessa",
      "where": "tavern",            # hook point: tavern, dock, sea_event,
                                     #   wreck, embark, shipyard, lighthouse...
      "priority": 10,               # higher wins; ties resolved by weight
      "weight": 1,                  # random weight among equal priority
      "once": true,                 # never repeats after being seen
      "requires": [ ...requirements... ],
      "title": "Spoken headline",
      "speaker": "Odessa",
      "pages": ["paragraph", "paragraph", ...],
      "effects": { ...applied when viewed... },
      "choices": [
        {"label": "...", "requires": [...],
         "effects": {...}, "response": ["..."], "goto": "next_id"}
      ]
    }

Requirements (all must hold; nest "any"/"all" for boolean logic):
    {"q": "runs", "gte": 3}      quality comparisons: eq ne gt gte lt lte
    {"seen": "id"}               storylet already seen
    {"not_seen": "id"}           storylet not yet seen

Effects:
    {"set": {"name": 2}, "add": {"affinity_odessa": 1},
     "pearls": 5, "salvage": -2, "hull": -1, "grit": -1, "supplies": 1,
     "unlock_vessel": "id", "unlock_region": "id", "almanac": "page_id",
     "almanac_loose": 1, "renown": 1,
     "keepsake": "id", "deliver_keepsake": "id"}
"""

import json
import os
import random
from typing import Optional

from core.paths import STORY_DIR

_COMPARATORS = {
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
}


class Storylet:
    def __init__(self, raw: dict, source: str = ""):
        self.id = raw["id"]
        self.arc = raw.get("arc", "misc")
        self.where = raw.get("where", "tavern")
        self.priority = raw.get("priority", 0)
        self.weight = raw.get("weight", 1)
        self.once = raw.get("once", True)
        self.requires = raw.get("requires", [])
        self.title = raw.get("title", "")
        self.speaker = raw.get("speaker", "")
        self.pages = raw.get("pages", [])
        self.effects = raw.get("effects", {})
        self.choices = raw.get("choices", [])
        self.source = source


def _check_requirement(req: dict, ctx: dict, seen: dict) -> bool:
    if "any" in req:
        return any(_check_requirement(r, ctx, seen) for r in req["any"])
    if "all" in req:
        return all(_check_requirement(r, ctx, seen) for r in req["all"])
    if "seen" in req:
        return seen.get(req["seen"], 0) > 0
    if "not_seen" in req:
        return seen.get(req["not_seen"], 0) == 0
    if "q" in req:
        value = ctx.get(req["q"], 0)
        for op, fn in _COMPARATORS.items():
            if op in req:
                if not fn(value, req[op]):
                    return False
        return True
    return True


def check_requirements(requires: list, ctx: dict, seen: dict) -> bool:
    return all(_check_requirement(r, ctx, seen) for r in requires)


class StoryEngine:
    def __init__(self, story_dir: str = STORY_DIR, rng: Optional[random.Random] = None):
        self.storylets: dict[str, Storylet] = {}
        self.rng = rng or random.Random()
        self.load_dir(story_dir)

    def load_dir(self, story_dir: str) -> None:
        if not os.path.isdir(story_dir):
            return
        for name in sorted(os.listdir(story_dir)):
            if not name.endswith(".json"):
                continue
            path = os.path.join(story_dir, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError) as exc:
                print(f"Story: skipping {name} ({exc})")
                continue
            entries = data.get("storylets", data if isinstance(data, list) else [])
            for raw in entries:
                if "id" not in raw:
                    continue
                if raw["id"] in self.storylets:
                    print(f"Story: duplicate storylet id {raw['id']} in {name}")
                self.storylets[raw["id"]] = Storylet(raw, source=name)

    def get(self, storylet_id: str) -> Optional[Storylet]:
        return self.storylets.get(storylet_id)

    def eligible(self, where: str, ctx: dict, seen: dict) -> list[Storylet]:
        out = []
        for s in self.storylets.values():
            if s.where != where:
                continue
            if s.once and seen.get(s.id, 0) > 0:
                continue
            if not check_requirements(s.requires, ctx, seen):
                continue
            out.append(s)
        return out

    def pick(self, where: str, ctx: dict, seen: dict) -> Optional[Storylet]:
        """Highest priority wins; ties broken by weighted random choice."""
        pool = self.eligible(where, ctx, seen)
        if not pool:
            return None
        top = max(s.priority for s in pool)
        finalists = [s for s in pool if s.priority == top]
        weights = [max(1, s.weight) for s in finalists]
        return self.rng.choices(finalists, weights=weights, k=1)[0]

    def available_choices(self, storylet: Storylet, ctx: dict, seen: dict) -> list[dict]:
        return [c for c in storylet.choices
                if check_requirements(c.get("requires", []), ctx, seen)]

    def count_by_arc(self) -> dict[str, int]:
        arcs: dict[str, int] = {}
        for s in self.storylets.values():
            arcs[s.arc] = arcs.get(s.arc, 0) + 1
        return arcs
