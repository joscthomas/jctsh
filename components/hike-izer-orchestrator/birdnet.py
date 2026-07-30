#!/usr/bin/env python
"""
Hike-izer BirdNET Live integration (CARD-0080).

Parses whatever BirdNET Live Survey Mode export(s) Joseph has dropped into a
hike's staging directory -- either the app's raw `.zip` (auto-extracted here,
so he never has to unzip it himself first) or a bare `.json` already pulled
out of one. Deliberately parsing only: no local-time formatting (that's
templating.py's job, same as every other time value it renders) and no API
calls (unlike photo_captions.py/place_context.py/narrative.py, there's
nothing here for Claude to identify -- BirdNET Live already did the
classification on-device).

Real exports (2026-07-29, two actual hikes) confirmed the shape: each
`detections[]` entry has a precise UTC `timestamp`, `commonName`,
`scientificName`, and `confidence` -- but GPS is session-level only (one
lat/lon for the whole survey, not per-detection), so no location
correlation is attempted (Joseph's call: table only, Time column is enough).
The model (BirdNET+) classifies amphibians/mammals/insects alongside birds
in the same unified taxonomy -- nothing here filters by taxon (Joseph's
call: report everything the model reports).
"""

import glob
import json
import os
import zipfile


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


def parse_detections(staging_dir):
    """Scans `staging_dir` for BirdNET Live export(s) (`.zip` and/or `.json`
    -- supports more than one, e.g. multiple survey sessions staged for the
    same hike) and returns one row per distinct species detected, sorted by
    first-detection time:

        {"common_name": ..., "scientific_name": ..., "count": ...,
         "best_confidence": ..., "first_timestamp": <raw UTC ISO string>}

    Returns an empty list if the staging directory doesn't exist or nothing
    staged there is a real BirdNET Live export -- same optional-resource
    treatment as the Gaia embed in _read_staging()."""
    if not os.path.isdir(staging_dir):
        return []

    candidates = sorted(
        glob.glob(os.path.join(staging_dir, "*.zip"))
        + glob.glob(os.path.join(staging_dir, "*.json"))
    )

    species = {}  # (common_name, scientific_name) -> accumulator dict
    for path in candidates:
        data = _load_export(path)
        if not data:
            continue
        for det in data.get("detections", []):
            key = (det.get("commonName"), det.get("scientificName"))
            if key not in species:
                species[key] = {
                    "common_name": det.get("commonName"),
                    "scientific_name": det.get("scientificName"),
                    "count": 0,
                    "best_confidence": 0.0,
                    "first_timestamp": det.get("timestamp"),
                }
            row = species[key]
            row["count"] += 1
            row["best_confidence"] = max(row["best_confidence"], det.get("confidence", 0.0))
            if det.get("timestamp") and (
                not row["first_timestamp"] or det["timestamp"] < row["first_timestamp"]
            ):
                row["first_timestamp"] = det["timestamp"]

    return sorted(species.values(), key=lambda r: r["first_timestamp"] or "")
