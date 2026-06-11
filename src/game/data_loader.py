"""Loads static game data from data/*.json with caching."""

import json
import os
from functools import lru_cache

from core.paths import DATA_DIR


@lru_cache(maxsize=None)
def load_data(name: str) -> dict:
    path = os.path.join(DATA_DIR, f"{name}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def vessels() -> dict:
    return {v["id"]: v for v in load_data("vessels")["vessels"]}


def regions() -> list[dict]:
    return load_data("regions")["regions"]


def region_by_id(region_id: str) -> dict:
    for r in regions():
        if r["id"] == region_id:
            return r
    raise KeyError(region_id)


def boons() -> dict:
    return {b["id"]: b for b in load_data("boons")["boons"]}


def gear() -> dict:
    return {g["id"]: g for g in load_data("gear")["gear"]}
