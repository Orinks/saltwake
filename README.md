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

If the build succeeds but the archive seems to vanish on Windows, check
your antivirus: freshly built unsigned PyInstaller executables are
sometimes quarantined on sight. Add an exclusion for the `dist/` folder or
restore the file from quarantine.

## How to play

The full manual also lives in the game: **How to play** on the title menu
opens a paged spoken version of everything below (Left/Right change pages,
Up/Down read line by line, Enter reads the whole page).

### The loop

You are the Tideborn. From Greywater Quay you **embark on tides** — runs
across reaches of open water. Each leg of the sea chart offers two or
three headings: a contest, something on the water, a friendly beacon,
drifting salvage, or rough water. Choose one and commit. At the end of a
reach a warden waits; beat it and you can press deeper or turn for home.
Salvage converts to pearls **in full** when you make it home, **half** if
you wreck — and a wreck costs nothing else. Renown, story, almanac pages,
and friendships all survive. Between tides, spend pearls at the quay and
talk to people; every run moves the story.

### Menus

| Key | Action |
| --- | --- |
| Up / Down | Navigate |
| Enter / Space | Select |
| Escape | Back |
| Home / End | First / last item |
| Any letter | Jump to the next item starting with it |
| H | What the focused item does |
| R | Repeat the last speech |

### At sea

| Key | Action |
| --- | --- |
| Arrow keys | Steer, carve, dive, brace — each contest speaks its rules first |
| Enter / Space | Start a contest; grab; reel |
| T | Status: hull, grit, salvage, position, weather |
| R | Repeat the last speech |
| Escape | Abandon a contest (a failure, never a trap) |
| Page Up / Page Down | Speech rate, anywhere |
| F2, F3 / F4 | Music on/off, volume down/up |

### The six contests

Every contest begins with spoken rules; Enter starts, three rising tones
count you in. Cues are stereo-panned sound with a spoken twin — nothing is
audio-only.

- **Boat race** — gates call from a side: answer left, right, or up for
  dead ahead. Clean gates build speed; beat the pacer across the line.
- **Jet ski slalom** — buoys alternate sides, tempo climbs. Carve with
  left and right; three misses washes you out.
- **Dive salvage** — sonar pings lean toward the cache; lower pitch means
  deeper than you. Down descends, up ascends, left and right swim, Space
  grabs. Surface at depth zero before your breath runs out.
- **Storm crossing** — steer *into* the gusts: gust on the left, press
  right; gust on the right, press left; deep tone dead ahead, brace with
  down. Mistakes cost hull.
- **Fishing** — when the line sings high, reel with Space; when the tone
  drops low, hands off or give line with down. Reel against a run and the
  line snaps.
- **Rescue tow** — answer the whistle's direction three times to come
  alongside, then keep the drifting tow tone centered; brace with down
  when they panic.

Reach wardens are harder, themed versions of these with their own music
and their own opinions.

### Greywater Quay

The Brinehouse tavern (the regulars, whose stories deepen with your
renown, your deeds, and your visits), the harbormaster's office (ledgers
and the main story), the shipyard (vessels, each with its own handling),
the chandlery (permanent gear), the Drowned Almanac (recovered lore, in
five volumes), the Chronicle (your record, copyable to the clipboard with
C), Ties (where you stand with everyone), Memories (re-read any story
you've heard), and Achievements (129 marks, from first tide to legend).

### Tips and tricks

- **Talk to everyone between every tide.** Story beats gate on your run
  count, deeds, and how well people know you — a quiet answer today is a
  new scene after your next homecoming.
- **Vary your contests.** Different people care about different deeds:
  racers notice wins, the kitchen notices fish, the whole coast notices
  rescues. Playing one activity forever leaves stories locked.
- **Grit is the run's fuel.** Contests spend it, exhaustion ends the tide.
  Rest at beacons, and treat a low-grit deep push with suspicion.
- **Carry a spare supply.** Beacons patch three hull for one supply, and
  rough water can be skirted for a supply instead of risking the hull.
- **Check T before committing.** Weather changes leg by leg; a dive in
  glass calm and a dive in a running sea are different propositions.
- **Take the Tiding.** Beacon boons last the whole tide and stack. Listen
  to the water even when you don't need the rest.
- **Escape is always safe.** Abandoning a contest costs the attempt — no
  reward, no shame, never a trap. If the weather turned mid-slalom, living
  to carve tomorrow is a strategy, not a defeat.
- **Buy gear early.** Chandlery gear is permanent and works on every tide;
  the cheap pieces pay for themselves within a run or two, and the compass
  warns you which headings sound ugly.
- **Match the boat to the plan.** Vessels trade hull, grit, and contest
  skills; a salvage tide and a race day want different hulls.
- **Wrecking is progress.** Half the salvage still banks, the story
  reacts, and some things can only be learned by coming back. Don't play
  scared.
- **Bank before you're rich.** Early on, coming home with a modest haul
  beats wrecking with a heavy one — renown and gear compound.
- **Loose Almanac pages ride along.** Once you've met the right person at
  the tavern, pages wash up with dives, fishing hauls, and caches, and
  friendly beacons hold them for you. Collectors dive deep and stop for
  wax on the water.
- **After the credits, keep sailing.** The post-game has its own beats,
  Tide Marks raise the difficulty for richer banking, and the sea still
  has things to say.

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
