"""Applies storylet effects to the profile and (optionally) the active run.

Returns plain-language messages so scenes can speak what just happened.
"""

from game import profile as profile_mod


def apply_effects(effects: dict, profile: dict, run=None) -> list[str]:
    messages: list[str] = []
    if not effects:
        return messages

    for name, value in effects.get("set", {}).items():
        profile_mod.set_quality(profile, name, value)
    for name, delta in effects.get("add", {}).items():
        profile_mod.add_quality(profile, name, delta)
        if name.startswith("affinity_"):
            who = name.replace("affinity_", "").title()
            if delta > 0:
                messages.append(f"{who} thinks a little better of you.")

    if "pearls" in effects:
        profile["pearls"] = max(0, profile["pearls"] + effects["pearls"])
        amount = effects["pearls"]
        messages.append(f"You {'gain' if amount >= 0 else 'lose'} {abs(amount)} pearls.")
    if "renown" in effects:
        profile["renown"] += effects["renown"]
        messages.append(f"Renown increases by {effects['renown']}.")
    if "almanac" in effects:
        page = effects["almanac"]
        if page not in profile["almanac"]:
            profile["almanac"].append(page)
            messages.append("A page for the Drowned Almanac. It is added to your collection.")
    if "unlock_vessel" in effects:
        vid = effects["unlock_vessel"]
        if vid not in profile["unlocked_vessels"]:
            profile["unlocked_vessels"].append(vid)
            messages.append("A new vessel is available at the shipyard.")
    if "unlock_region" in effects:
        rid = effects["unlock_region"]
        if rid not in profile["unlocked_regions"]:
            profile["unlocked_regions"].append(rid)
            messages.append("New waters are open to you.")

    if run is not None:
        if "salvage" in effects:
            run.salvage = max(0, run.salvage + effects["salvage"])
            amount = effects["salvage"]
            messages.append(f"You {'gain' if amount >= 0 else 'lose'} {abs(amount)} salvage.")
        if "hull" in effects:
            run.hull = max(0, min(run.hull_max, run.hull + effects["hull"]))
            if effects["hull"] < 0:
                messages.append(f"Your hull takes {abs(effects['hull'])} damage.")
            else:
                messages.append(f"Your hull is patched by {effects['hull']}.")
        if "grit" in effects:
            run.grit = max(0, min(run.grit_max, run.grit + effects["grit"]))
        if "supplies" in effects:
            run.supplies = max(0, run.supplies + effects["supplies"])
            amount = effects["supplies"]
            messages.append(f"You {'gain' if amount >= 0 else 'spend'} {abs(amount)} supplies.")

    return messages
