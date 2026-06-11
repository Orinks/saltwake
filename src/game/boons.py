"""Tidings: per-run boons granted by the sea.

Build variety is the roguelite engine of replayability — Tidings stack and
synergize with vessel bonuses and gear so each run plays differently.
They vanish when the run ends.
"""

import random

from game import data_loader


def grant_random(run, rng: random.Random, rarity_bias: float = 0.0,
                 count: int = 3) -> list[dict]:
    """Returns up to `count` Tidings the player may choose between."""
    all_boons = data_loader.boons()
    held = {b["id"] for b in run.boons}
    pool = [b for b in all_boons.values() if b["id"] not in held]
    if not pool:
        return []
    rarity_weight = {"common": 60, "rare": 30, "deep": 10}
    weights = []
    for b in pool:
        w = rarity_weight.get(b.get("rarity", "common"), 40)
        if b.get("rarity") == "deep":
            w += int(rarity_bias * 30)
        weights.append(w)
    picks = []
    pool = pool[:]
    for _ in range(min(count, len(pool))):
        choice = rng.choices(pool, weights=weights, k=1)[0]
        idx = pool.index(choice)
        pool.pop(idx)
        weights.pop(idx)
        picks.append(choice)
    return picks


def total_modifier(run, key: str) -> float:
    """Sums a numeric modifier across held Tidings, gear, and vessel bonuses."""
    total = 0.0
    for b in run.boons:
        total += b.get("modifiers", {}).get(key, 0.0)
    for g in run.gear:
        total += g.get("modifiers", {}).get(key, 0.0)
    total += run.vessel.get("modifiers", {}).get(key, 0.0)
    return total


def has_tag(run, tag: str) -> bool:
    """Checks one-shot ability tags like 'reroll_fail' or 'free_miss'."""
    for b in run.boons:
        if tag in b.get("tags", []):
            return True
    for g in run.gear:
        if tag in g.get("tags", []):
            return True
    return False


def consume_tag(run, tag: str) -> bool:
    """Uses up a one-shot tag if held. Returns True if consumed."""
    for b in run.boons:
        if tag in b.get("tags", []):
            b["tags"] = [t for t in b["tags"] if t != tag]
            return True
    for g in run.gear:
        if tag in g.get("tags", []):
            g["tags"] = [t for t in g["tags"] if t != tag]
            return True
    return False
