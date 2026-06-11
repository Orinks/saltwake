# Saltwake

A watersports roguelite where the sea remembers. Audio-first, screen-reader-first,
built on the Freight Fate stack: Python 3.12, Pygame, and Prism speech output.

You are the Tideborn: washed up at Greywater Quay with no memory, a brass key,
and a habit of not drowning. Set out on tides (runs) across reaches of open
water; race boats, carve jet ski slaloms, free-dive wrecks, cross storms, fish,
and haul swimmers out of the chop. Wreck or come home, the story moves: every
run, the people of the quay have more to say, and the Drowned Almanac fills
with pages about who you were before the water took your memory.

## Features

- **Six watersports activities**, all played by ear with arrow keys against
  spoken and stereo-panned sound cues: boat racing, jet ski slalom, dive
  salvage, storm crossings, fishing, and rescue tows.
- **Roguelite structure**: branching sea-chart headings, per-run Tidings
  (boons), permadeath that banks half and never erases story, pearls and
  renown meta-progression, six vessels, permanent gear, and post-victory
  Tide Marks difficulty.
- **A novel-scale story** (~17,500 words across 100+ storylets) told the
  Hades way: priority-picked beats keyed to run count, wrecks, deeds, and
  relationships, on a Sunless Sea style quality/storylet engine. Three acts,
  six NPC arcs, a finale inside the Glass Squall, and post-game epilogues.
- **Accessibility is the design**, not a feature: everything is spoken via
  Prism (NVDA, JAWS, SAPI, VoiceOver, Speech Dispatcher, and more), all cues
  carry redundant speech, R repeats, T reads status, H explains, and a visual
  mirror shows the last spoken line for sighted players.

## Install and run

The project uses [uv](https://docs.astral.sh/uv/) for dependency management:

```bash
uv sync
uv run python src/main.py
```

Useful flags and environment variables:

- `uv run python src/main.py --self-test` — boot everything headless and exit.
- `uv run python src/main.py --no-speech` — echo speech to the console (development).
- `SALTWAKE_NO_SPEECH=1` — disable speech entirely (CI / tests).
- `SALTWAKE_SPEECH_BACKEND=SAPI` — force a specific Prism backend.

## Controls

- **Arrow keys** — navigate menus; steer, carve, dive, and brace at sea
- **Enter / Space** — select, advance story pages, reel
- **Escape** — back, skip to choices, abandon an activity
- **R** — repeat last speech, **T** — status at sea, **H** — help for the focused item
- **Page Up / Page Down** — speech rate
- First-letter navigation works in every menu

## Project structure

```
saltwake/
├── src/
│   ├── main.py            # entry point, game loop, self-test
│   ├── core/              # speech (Prism), synthesized audio, menus, scenes, saves
│   ├── story/             # storylet engine, requirement DSL, effects
│   ├── game/              # profile, runs, chart, weather, boons, vessels
│   │   └── activities/    # the six watersports minigames + bosses
│   └── scenes/            # harbor hub, expedition, storylets, endings
├── data/                  # vessels, regions, boons, gear
│   └── story/             # the story corpus (JSON storylets + almanac pages)
├── tests/                 # pytest suite incl. content integrity checks
└── docs/DESIGN.md         # design notes and the research behind them
```

## Tests

```bash
uv run pytest
```

The suite covers the storylet engine, chart generation, run systems, effects,
and integrity of the story corpus (every `goto` resolves, every almanac page
is obtainable, the main arc is reachable end to end).

## License

MIT
