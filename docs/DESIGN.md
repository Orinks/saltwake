# Saltwake design notes

## What we borrowed, and from where

Saltwake's design deliberately incorporates the practices that make the best
roguelites and nautical narrative games work:

### From Hades (Supergiant)
- **Death is narrative, not punishment.** A wreck banks half your salvage,
  advances the `sea_debt` arc, and triggers a wreck storylet — the town
  reacting to you washing in again. The first ~10 wrecks each have bespoke
  beats; close relationships add NPC reactions on the beach.
- **Every run advances something.** Pearls, renown, qualities, almanac pages,
  and relationship beats all persist. There is no "wasted" run.
- **Priority-picked incremental dialogue.** The story engine picks the
  highest-priority unseen storylet whose requirements hold, so the most
  load-bearing beat always fires first and ambient lines fill the gaps.
- **Post-victory difficulty (Heat → Tide Marks)** with paired reward bonuses.

### From Sunless Sea / Failbetter's quality-based narrative
- **Storylets gated on qualities.** All story state is integer qualities
  (flags, affinities, counters) checked by a small requirement DSL
  (`gte/lte/eq`, `seen/not_seen`, `any/all`). Content is pure data in
  `data/story/*.json` — writers never touch engine code.
- **A nautical mystery told in prose**, discovered out of order through
  found documents (the Drowned Almanac) and port conversations.
- **The hub-and-expedition rhythm**: port for story and outfitting, sea for
  risk; returning home to bank is itself a strategic choice.

### From FTL / Slay the Spire
- **Branching node choices**: each chart row offers 2–3 headings (contest,
  story event, beacon, cache, hazard), with a guaranteed mid-region beacon
  as a breath point and a boss at every region's end.
- **Risk/reward forks**: push through a squall vs. pay supplies to detour;
  press deeper after a boss vs. turn home and bank everything.

### From audio games (Top Speed, Sequence Storm, A Hero's Call)
- **Stereo pan carries position, pitch carries depth/tension**, and every
  audio cue has a spoken twin so no information is audio-only.
- **Universal keys** (R repeat, T status, H help), first-letter menu
  navigation, pause-anywhere, and abandon-anywhere (never a softlock).
- **Synthesized cues** (numpy, streamed through BASS via sound_lib with a
  pygame.mixer fallback — Freight Fate's audio engine architecture) — no
  assets needed, and cue timbres stay consistent across activities. On the
  BASS path, pan and volume are channel attributes rather than baked into
  samples, so one cached mono buffer serves every position. With no audio
  device, BASS's no-sound device keeps the full pipeline running headless.
- **Speech through the player's own screen reader** via Prism, exactly as
  Freight Fate does: runtime-validated backend choice with priority
  fallback, env-var override, and silent-safe failure.

## The story architecture

Three acts, ~17,500 words, 106 storylets in 9 arcs:

1. **Act 1 — The Tideborn.** Arrival, the loop established, the Almanac
   project with Nereus. Gate: clear the Shallows + 2 almanac pages →
   the handwriting reveal → the lighthouse opens.
2. **Act 2 — The Lantern Jane.** The Pale Ferry (Chop boss) names the ship;
   Odessa's recognition; the Leviathan's trench (Wreckwater boss) locates
   her; the whole quay raises her. Gate: `jane_raised` → Act 3 + the
   Glass Squall region + the Lantern Jane as a playable vessel.
3. **Act 3 — The Thirty-Second Soul.** Messages entrusted by the quay,
   the crossing, the Undertow, and Liss. Victory leads to a choice of
   framing, then post-game epilogue beats for every major NPC and an
   open-ended post-game loop.

Six NPC arcs (Odessa, Mirabel, Brick, Nereus, Cass, Sefton) progress on
**affinity** (earned in conversation choices) crossed with **deeds**
(races won, rescues, dives, storms survived), so different playstyles
open different people first. Repeatable ambient beats keep every hook
point alive between arc beats.

## Deepening with each run

The requirement context exposes: run count, wrecks, homecomings, renown
level, almanac pages, every stat, every quality, and (at sea) hull/salvage/
region. Content keys to all of them, so the same tavern visit yields new
material as the player's history accumulates — the Hades trick, on a
Failbetter engine.

## The soundtrack

Eighteen tracks, all procedural: `core/composer.py` renders each spec in
`data/music.json` (tempo, root, mode, chord progression in scale degrees,
and six voices — pad, bass, arp, melody, percussion, surf) to a seeded,
deterministic stereo WAV. Specs are the source of truth; audio is a build
artifact cached in `assets/music/` (gitignored). Region themes darken with
depth (lydian Shallows → whole-tone Glass Squall), each activity has its
own tempo and temperament, and the run endings get somber, warm, and
triumphant pieces respectively.

Accessibility rule for music: it is atmosphere only. Every piece of
information the score hints at (region, danger, outcome) is also spoken,
music defaults to a low mix under speech and cues, and F2/F3/F4 control it
from anywhere without entering a menu.

## Extending the corpus

Add a JSON file to `data/story/`. The integrity tests enforce: unique ids,
resolvable `goto` targets, known effect keys, recognized requirement shapes,
and that every almanac page is obtainable. The reachability test walks the
main spine end to end.
