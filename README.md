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
- **A novel-scale story** (~24,500 words across 140+ storylets) told the
  Hades way: priority-picked beats keyed to run count, wrecks, deeds, and
  relationships, on a Sunless Sea style quality/storylet engine. Three acts,
  eight character arcs, a finale inside the Glass Squall, and a post-game
  where the whole coast answers the ending. Ties shows where you stand
  with everyone, and Memories keeps every storylet you've heard
  re-readable, grouped by teller.
- **A 50-page Drowned Almanac in five volumes**: marquee pages granted by
  the story, plus a pool of loose pages that wash up from dives, fishing,
  caches, and beacons — the sea posting you a drowned town, page by page.
- **129 story-rooted achievements** from first tide to salt-proof legend,
  in six browsable categories, with hidden marks that never spoil the
  story and spoken unlock announcements.
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
  mirror shows the last spoken line for sighted players. The Chronicle can
  copy your whole record to the clipboard for sharing.

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

On Linux there is also a single-file
`Saltwake-<version>-linux-x86_64.AppImage`: download it, mark it
executable (`chmod +x`), and run it — no extraction, and it works on
non-Debian distributions (every AppImage is boot-tested on Fedora before
release). Saves and the music cache live in a `Saltwake` folder next to
the AppImage when that directory is writable, or under
`~/.local/share/saltwake` otherwise; set `SALTWAKE_DATA_DIR` to choose
your own spot. The in-game updater works here too: it downloads the new
AppImage and swaps the file in place on restart (the folder holding the
AppImage has to be writable; if it isn't, the game tells you where the
downloaded update was saved instead).

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
- `--check-dependencies` — verify the release-critical runtime pieces
  (Prism and BASS native libraries, the game data) without building.
  CI runs this as a release gate before every build.

On Linux, `installer/build_appimage.py` packages the freshly built
`dist/Saltwake/` into the release AppImage (run it after
`tools/build_release.py`). It downloads pinned linuxdeploy and AppImage
runtime tools on first use, keeps host-integration libraries (GLib,
D-Bus, OpenSSL) out of the bundle so the game integrates with whatever
distribution it lands on, and writes
`dist/Saltwake-<version>-linux-x86_64.AppImage`.

If the build succeeds but the archive seems to vanish on Windows, check
your antivirus: freshly built unsigned PyInstaller executables are
sometimes quarantined on sight. Add an exclusion for the `dist/` folder or
restore the file from quarantine.

## How to play

The full player's manual — the loop, every key, all six contests, and the
tips worth knowing — is **[docs/Manual.html](docs/Manual.html)**. It ships
with the game in the `docs` folder next to the executable, so it is there
after you unzip and after any game manager adds Saltwake to its library.

The same manual lives inside the game: **How to play** on the title menu
opens a paged spoken version (Left/Right change pages, Up/Down read line
by line, Enter reads the whole page).

The short version: you are the Tideborn. From Greywater Quay you **embark
on tides** — runs across reaches of open water, each leg offering a
contest, a beacon, drifting salvage, or rough water. Salvage becomes
pearls **in full** when you make it home and **half** if you wreck; a
wreck costs nothing else, and renown, story, almanac pages, and
friendships all survive. Between tides, spend pearls at the quay and talk
to people. Every run moves the story.

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
├── docs/                  # player-facing documentation, shipped with the game
│   └── Manual.html        # the player's manual
└── DESIGN.md              # design notes and the research behind them
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
