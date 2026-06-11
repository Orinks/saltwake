# Saltwake

A watersports roguelite where the sea remembers. Audio-first, screen-reader-first,
built on the Freight Fate stack: Python, Pygame, Prism speech output, and
BASS audio via sound_lib (with automatic pygame.mixer fallback).

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
- **An 18-track procedural soundtrack** (~13 minutes of looped music)
  synthesized entirely from code and data — a title theme, the quay, all
  four regions, every activity, two boss themes, and wreck, homecoming, and
  victory pieces. Tracks render from `data/music.json` on first launch and
  cache as WAVs; `tools/render_soundtrack.py` pre-renders the lot. Music
  sits under the speech and cue layer by design: it sets scenes, never
  carries information.
- **Accessibility is the design**, not a feature: everything is spoken via
  Prism (NVDA, JAWS, SAPI, VoiceOver, Speech Dispatcher, and more), all cues
  carry redundant speech, R repeats, T reads status, H explains, and a visual
  mirror shows the last spoken line for sighted players.

## Download and play

The easiest way to play is a prebuilt portable build from the
[releases page](https://github.com/Orinks/saltwake/releases):

- **Stable releases** (`v0.1.0` and so on) are the finished, numbered
  versions — pick the latest one.
- **Developer snapshots** (`nightly-...`, marked pre-release) are automatic
  nightly builds of work in progress: new features sooner, rough edges
  included.

Download the archive for your platform, extract it anywhere, and run the
game from the extracted `Saltwake` folder — `Saltwake.exe` on Windows,
`Saltwake` on macOS and Linux. There is nothing to install, and the game
is truly portable: saves live in a `saves` folder inside the game folder,
so you can move or copy the whole folder and your progress travels with
it. The game checks for newer releases at the title menu and can
download, install, and restart itself — updates replace only the game's
own files and never touch the `saves` folder. Switch between stable and
snapshot updates in Settings under "Update channel".

## Run from source

You need two tools installed and on your PATH:

- [uv](https://docs.astral.sh/uv/getting-started/installation/) — manages
  Python and all dependencies for you (it downloads a suitable Python
  automatically, so a system Python is not required). The official
  installer puts uv on your PATH for you; close and reopen the terminal
  afterwards so the change takes effect.

  On Windows (PowerShell):

  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

  On macOS or Linux:

  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

- [git](https://git-scm.com/downloads) — required even after cloning,
  because one dependency (`sound_lib`) installs straight from a git
  repository. If `uv sync` fails resolving `sound_lib`, a missing git is
  almost always why.

```bash
git clone https://github.com/Orinks/saltwake.git
cd saltwake
uv sync
uv run python src/main.py
```

On Linux you also need SDL and Speech Dispatcher packages from your
distribution (for example `libsdl2-2.0-0` and `speech-dispatcher` on
Debian/Ubuntu).

Useful flags and environment variables:

- `uv run python src/main.py --self-test` — boot everything headless and exit.
- `uv run python src/main.py --no-speech` — echo speech to the console (development).
- `SALTWAKE_NO_SPEECH=1` — disable speech entirely (CI / tests).
- `SALTWAKE_SPEECH_BACKEND=SAPI` — force a specific Prism backend.
- `SALTWAKE_AUDIO_BACKEND=pygame` — skip BASS and use the pygame.mixer
  audio fallback.
- `SALTWAKE_DATA_DIR=<path>` — override where saves and the music cache
  are written.

Saltwake is portable: saves and the rendered music cache live in the
game's own directory (next to the executable in frozen builds), never in
per-user system folders.

## Build a standalone copy

`tools/build_release.py` produces the same portable build that the
releases page ships, using PyInstaller:

```bash
uv sync --group build
uv run python tools/build_release.py
```

This freezes the game into `dist/Saltwake/`, pre-renders all 18 music
tracks into the bundle so first launch never waits on the composer, boots
the result once as a smoke check, and archives it as
`dist/Saltwake-<version>-windows-portable.zip` (or `-macos.zip` /
`-linux-x64.tar.gz`). Useful flags:

- `--skip-smoke` — skip booting the frozen build.
- `--tag <label>` — override the version label in the archive name, as the
  nightly workflow does.

If the build succeeds but the archive seems to vanish on Windows, check
your antivirus: freshly built unsigned PyInstaller executables are
sometimes quarantined on sight. Add an exclusion for the `dist/` folder or
restore the file from quarantine.

## Controls

- **Arrow keys** — navigate menus; steer, carve, dive, and brace at sea
- **Enter / Space** — select, advance story pages, reel
- **Escape** — back, skip to choices, abandon an activity
- **R** — repeat last speech, **T** — status at sea, **H** — help for the focused item
- **Page Up / Page Down** — speech rate
- **F2** — music on/off, **F3 / F4** — music volume down/up
- First-letter navigation works in every menu
- **How to play** on the title menu opens a paged manual: Left/Right change
  pages, Up/Down read line by line, Enter reads the whole page

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
