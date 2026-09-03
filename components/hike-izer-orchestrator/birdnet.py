#!/usr/bin/env python
"""
Hike-izer BirdNET Live integration (CARD-0080).

Parses whatever BirdNET Live session export(s) Joseph has dropped into a
hike's staging directory -- either the app's raw `.zip` (auto-extracted here,
so he never has to unzip it himself first) or a bare `.json` already pulled
out of one. Deliberately parsing only: no local-time formatting (that's
templating.py's job, same as every other time value it renders) and no API
calls (unlike photo_captions.py/place_context.py/narrative.py, there's
nothing here for Claude to identify -- BirdNET Live already did the
classification on-device).

Real exports (2026-07-29, two actual hikes, Live Mode -- see CARD-0182)
originally confirmed the shape: each `detections[]` entry had a precise UTC
`timestamp`, `commonName`, `scientificName`, and `confidence` -- GPS was
session-level only (one lat/lon for the whole survey, not per-detection).
That's no longer accurate -- CARD-0235 found a real per-detection
`latitude`/`longitude` on every detection in a 2026-08-29 Survey Mode
export (29 distinct coordinate pairs across 39 detections), added by a
BirdNET Live app update sometime between those two dates. `parse_detections()`
still deliberately does no location correlation for the per-hike Wildlife
Heard *table* (Joseph's call, CARD-0080: table only, Time column is
enough -- that decision stands), but now carries a representative `lat`/`lon`
per species for the Wildlife Detections *sheet* archive (CARD-0235).
`parse_occurrences()` (CARD-0133) is built for the Route Map's bird
markers, which do need a real position per sighting: it groups the same
raw per-detection timestamps into per-occurrence rows, each now carrying
its own representative `lat`/`lon` (from the nearest raw detection to
`representative_timestamp`) when the export has it, falling back to the
caller interpolating against the GPS track
(build_hike_map.interpolate_position()) when it doesn't -- older exports
still have no per-detection GPS at all. The model (BirdNET+) classifies
amphibians/mammals/insects alongside birds in the same unified taxonomy --
nothing here filters by taxon (Joseph's call: report everything the model
reports).
"""

import glob
import json
import os
import zipfile
from datetime import datetime, timedelta, timezone


def _load_export(path):
    """Returns the parsed top-level dict from a single BirdNET Live export
    file (`.json` read directly, `.zip` extracted in-memory), or None if
    `path` isn't a real BirdNET Live export -- so an unrelated staged file
    is silently skipped rather than crashing the whole step-2 run."""
    try:
        if path.endswith(".zip"):
            with zipfile.ZipFile(path) as zf:
                json_names = [
                    n for n in zf.namelist()
                    if n.endswith(".json") and not n.endswith(".metadata.json")
                ]
                if not json_names:
                    return None
                with zf.open(json_names[0]) as f:
                    data = json.load(f)
        else:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
    except (OSError, json.JSONDecodeError, zipfile.BadZipFile):
        return None
    if not isinstance(data, dict) or "detections" not in data:
        return None
    return data


def has_staged_export(staging_dir):
    """CARD-0229: distinguishes "no BirdNET file was ever staged" (the
    common, unremarkable case in step 1 -- nothing to report) from "a file
    was staged but parsing it produced zero detections" (worth a human
    flag -- could be a genuinely birdless hike, or could be a corrupted/
    truncated export silently swallowed by _load_export()'s own broad
    except clause). Same candidate-globbing _load_all_detections() uses,
    but only checks existence -- doesn't open/parse anything."""
    if not os.path.isdir(staging_dir):
        return False
    return bool(
        glob.glob(os.path.join(staging_dir, "*.zip"))
        + glob.glob(os.path.join(staging_dir, "*.json"))
    )


def _load_all_detections(staging_dir):
    """Scans `staging_dir` for BirdNET Live export(s) (`.zip` and/or `.json`
    -- supports more than one, e.g. multiple survey sessions staged for the
    same hike) and returns the flat list of every raw detection dict across
    all of them, exactly as BirdNET Live wrote them (`commonName`,
    `scientificName`, `confidence`, `timestamp`). Shared by parse_detections()
    (species-aggregated, for the existing Wildlife Heard table) and
    parse_occurrences() (CARD-0133, time-windowed per-sighting groups, for
    Route Map markers) so the export files only get read/parsed once.
    Returns an empty list if the staging directory doesn't exist or nothing
    staged there is a real BirdNET Live export -- same optional-resource
    treatment as the Gaia embed in generation.py's _read_staging()."""
    if not os.path.isdir(staging_dir):
        return []

    candidates = sorted(
        glob.glob(os.path.join(staging_dir, "*.zip"))
        + glob.glob(os.path.join(staging_dir, "*.json"))
    )

    detections = []
    for path in candidates:
        data = _load_export(path)
        if not data:
            continue
        detections.extend(data.get("detections", []))
    return detections


