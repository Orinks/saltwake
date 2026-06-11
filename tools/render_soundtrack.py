"""Pre-renders the entire soundtrack to assets/music/.

Usage:  uv run python tools/render_soundtrack.py [--force]
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))

from core.composer import duration_seconds, render_track, write_wav
from core.music import MUSIC_CACHE, load_specs


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the Saltwake soundtrack")
    parser.add_argument("--force", action="store_true", help="re-render existing tracks")
    args = parser.parse_args()

    os.makedirs(MUSIC_CACHE, exist_ok=True)
    specs = load_specs()
    total = 0.0
    for track_id, spec in specs.items():
        path = os.path.join(MUSIC_CACHE, f"{track_id}.wav")
        if os.path.isfile(path) and not args.force:
            print(f"  = {spec['title']} (cached)")
            continue
        start = time.perf_counter()
        pcm = render_track(spec)
        write_wav(path, pcm)
        secs = duration_seconds(pcm)
        total += secs
        print(f"  + {spec['title']}: {secs:.0f}s loop "
              f"(rendered in {time.perf_counter() - start:.2f}s)")
    print(f"{len(specs)} tracks in {MUSIC_CACHE}")
    if total:
        print(f"New audio rendered: {total / 60:.1f} minutes of loops")
    return 0


if __name__ == "__main__":
    sys.exit(main())
