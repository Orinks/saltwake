"""Sea chart generation.

Each region is a sequence of rows; each row offers two or three headings
(like FTL beacons / Slay the Spire columns). The final row is always the
region's boss encounter. Node mix is weighted per region so deeper waters
skew toward danger.
"""

import random

NODE_TYPES = ("activity", "event", "beacon", "cache", "hazard")

ACTIVITY_KINDS = ("boat_race", "jetski_slalom", "dive_salvage",
                  "storm_run", "fishing", "rescue_tow")

_NODE_SPOKEN = {
    "activity": "a contest",
    "event": "something on the water",
    "beacon": "a friendly beacon",
    "cache": "drifting salvage",
    "hazard": "rough water",
    "boss": "the reach warden",
}

_ACTIVITY_SPOKEN = {
    "boat_race": "a boat race",
    "jetski_slalom": "a jet ski slalom",
    "dive_salvage": "a dive site",
    "storm_run": "a storm crossing",
    "fishing": "good fishing water",
    "rescue_tow": "a distress call",
}


def spoken_name(node: dict) -> str:
    if node["type"] == "activity":
        return _ACTIVITY_SPOKEN.get(node["kind"], "a contest")
    return _NODE_SPOKEN.get(node["type"], "open water")


def generate_region_chart(region: dict, rng: random.Random,
                          unlocked_activities=None) -> list[list[dict]]:
    rows = []
    n_rows = region.get("rows", 5)
    weights = region.get("node_weights",
                         {"activity": 50, "event": 22, "beacon": 10,
                          "cache": 10, "hazard": 8})
    activity_pool = list(region.get("activities", ACTIVITY_KINDS))
    if unlocked_activities is not None:
        activity_pool = [a for a in activity_pool if a in unlocked_activities] or activity_pool

    for row_i in range(n_rows):
        width = rng.choice((2, 3, 3))
        row = []
        types_in_row: set[str] = set()
        for _ in range(width):
            node = _roll_node(weights, activity_pool, rng, exclude=types_in_row)
            types_in_row.add(node["type"])
            row.append(node)
        # Guarantee a beacon choice midway so runs have a breath point.
        if row_i == n_rows // 2 and not any(n["type"] == "beacon" for n in row):
            row[rng.randrange(len(row))] = {"type": "beacon"}
        rows.append(row)

    rows.append([{"type": "boss", "kind": region.get("boss", "regatta_champion")}])
    return rows


def _roll_node(weights: dict, activity_pool: list, rng: random.Random,
               exclude: set) -> dict:
    names = list(weights.keys())
    values = list(weights.values())
    for _ in range(6):
        node_type = rng.choices(names, weights=values, k=1)[0]
        if node_type not in exclude or len(exclude) >= len(names):
            break
    if node_type == "activity":
        return {"type": "activity", "kind": rng.choice(activity_pool)}
    return {"type": node_type}