def parse_detections(staging_dir):
    """Returns one row per distinct species detected, sorted by
    first-detection time:

        {"common_name": ..., "scientific_name": ..., "count": ...,
         "best_confidence": ..., "first_timestamp": <raw UTC ISO string>,
         "lat": ..., "lon": ...}

    Output shape extended by CARD-0235 -- lat/lon are the first detection's
    own coordinates (tracked alongside first_timestamp, same "earlier
    detection found -> update together" logic), None on older exports that
    never carried per-detection GPS. templating.py's birdnet_table_rows()
    still only reads the pre-existing fields (CARD-0080: no location in
    the Wildlife Heard table) -- lat/lon here exist for the Wildlife
    Detections sheet archive (generation.py's _post_wildlife_detection())."""
    species = {}  # (common_name, scientific_name) -> accumulator dict
    for det in _load_all_detections(staging_dir):
        key = (det.get("commonName"), det.get("scientificName"))
        if key not in species:
            species[key] = {
                "common_name": det.get("commonName"),
                "scientific_name": det.get("scientificName"),
                "count": 0,
                "best_confidence": 0.0,
                "first_timestamp": det.get("timestamp"),
                "lat": det.get("latitude"),
                "lon": det.get("longitude"),
            }
        row = species[key]
        row["count"] += 1
        row["best_confidence"] = max(row["best_confidence"], det.get("confidence", 0.0))
        if det.get("timestamp") and (
            not row["first_timestamp"] or det["timestamp"] < row["first_timestamp"]
        ):
            row["first_timestamp"] = det["timestamp"]
            row["lat"] = det.get("latitude")
            row["lon"] = det.get("longitude")

    return sorted(species.values(), key=lambda r: r["first_timestamp"] or "")


def _parse_ts(iso_ts):
    dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _occurrence_row(common_name, scientific_name, dets):
    start, end = _parse_ts(dets[0]["timestamp"]), _parse_ts(dets[-1]["timestamp"])
    midpoint = start + (end - start) / 2

    # CARD-0235: lat/lon come from whichever raw detection in this run is
    # closest in time to the same midpoint already used for
    # representative_timestamp -- one real, traceable fix, not a synthetic
    # average. None on older exports with no per-detection GPS at all;
    # templating.py falls back to interpolate_position() in that case,
    # exactly as it always has.
    nearest = min(dets, key=lambda d: abs(_parse_ts(d["timestamp"]) - midpoint))

    return {
        "common_name": common_name,
        "scientific_name": scientific_name,
        "count": len(dets),
        "best_confidence": max(d.get("confidence", 0.0) for d in dets),
        "representative_timestamp": midpoint.isoformat().replace("+00:00", "Z"),
        "lat": nearest.get("latitude"),
        "lon": nearest.get("longitude"),
    }


def parse_occurrences(staging_dir, gap_minutes=5):
    """CARD-0133: a per-sighting-event view of the same raw detections
    parse_detections() aggregates down to one row per species for the whole
    scan -- for the Route Map's bird markers, which need real positions (via
    build_hike_map.interpolate_position() against each occurrence's own
    `representative_timestamp`), not one shared point for the entire hike.

    BirdNET Live can re-trigger on the same singing bird every few seconds
    for minutes at a stretch -- grouping consecutive same-species detections
    within `gap_minutes` of each other into one "occurrence" avoids placing
    one marker per raw re-trigger for a bird that never moved. Detections
    with no timestamp at all are skipped entirely (nothing to group them by
    or place them with).

    Returns one dict per occurrence, sorted by representative_timestamp
    (same sort convention parse_detections() already uses for
    first_timestamp):

        {"common_name": ..., "scientific_name": ..., "count": ...,
         "best_confidence": ..., "representative_timestamp": <raw UTC ISO
         string -- the occurrence's own start/end midpoint>}
    """
    by_species = {}
    for det in _load_all_detections(staging_dir):
        if not det.get("timestamp"):
            continue
        key = (det.get("commonName"), det.get("scientificName"))
        by_species.setdefault(key, []).append(det)

    gap_threshold = timedelta(minutes=gap_minutes)
    occurrences = []
    for (common_name, scientific_name), dets in by_species.items():
        dets.sort(key=lambda d: d["timestamp"])
        run = []
        for det in dets:
            if run and _parse_ts(det["timestamp"]) - _parse_ts(run[-1]["timestamp"]) > gap_threshold:
                occurrences.append(_occurrence_row(common_name, scientific_name, run))
                run = []
            run.append(det)
        if run:
            occurrences.append(_occurrence_row(common_name, scientific_name, run))

    return sorted(occurrences, key=lambda r: r["representative_timestamp"])
