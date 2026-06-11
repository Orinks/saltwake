"""Sea states. Rolled per chart row; modifies activity difficulty and risk."""

import random

SEA_STATES = {
    "calm": {
        "name": "calm water",
        "difficulty": 0.85,
        "damage_mult": 0.8,
        "description": "The water lies flat as hammered tin.",
    },
    "chop": {
        "name": "light chop",
        "difficulty": 1.0,
        "damage_mult": 1.0,
        "description": "Short waves slap the hull in an easy rhythm.",
    },
    "swell": {
        "name": "rolling swell",
        "difficulty": 1.15,
        "damage_mult": 1.2,
        "description": "Long hills of water lift and drop the boat.",
    },
    "squall": {
        "name": "squall",
        "difficulty": 1.35,
        "damage_mult": 1.5,
        "description": "Rain comes in sideways and the wind has teeth.",
    },
    "glass": {
        "name": "glass calm",
        "difficulty": 0.75,
        "damage_mult": 1.0,
        "description": "The sea has gone unnaturally still, like held breath.",
    },
}

_WEIGHTS_BY_REGION_TIER = {
    0: [("calm", 40), ("chop", 45), ("swell", 12), ("squall", 2), ("glass", 1)],
    1: [("calm", 22), ("chop", 42), ("swell", 25), ("squall", 9), ("glass", 2)],
    2: [("calm", 10), ("chop", 30), ("swell", 35), ("squall", 22), ("glass", 3)],
    3: [("calm", 5), ("chop", 15), ("swell", 30), ("squall", 35), ("glass", 15)],
}


def roll_sea_state(region_tier: int, rng: random.Random) -> str:
    weights = _WEIGHTS_BY_REGION_TIER.get(min(region_tier, 3), _WEIGHTS_BY_REGION_TIER[1])
    names = [w[0] for w in weights]
    values = [w[1] for w in weights]
    return rng.choices(names, weights=values, k=1)[0]


def describe(state: str) -> str:
    info = SEA_STATES[state]
    return f"{info['name'].capitalize()}. {info['description']}"


def difficulty(state: str) -> float:
    return SEA_STATES[state]["difficulty"]


def damage_mult(state: str) -> float:
    return SEA_STATES[state]["damage_mult"]
