#!/usr/bin/env python
"""
CARD-0210: one-time backfill for the wildlife life list's new per-hike
detection counts.

wildlife_life_list.json predates CARD-0210 -- every entry's "hikes" list
holds bare file_stem strings, not {"file_stem": ..., "count": ...} dicts,
so build_wildlife_index.py's new Detections/Detections-by-Month stats would
undercount every hike processed before this card (falling back to count=1
via _hike_count()'s legacy tolerance) unless the real counts are recovered.

Staged BirdNET exports are never deleted after use (CARD-0112/CARD-0119
convention) -- still sitting in every hike's own <file_stem>_staging/
directory -- so the real per-hike counts can be recovered directly by
re-running birdnet.parse_detections() against each one, rather than
migrating the old file in place with a synthetic count.

Rebuilds wildlife_life_list.json from scratch (does not try to merge with
whatever's already there) by replaying every hike's real BirdNET detections
through update_from_hike(), in file_stem order -- oldest first, so
first_heard resolves correctly without needing that function's own
defensive out-of-order handling to do any work.

Run once, inside the orchestrator container:
    docker exec hike-izer-orchestrator python3 backfill_wildlife_counts.py
Safe to re-run -- it's a full rebuild each time, not an incremental merge,
so re-running just reproduces the same correct result.
"""

import glob
import json
import os
import sys

import birdnet
import wildlife_life_list

SRV_DIR = "/srv/hike-izer"


def main():
    staging_dirs = sorted(glob.glob(os.path.join(SRV_DIR, "*_staging")))

    # Fresh rebuild -- remove any existing life list first so update_from_hike()
    # starts from empty rather than merging onto stale pre-CARD-0210 data.
    if os.path.exists(wildlife_life_list.LIFE_LIST_PATH):
        os.remove(wildlife_life_list.LIFE_LIST_PATH)

    processed = 0
    total_detections = 0
    for staging_dir in staging_dirs:
        dirname = os.path.basename(staging_dir)
        file_stem = dirname[: -len("_staging")]
        date_str = file_stem[:10]

        rows = birdnet.parse_detections(staging_dir)
        if not rows:
            continue

        wildlife_life_list.update_from_hike(file_stem, date_str, rows)
        processed += 1
        total_detections += sum(r["count"] for r in rows)
        print(
            f"{file_stem}: {len(rows)} species, {sum(r['count'] for r in rows)} detections",
            file=sys.stderr,
        )

    life_list = wildlife_life_list.load()
    print(
        f"\nBackfill complete: {processed} hikes with BirdNET data, "
        f"{len(life_list)} species total, {total_detections} total detections recorded.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
