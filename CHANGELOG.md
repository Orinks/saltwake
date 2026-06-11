# Changelog

## Unreleased

### Added
- **Auto-updater.** The packaged game now checks GitHub for new releases
  at the title menu. When one is found, a fully spoken prompt offers
  "Download and restart" (downloads the update, swaps it in, and
  relaunches the game for you), "What's new" (reads the update's changelog
  line by line), "Remind me later", and "Skip this version". A new
  Settings entry, "Update channel", picks between stable releases and
  nightly developer snapshots — nightly builds follow the dev channel by
  default, stable builds follow stable — and "Check for updates" looks
  right now. Source checkouts are left alone; git manages those.

## 0.1.0 — 2026-06-11

The first release of Saltwake: a watersports roguelite where the sea
remembers. Audio-first and screen-reader-first.

### Added
- **Six watersports contests played by ear**: boat racing, jet ski slalom,
  free-dive salvage, storm crossings, fishing, and rescue tows, all driven
  by stereo-panned cues with spoken twins.
- **Roguelite tides**: branching sea-chart headings across four regions
  with reach-warden bosses, per-run Tidings (boons), beacons, caches, and
  squalls. Salvage banks to pearls in full at homecoming, half on a wreck.
- **A novel-scale story** (~17,500 words, 100+ storylets): a three-act
  mystery told Hades-style across runs on a Sunless Sea style quality
  engine, with six NPC relationship arcs, wreck-greeting beats, a readable
  Drowned Almanac, and post-game epilogues.
- **Meta progression**: renown levels, six vessels, permanent gear, and
  post-victory Tide Marks difficulty.
- **An 18-track procedural soundtrack** (~13 minutes of loops) rendered
  from seeded specs at first launch; F2 toggles, F3/F4 set volume.
- **Accessibility throughout**: Prism speech (NVDA, JAWS, SAPI, VoiceOver,
  Speech Dispatcher), BASS audio via sound_lib with pygame fallback, a
  paged spoken manual, navigable Chronicle and Almanac, R/T/H information
  keys, and a visual mirror of the last spoken line.
- **Portable by design**: saves and the music cache live in the game's own
  directory; unzip and run.
