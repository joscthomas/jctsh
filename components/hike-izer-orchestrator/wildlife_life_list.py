#!/usr/bin/env python
"""
CARD-0142: a running cross-hike life list of every species BirdNET Live has
ever identified while hiking. `birdnet.py` only ever parses one hike's own
staged export at render time -- nothing about a species persists once that
render is done, so no single hike-izer page can answer "have I heard this
before, and when." This module is the small piece of memory that closes
that gap: every time a hike's BirdNET detections are parsed (both step 1's
best-effort pass and step 2's real pass, CARD-0135), the caller merges that
hike's species into this file.

Keyed by scientific_name (globally unique, unlike common_name). Idempotent:
re-processing the same hike (step 1 then step 2, or a re-render) updates
that hike's own entry in place -- never duplicates, never double-counts.

CARD-0210: each entry's "hikes" list holds {"file_stem": ..., "count": ...}
dicts, not bare file_stem strings -- count is birdnet.parse_detections()'s
own per-hike detection count for that species, carried through so
build_wildlife_index.py can compute detection-frequency and by-month
seasonality stats. No separate date field needed: every file_stem already
starts with YYYY-MM-DD, the same trick the "First Heard" column's sort
already relies on. Re-processing the same hike overwrites that hike's own
stored count (last-processed-wins) rather than appending a duplicate or
summing -- step 2's real BirdNET pass should supersede step 1's best-effort
one, not add to it.

CARD-0276: each hike dict also carries "archived" (bool) -- whether this
species' row for this hike has actually reached the "Wildlife Detections"
Sheet, tracked separately from the entry existing at all. Before this field
existed, generation.py's own dedup check (skip re-posting a species already
recorded for this file_stem) conflated "this hike was rendered" with "this
hike's Sheets write succeeded" -- since update_from_hike() ran unconditionally
right after the archive attempt regardless of whether it actually posted, a
failed Sheets write was silently never retried by any later pass (e.g. the
daily refresh). A hike entry with archived=False (or missing the key, for a
species newly recorded by an in-progress archive attempt) is still a valid
retry candidate; a pre-CARD-0276 entry with no "archived" key at all is
treated as already-archived by generation.py's dedup check, since that
historical data predates per-row tracking and mass-retrying it would just
re-post rows Joseph never had reason to suspect are missing.
"""

import json
import os
import sys
import urllib.parse
import urllib.request

LIFE_LIST_PATH = "/srv/hike-izer-private/wildlife_life_list.json"


def load(path=LIFE_LIST_PATH):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def update_from_hike(file_stem, date_str, birdnet_rows, archived_species=None, path=LIFE_LIST_PATH):
    """birdnet_rows is birdnet.parse_detections()'s own output -- one dict
    per species already seen this hike, with common_name/scientific_name/
    first_timestamp. Merges each into the persisted life list and rewrites
    it in place. No-op if birdnet_rows is empty (nothing to merge).

    CARD-0276: archived_species, when given, is the set of scientific_name
    values whose Sheets archive attempt actually succeeded for this hike
    (generation.py's _archive_new_wildlife_detections() return value) --
    every other row gets archived=False so a later pass still treats it as
    a retry candidate instead of silently considering it done. None (the
    default) marks every row archived=True, matching pre-CARD-0276 behavior
    -- used by rebuild_from_sheets(), whose rows are Sheets-derived by
    construction and therefore already known-archived."""
    if not birdnet_rows:
        return

    life_list = load(path)
    for row in birdnet_rows:
        key = row["scientific_name"]
        is_archived = archived_species is None or key in archived_species
        entry = life_list.get(key)
        if entry is None:
            entry = {
                "common_name": row["common_name"],
                "scientific_name": row["scientific_name"],
                "first_heard_date": date_str,
                "first_heard_file_stem": file_stem,
                "hikes": [],
            }
            life_list[key] = entry
        elif date_str < entry["first_heard_date"]:
            # Defensive -- in practice hikes are processed in chronological
            # order, but if a backfill or re-run ever processes an earlier
            # hike after a later one, the earliest sighting should win.
            entry["first_heard_date"] = date_str
            entry["first_heard_file_stem"] = file_stem

        existing_hike = next((h for h in entry["hikes"] if h["file_stem"] == file_stem), None)
        if existing_hike is None:
            entry["hikes"].append({"file_stem": file_stem, "count": row["count"], "archived": is_archived})
        else:
            existing_hike["count"] = row["count"]
            if is_archived:
                # Only ever flips False/missing -> True here -- never regress
                # an already-True flag back to False for a row that simply
                # wasn't in this particular archived_species set (e.g. a
                # rebuild_from_sheets() call, which always passes None and
                # would otherwise be a no-op update anyway).
                existing_hike["archived"] = True

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(life_list, f, indent=2)


def rebuild_from_sheets(export_url, export_key, path=LIFE_LIST_PATH):
    """CARD-0229: recovery tool, not part of the regular generation flow --
    reconstructs the local life-list cache from scratch from the "Wildlife
    Detections" sheet's full history (the sheet is now the durable source
    of truth; this file is a rebuildable cache of it, per that card's own
    decision). Replays every hike's rows through update_from_hike() in
    chronological order, reusing its existing merge/idempotency logic
    rather than duplicating it -- the only new part here is fetching and
    grouping the Sheets data. Overwrites `path` unconditionally; caller's
    job to back it up first if that matters."""
    url = export_url + "?" + urllib.parse.urlencode({"key": export_key, "action": "export", "sheet": "Wildlife Detections"})
    with urllib.request.urlopen(url, timeout=60) as resp:
        result = json.loads(resp.read())
    if result.get("status") != "ok":
        raise RuntimeError(f"Apps Script export failed: {result}")

    by_hike = {}
    for row in result.get("rows", []):
        file_stem = row.get("hike_file_stem")
        if not file_stem:
            continue
        by_hike.setdefault(file_stem, []).append({
            "common_name": row.get("common_name"),
            "scientific_name": row.get("scientific_name"),
            "count": row.get("count"),
            "best_confidence": row.get("best_confidence"),
            "first_timestamp": row.get("timestamp"),
        })

    if os.path.exists(path):
        os.remove(path)  # start from empty -- update_from_hike() below re-`load()`s each call

    for file_stem in sorted(by_hike.keys()):
        date_str = file_stem[:10]
        update_from_hike(file_stem, date_str, by_hike[file_stem], path=path)

    return len(by_hike)


if __name__ == "__main__":
    # CARD-0229: manual recovery only -- e.g.
    #   docker exec hike-izer-orchestrator python3 -c "
    #     import wildlife_life_list, os
    #     wildlife_life_list.rebuild_from_sheets(os.environ['APPS_SCRIPT_URL'], os.environ['APPS_SCRIPT_KEY'])"
    # or run this file directly with APPS_SCRIPT_URL/APPS_SCRIPT_KEY already in the environment.
    url = os.environ.get("APPS_SCRIPT_URL")
    key = os.environ.get("APPS_SCRIPT_KEY")
    if not url or not key:
        print("APPS_SCRIPT_URL and APPS_SCRIPT_KEY must be set in the environment.", file=sys.stderr)
        raise SystemExit(1)
    n = rebuild_from_sheets(url, key)
    print(f"Rebuilt {LIFE_LIST_PATH} from {n} hike(s) in the Wildlife Detections sheet.")
