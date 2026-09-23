#!/usr/bin/env python
"""
CARD-0308: a running cross-hike life list of every animal species whose
scat has been confidently identified in a hike photo. Structural mirror of
wildlife_life_list.py (CARD-0142) -- same persistence shape, same
idempotent merge-per-hike design, same archived-tracking discipline -- but
a genuinely separate file/sheet/page, not merged into the BirdNET-sourced
wildlife life list (CARD-0308's own interview: audio-based bird ID and
photo-based scat ID are different evidence qualities, kept structurally
parallel rather than combined).

Keyed by scientific_name (globally unique, unlike common_name). Idempotent:
re-processing the same hike updates that hike's own entry in place -- never
duplicates, never double-counts.

Each entry's "hikes" list holds {"file_stem": ..., "count": ...} dicts --
count is how many distinct photos on that hike had this species' scat
confidently identified. Re-processing the same hike overwrites that hike's
own stored count (last-processed-wins), same as the wildlife sibling.

Each hike dict also carries "archived" (bool) -- whether this species' row
for this hike has actually reached the "Scat Detections" Sheet, tracked
separately from the entry existing at all, same CARD-0276 discipline the
wildlife life list already established (a failed Sheets write must stay
retry-eligible, not get silently marked done just because this local cache
was updated).
"""

import json
import os
import sys
import urllib.parse
import urllib.request

LIFE_LIST_PATH = "/srv/hike-izer-private/scat_life_list.json"


def load(path=LIFE_LIST_PATH):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def update_from_hike(file_stem, date_str, scat_rows, archived_species=None, path=LIFE_LIST_PATH):
    """scat_rows: one dict per species identified this hike, each with
    common_name/scientific_name/count (see generation.py's
    _scat_rows_from_manifest()). Merges each into the persisted life list
    and rewrites it in place. No-op if scat_rows is empty.

    archived_species: the set of scientific_name values whose Sheets
    archive attempt actually succeeded for this hike
    (generation.py's _archive_new_scat_detections() return value) -- every
    other row gets archived=False so a later pass still treats it as a
    retry candidate. None (the default) marks every row archived=True --
    used by rebuild_from_sheets(), whose rows are Sheets-derived by
    construction and therefore already known-archived."""
    if not scat_rows:
        return

    life_list = load(path)
    for row in scat_rows:
        key = row["scientific_name"]
        is_archived = archived_species is None or key in archived_species
        entry = life_list.get(key)
        if entry is None:
            entry = {
                "common_name": row["common_name"],
                "scientific_name": row["scientific_name"],
                "first_identified_date": date_str,
                "first_identified_file_stem": file_stem,
                "hikes": [],
            }
            life_list[key] = entry
        elif date_str < entry["first_identified_date"]:
            # Defensive -- in practice hikes are processed in chronological
            # order, but if a backfill or re-run ever processes an earlier
            # hike after a later one, the earliest sighting should win.
            entry["first_identified_date"] = date_str
            entry["first_identified_file_stem"] = file_stem

        existing_hike = next((h for h in entry["hikes"] if h["file_stem"] == file_stem), None)
        if existing_hike is None:
            entry["hikes"].append({"file_stem": file_stem, "count": row["count"], "archived": is_archived})
        else:
            existing_hike["count"] = row["count"]
            if is_archived:
                existing_hike["archived"] = True

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(life_list, f, indent=2)


def rebuild_from_sheets(export_url, export_key, path=LIFE_LIST_PATH):
    """Recovery tool, not part of the regular generation flow -- reconstructs
    the local life-list cache from scratch from the "Scat Detections"
    sheet's full history (the sheet is the durable source of truth; this
    file is a rebuildable cache of it, same CARD-0229 precedent as the
    wildlife life list). Replays every hike's rows through
    update_from_hike() in chronological order. Overwrites `path`
    unconditionally; caller's job to back it up first if that matters."""
    url = export_url + "?" + urllib.parse.urlencode({"key": export_key, "action": "export", "sheet": "Scat Detections"})
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
        })

    if os.path.exists(path):
        os.remove(path)  # start from empty -- update_from_hike() below re-`load()`s each call

    for file_stem in sorted(by_hike.keys()):
        date_str = file_stem[:10]
        update_from_hike(file_stem, date_str, by_hike[file_stem], path=path)

    return len(by_hike)


if __name__ == "__main__":
    # Manual recovery only -- e.g.
    #   docker exec hike-izer-orchestrator python3 -c "
    #     import scat_life_list, os
    #     scat_life_list.rebuild_from_sheets(os.environ['APPS_SCRIPT_URL'], os.environ['APPS_SCRIPT_KEY'])"
    # or run this file directly with APPS_SCRIPT_URL/APPS_SCRIPT_KEY already in the environment.
    url = os.environ.get("APPS_SCRIPT_URL")
    key = os.environ.get("APPS_SCRIPT_KEY")
    if not url or not key:
        print("APPS_SCRIPT_URL and APPS_SCRIPT_KEY must be set in the environment.", file=sys.stderr)
        raise SystemExit(1)
    n = rebuild_from_sheets(url, key)
    print(f"Rebuilt {LIFE_LIST_PATH} from {n} hike(s) in the Scat Detections sheet.")
