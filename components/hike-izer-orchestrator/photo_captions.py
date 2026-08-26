#!/usr/bin/env python
"""
Hike-izer photo captioning (CARD-0107).

Identifies the clear focal-point subject of each hike photo -- a species,
landmark, or named facility/sign -- as a short caption. Deliberately not part
of narrative.py's call: captions render directly on the photo grid (as
visible text and as real alt text, replacing the empty alt="" every photo
previously shipped with), so they can't drift into the same table/narrative
redundancy problem CARD-0109 exists to prevent, and CARD-0108's scoped-search
enrichment can key off a named subject once one exists.

Uses Immich's already-downloaded `thumb` variant, not `original` -- CARD-0107's
real experiment (2026-07-28, 3 real photos) found identical identification
quality at ~24% lower cost.
"""

import base64
import json
import os
import sys

import anthropic
from pydantic import BaseModel

MODEL = "claude-opus-4-8"

PROMPT = (
    "This photo was taken during a hike. Two separate things:\n\n"
    "1. caption: a short caption (under 12 words) naming the clear focal "
    "subject -- a specific plant or wildlife species, or a landmark -- but "
    "ONLY if that identification adds something a viewer can't already see "
    "for themselves in the photo. Do NOT just repeat or paraphrase text "
    "that's already legible on a sign, plaque, or label in the photo -- "
    "restating visible text is redundant with what the photo already shows, "
    "not a real caption. If the photo's clear subject is a sign/plaque and "
    "there's nothing to add beyond what it already says, leave caption "
    "empty. Also leave it empty if nothing is confidently identifiable, or "
    "the photo is self-explanatory with no specific subject (a general "
    "view, a person, an unremarkable trail shot). Don't guess and don't "
    "force a caption where there's nothing to add.\n\n"
    "2. sign_text: if a sign, plaque, or other readable text is the photo's "
    "clear subject, transcribe its text here as accurately as you can. This "
    "is NOT shown to the reader as a caption -- it's captured as raw "
    "material for a later search step that looks up what the named place or "
    "thing actually is. Leave empty if there's no such text in the photo."
)


class PhotoObservation(BaseModel):
    caption: str
    sign_text: str


def _caption_one(client, thumb_path, cost_tracker=None):
    with open(thumb_path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    response = client.messages.parse(
        model=MODEL,
        # sign_text can run long on a busy promotional sign (found live,
        # 2026-07-28 -- 100 was tuned for caption alone and truncated
        # mid-JSON-string on two real photos, failing to parse).
        max_tokens=400,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}},
                {"type": "text", "text": PROMPT},
            ],
        }],
        output_format=PhotoObservation,
    )
    if cost_tracker:
        cost_tracker.record(response)
    return response.parsed_output.caption.strip(), response.parsed_output.sign_text.strip()


def caption_photos(photos_manifest, photos_dir, api_key, cost_tracker=None):
    """Adds 'caption' (shown to the reader) and 'sign_text' (not shown --
    raw text transcribed from a sign/plaque in the photo, captured for
    CARD-0108's later search step) to each image asset in photos_manifest
    (mutates and returns it). Videos are skipped -- this is a still-image
    task. CARD-0214: an asset that already carries a 'caption' key (recovered
    from a prior pass by generation.py's _fetch_photos()) is left untouched
    -- only genuinely new assets get a real _caption_one() call, so a second
    or later pass over the same hike never re-pays for a photo it already
    captioned.

    CARD-0117: also writes the captioned manifest back to
    <photos_dir>/manifest.json, overwriting fetch_hike_photos.py's original
    caption-less version. Previously captions only ever existed in memory
    for the one render call that immediately followed -- found live
    2026-07-29 when a page got re-rendered (to fix an unrelated bug) from
    the on-disk manifest and silently lost real, already-paid-for captions,
    since the file on disk had never actually held them. Persisting here
    means any future re-render reads the real thing instead of a stale
    caption-less copy."""
    if not photos_manifest or not photos_manifest.get("assets"):
        return photos_manifest

    client = anthropic.Anthropic(api_key=api_key)
    for asset in photos_manifest["assets"]:
        if asset.get("type") != "IMAGE":
            continue
        # CARD-0214: a 'caption' key already present means generation.py's
        # _fetch_photos() recovered it from a prior pass (keyed by Immich's
        # own asset id) -- skip re-captioning something already paid for.
        # Only assets genuinely new since the last pass reach _caption_one().
        if "caption" in asset:
            continue
        thumb_path = os.path.join(photos_dir, asset["thumb"])
        try:
            asset["caption"], asset["sign_text"] = _caption_one(client, thumb_path, cost_tracker=cost_tracker)
        except Exception as e:
            # A captioning failure shouldn't block the rest of the gallery --
            # same "never let an optional enrichment step break the pipeline"
            # principle already applied to photo fetch (CARD-0084) and
            # forecast capture (CARD-0083/CARD-0106).
            print(f"Caption failed for {asset['thumb']}: {e}", file=sys.stderr)
            asset["caption"] = ""
            asset["sign_text"] = ""

    try:
        manifest_path = os.path.join(photos_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(photos_manifest, f, indent=2)
    except OSError as e:
        # Captions still render on this run either way (they're already in
        # the in-memory manifest returned below) -- a write failure here
        # only risks a future re-render missing them, not this one.
        print(f"Failed to persist captioned manifest to {manifest_path}: {e}", file=sys.stderr)

    return photos_manifest
