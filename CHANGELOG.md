# Changelog

## Unreleased

### Added
- **A big story content update** (~7,500 new words, 37 new storylets,
  now ~24,500 words across 140+ storylets):
  - **What the brass key opens.** The key you washed in with finally has
    an answer, and Liss is the one holding it. After the finale she joins
    the Brinehouse regulars with her own arc: the lamp locker, bell
    seniority, and an apprenticeship.
  - **The Keeper gets his own visits.** New lighthouse storylets teach
    you the lamp code, and tell you about the three tideborn he went to
    see before you.
  - **Every NPC arc grows**: Odessa tags the untagged photograph, Mirabel
    reopens Ren's stall and explains the corner table, Brick fills out
    the invitational entry form and trades storm fears, Nereus reads you
    the Jane's printed timetable and starts a book about the living,
    Cass learns to hear the water and finally beats you fair, and the
    chandler brothers invent a knot for a debt the sea paid back.
  - **The world answers the ending.** New post-finale beats nearly
    everywhere: the Pale Ferry's last crossing, the drowned forest gone
    quiet, the Leviathan's circle unwound, the regatta champion vindicated,
    wrecks where the sea walks you home as a friend, Liss waiting furious
    on the shingle, new homecomings, a beacon dry shelf finally emptying,
    and the sea's post resuming with living mail.
  - **Four new Drowned Almanac pages**, including the Jane's annotated
    summer timetable and the lamp locker's standing orders.
- **The Drowned Almanac grows to 50 pages, bound in five volumes.**
  Thirty-eight new "loose pages" — town bylaws, ferry logs, letters,
  lifeboat records, beacon customs, and post-finale living mail — now
  wash up from gameplay: successful dives, fishing hauls, drifting
  caches, wax-page sea events, and pages held for you at friendly
  beacons, each a random page you don't yet hold. Marquee pages stay
  story-granted, the New Mornings volume arrives with the ending, and
  the Almanac reader is reorganized into Nereus's five volumes (The
  Town, The Ferry, The Squall Year, The Coast, The New Mornings), each
  with spoken found-of-total counts.
- **Keepsakes: the sea returns what was somebody's.** Deep dives can now
  surface personal objects the water kept — a thimble, a whistle, a
  medal, a letter twenty years late, a school slate, a twice-engraved
  ring — each with a spoken hint about who might know it. They ride in a
  new Sea chest menu at the quay, and carrying one to its owner plays a
  delivery scene: memories recovered, families traced, accounts settled.
  Emotional, cozy, and the game's premise in miniature: the sea holds
  people's memories and gives them back attached to things. Keepsakes
  gate themselves behind the story so nothing surfaces before its owner
  could receive it, follow-up beats linger after delivery, and three new
  achievements mark the courier work (134 total).
- **The Lantern Jane post-game strand.** The story engine can now see
  which hull is under you, and she uses it: a first cast-off under your
  own hands, the sea making way for a sea-kept boat, a family asking for
  a crossing over the Hollow, the channel buoys ringing her home, the
  dawn run revived with a lamp keeper (senior) aboard, a homecoming the
  whole quay stops for, the Leviathan meeting the boat it kept, the
  drowned town flashing its windows at her shadow, and an answer to the
  question nobody wanted to ask: what happens if you wreck her. Two new
  hidden achievements ride along (131 total).
- **129 achievements, easy to hard, all rooted in the story.** Six
  spoken categories at the quay — The Tide That Turned, The Quay, The
  Water, Tides and Salt, The Post, and Deep Cuts — covering every story
  milestone, relationship, activity, and collection, with 37 hidden
  marks that stay "a secret the sea is keeping" until earned so the
  list never spoils the story. Unlocks are announced with queued speech
  and a fanfare the moment they land (storylets, activity results, run
  end, or back at the quay), and persist in the save.
- **Ties.** A new quay menu that speaks where you stand with every
  character you've met: a named closeness level per person (from
  "strangers, so far" to "family in all but paper"), with Enter or H
  reading the regard and the story bonds you've forged.
- **Memories.** Another new quay menu: every storylet you have seen stays
  re-readable, grouped by teller (the main story, each character, the sea
  itself), with the Almanac's reading controls. What people said stays
  said.
- **Copy the Chronicle.** The Chronicle can now put your whole record on
  the system clipboard as plain text, ready to paste — press C anywhere
  in it, or pick the new "Copy the Chronicle to the clipboard" entry.
- **Linux AppImage.** Releases now also ship a single-file
  `Saltwake-<version>-linux-x86_64.AppImage` that runs on any modern
  distribution — download it, mark it executable, and run it. Saves and
  the music cache live in a `Saltwake` folder next to the AppImage (or
  under `~/.local/share/saltwake` if that spot isn't writable), and the
  pre-rendered soundtrack is copied there on first run so nothing has to
  compose. Every AppImage is boot-tested on Fedora before release, so
  non-Debian distributions are no longer a gamble.

### Changed
- **Release gate, Freight Fate style.** Nightly developer snapshots now
  build from the `dev` branch instead of `main`, so changes soak in
  snapshots before a stable is tagged from `main`. Every build first
  passes the test suite, the headless self-test, and a new dependency
  check (`build_release.py --check-dependencies`) that verifies the
  Prism and BASS native libraries and the game data before any build
  time is spent; the frozen build's smoke test now also asserts the
  story corpus, almanac volumes, and achievements actually shipped
  inside the bundle.

### Fixed
- **End-of-tide storylets can finally see the finished run.** The
  run-end hook never passed the run along, so the "heavy boat"
  homecoming beat (gated on salvage aboard) could never trigger. It
  fires now, and vessel- and salvage-gated endings work in general.
- **Story choice responses are no longer cut off.** Picking a choice used
  to queue its response and immediately return to the menu underneath,
  whose announcement interrupted the response before it was heard —
  every choice without a follow-up storylet appeared to respond silently.
  Responses are now read like story pages: Enter or down arrow advances,
  up arrow re-reads, R repeats, Escape skips, and the scene only closes
  after the last line.
- **Speech no longer talks over itself across the game.** Menus that
  reopen right after an announcement (shipyard purchases, chandlery,
  tavern small talk, beacon rest and patch, Tiding picks, the save
  confirmation) now queue behind it instead of cutting it off. Sea event
  outcomes, region descriptions, weather reports, boss intros, and the
  end-of-tide summary are likewise read in full.
- **Pressing on into the next region no longer hangs the game.** Winning
  a reach warden and choosing to continue left the expedition without a
  menu; the new region now announces itself and presents its first
  heading.

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
