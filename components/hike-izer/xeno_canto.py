#!/usr/bin/env python
"""
CARD-0174: reference bird-call lookup via the Xeno-canto API. Deployed copy
from components/hike-izer/ into components/hike-izer-orchestrator/ at build
time (Dockerfile), same pattern as build_hike_map.py/build_hike_chart.py --
both templating.py (in-process import) and build_wildlife_index.py (its own
subprocess, see generation.py's BUILD_WILDLIFE_SCRIPT call) import this
directly.

Looks up one representative recording per species, keyed by scientific name
(more precise/stable than English name, which can mismatch BirdNET's own
common-name spelling), and caches results to a shared JSON file so the same
species looked up on one page (a per-hike page via templating.py) is already
cached for the other (wildlife.html via build_wildlife_index.py) -- these
run as separate OS processes within the same generation.py run, so the
cache is what makes that sharing work, not shared Python state. Cache is
re-read and re-written on every call rather than held open across calls --
call volume is a handful of species per page, not a hot path, so the extra
I/O is cheap and this stays correct across processes without needing any
locking.

Server-side only: the API key never reaches the browser. The rendered page
embeds Xeno-canto's own public audio-file URL directly (safe to be public,
same as any other CDN link) -- never the key itself, which stays in this
process's environment (XENO_CANTO_API_KEY, see generation.py's _env()-style
handling) and is never written into generated HTML.

Standard library only -- matches every other component in this pipeline.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

API_URL = "https://xeno-canto.org/api/3/recordings"
CACHE_PATH = "/srv/hike-izer-private/xeno_canto_cache.json"

# Prefer an actual song/call over incidental noise (alarm calls, flight
# calls, begging calls, etc. are real recordings but less useful as a
# "what does this species normally sound like" reference); prefer
# better-quality recordings when more than one type match exists. This is
# a best-effort ranking over whatever a 10-recording sample returns, not a
# hard filter -- any identified recording is better than none.
_TYPE_PREFERENCE = ("song", "call")
_QUALITY_RANK = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}


def _pick_best(recordings):
    def rank(r):
        rtype = (r.get("type") or "").lower()
        type_rank = next(
            (i for i, pref in enumerate(_TYPE_PREFERENCE) if pref in rtype),
            len(_TYPE_PREFERENCE),
        )
        return (type_rank, _QUALITY_RANK.get(r.get("q"), 5))
    return min(recordings, key=rank)


def _query(scientific_name, api_key):
    genus, _, species = scientific_name.partition(" ")
    query = urllib.parse.quote(f"gen:{genus} sp:{species}")
    url = f"{API_URL}?query={query}&key={urllib.parse.quote(api_key)}&per_page=10"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None

    recordings = data.get("recordings") or []
    if not recordings:
        return None

    best = _pick_best(recordings)
    if not best.get("file"):
        return None
    return {
        "audio_url": best["file"],
        "recordist": best.get("rec") or "unknown",
        "license_url": best.get("lic") or "",
        "xc_url": best.get("url") or "",
    }


def load_cache(path=CACHE_PATH):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_cache(cache, path=CACHE_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def lookup(scientific_name, api_key, cache_path=CACHE_PATH):
    """Returns a dict {audio_url, recordist, license_url, xc_url}, or None
    if there's no key configured yet, no recording was found, or the API
    call failed -- caller omits the speaker icon entirely in every None
    case, same "don't fabricate" convention as the rest of this pipeline.
    A failed lookup is cached as None too (not retried every call) --
    genuinely rare species with no Xeno-canto coverage shouldn't cost a
    fresh API round-trip on every single page that mentions them."""
    if not api_key:
        return None

    cache = load_cache(cache_path)
    if scientific_name in cache:
        return cache[scientific_name]

    result = _query(scientific_name, api_key)
    cache[scientific_name] = result
    save_cache(cache, cache_path)
    return result


def render_button_html(audio, esc):
    """Speaker-icon button + hidden <audio> element for one species, or ''
    if no reference call was found. `esc` is the caller's own HTML-
    escaping function -- both templating.py and build_wildlife_index.py
    already have one, no need for this module to take on that dependency
    itself. Shared here (not duplicated in each template) so both pages
    render byte-identical markup -- CARD-0176 hit real drift from exactly
    this kind of duplication between the two templates. Pairs with each
    page's own click-delegation script (`.audio-btn` -> toggle play/pause
    on the next sibling `<audio>`), not included here since it's one
    listener per page, not one per button."""
    if not audio:
        return ""
    title = (
        f"Reference call — recording by {audio['recordist']}, Xeno-canto "
        f"(CC BY-NC-SA) — {audio['xc_url']}"
    )
    return (
        f' <button class="audio-btn" type="button" title="{esc(title)}">&#128266;</button>'
        f'<audio preload="none" src="{esc(audio["audio_url"])}"></audio>'
    )
