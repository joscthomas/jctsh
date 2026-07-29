#!/usr/bin/env python
"""
Hike-izer place-context gathering (CARD-0108).

Grounds narrative.py's story in real facts about where the hike happened.
Three layers:

1. Base layer -- deterministic, free, no hallucination risk. OpenStreetMap
   Nominatim (street/neighborhood address) + Overpass (named park/school/
   trail features and their operator, containing or near the hike's own
   coordinates). CARD-0108's own experiment found Nominatim reverse-geocoding
   alone never surfaces a park/school name at any zoom level -- Overpass is
   the piece that actually answers "what is this place called."

2. Enrichment layer -- a scoped Claude + web_search call, run ONLY against
   confirmed named things (from Overpass or from a photo's sign_text) and
   real voiced content (Hiking Observations) -- never a blind search against
   raw coordinates. CARD-0108's own experiment found blind coordinate search
   expensive (~$0.35), rate-limited, and produced an unconfirmed guess where
   Overpass gave an exact free answer.

3. Regional layer -- geology/landform and biology/ecology, keyed to the
   broad area (county + state, via Nominatim's own address breakdown) rather
   than the exact point, since those facts are true anywhere in the region,
   not specific to one GPS coordinate. Cached to disk by region so repeat
   hikes in a familiar area (e.g. every Grand Rapids-area hike) reuse one
   lookup instead of re-searching every time -- only non-empty results are
   cached, so a transient search failure gets retried on the next hike
   rather than permanently baked in as "nothing found."

Deliberately returns a flat list of short, independent facts, not prose --
weaving them into the story, and eliminating overlap with the observations
table or between facts themselves, is narrative.py's job (per SKILL.md),
not this module's.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import anthropic

MODEL = "claude-opus-4-8"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
# Two independent public Overpass mirrors, tried in order. overpass-api.de
# returned 504 Gateway Timeout on two consecutive real runs several minutes
# apart during CARD-0108's own testing (2026-07-28) -- that gap plus two
# straight failures reads as a sustained outage on that specific instance,
# not a random blip, so a same-server retry wouldn't have helped; a second,
# independently-run mirror (Kumi Systems, speaks the same Overpass QL/
# response format) is the fix that actually addresses what was observed.
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
USER_AGENT = "jctsh-hike-izer/1.0 (personal project, https://hikes.jctnet.com)"
# CARD-0112: caps total named-feature queries per hike (route samples +
# distinct photo locations combined) and paces them -- found necessary
# against a real hike (2026-07-29) where an uncapped, back-to-back run
# tripped Overpass's own "Too Many Requests" almost immediately.
MAX_NAMED_FEATURE_QUERIES = 5
NAMED_FEATURE_QUERY_DELAY_S = 3


def _first_gps_point(hike_data):
    gps_rows = hike_data.get("gps_track") or []
    if not gps_rows:
        return None
    sorted_rows = sorted(gps_rows, key=lambda r: r.get("timestamp") or "")
    return sorted_rows[0]


def _hike_session_points(hike_data):
    """CARD-0112: every GPS point belonging to a confirmed is_hike session,
    chronologically ordered. Timestamps are compared as plain ISO 8601
    strings (not parsed to datetime) -- they sort correctly lexicographically
    since every timestamp in this pipeline shares the same format/offset, and
    this avoids a second parsing convention alongside fetch_hike_data.py's
    own. Returns [] if there's no confirmed hike."""
    coverage = hike_data.get("coverage", {})
    gps_track_coverage = coverage.get("gps_track", {})
    if not gps_track_coverage.get("hike_confirmed"):
        return []
    windows = [
        (s["start"], s["end"]) for s in gps_track_coverage.get("sessions", [])
        if s.get("is_hike")
    ]
    if not windows:
        return []
    gps_rows = hike_data.get("gps_track") or []
    points = [
        r for r in gps_rows
        if r.get("timestamp") and any(start <= r["timestamp"] <= end for start, end in windows)
    ]
    return sorted(points, key=lambda r: r["timestamp"])


def _sample_points(points, max_samples=3):
    """Evenly-spaced subset of points (always including the first and last),
    capped at max_samples -- enough to ground named-feature lookups along
    the whole route without one Overpass call per point."""
    if len(points) <= max_samples:
        return points
    step = (len(points) - 1) / (max_samples - 1)
    return [points[round(i * step)] for i in range(max_samples)]


def _dedupe_locations(points, precision=4):
    """Rounds lat/lon to `precision` decimals (~11m at 4 places) and drops
    repeats -- avoids firing near-identical Overpass queries for points
    that are effectively the same spot (e.g. several photos taken standing
    in one place, or a route sample landing close to another)."""
    seen = set()
    result = []
    for p in points:
        lat, lon = p.get("lat"), p.get("lon")
        if lat is None or lon is None:
            continue
        key = (round(lat, precision), round(lon, precision))
        if key in seen:
            continue
        seen.add(key)
        result.append(p)
    return result


def _nominatim_reverse(lat, lon):
    """Raw Nominatim reverse-geocode call -- one HTTP request, used for both
    the display_name (fallback location context) and the region key (county/
    state, for regional-context caching), so a single hike costs one
    Nominatim call, not two, out of respect for their free-tier usage
    policy. Returns the parsed response body, or None."""
    url = f"{NOMINATIM_URL}?lat={lat}&lon={lon}&format=jsonv2&zoom=16&addressdetails=1"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, TimeoutError) as e:
        print(f"_nominatim_reverse failed: {e}", file=sys.stderr)
        return None


def _region_key(nominatim_body):
    """A stable region-level identifier for regional-context caching --
    county + state (+ country), not the exact point, so hikes anywhere in
    the same broad area share one cached lookup. Takes the already-fetched
    Nominatim body (see _nominatim_reverse) rather than fetching again."""
    if not nominatim_body:
        return None
    addr = nominatim_body.get("address", {})
    county = addr.get("county") or addr.get("state_district")
    state = addr.get("state")
    country = addr.get("country")
    parts = [p for p in (county, state, country) if p]
    return ", ".join(parts) if parts else None


def named_features(lat, lon, radius_m=250):
    """Named parks, schools, and hiking-route relations containing or near
    the point, with operator where OSM has it. Returns [] on any failure --
    place context is enrichment, never allowed to block the pipeline."""
    query = f"""
[out:json][timeout:25];
(
  way(around:{radius_m},{lat},{lon})["amenity"="school"];
  way(around:{radius_m},{lat},{lon})["leisure"="park"];
  relation(around:{radius_m},{lat},{lon})["amenity"="school"];
  relation(around:{radius_m},{lat},{lon})["leisure"="park"];
  relation(around:{radius_m},{lat},{lon})["route"="hiking"];
);
out tags center;
"""
    data = ("data=" + urllib.parse.quote(query)).encode("utf-8")

    # Up to 2 attempts per mirror, 2 mirrors -- a live direct test (2026-07-28)
    # found the second mirror timing out too, on its own, nothing else
    # running -- three timeouts across two independent providers this
    # session. That's broader than one instance being down, so retry alone
    # or fallback alone isn't enough confidence; this combines both. Still
    # not a guarantee -- free public Overpass access has no SLA, and the
    # real safety net is the [] graceful-degradation path below, not this
    # loop succeeding every time.
    body = None
    last_error = None
    for url in OVERPASS_URLS:
        for attempt in range(2):
            req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=35) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                break
            except (urllib.error.URLError, urllib.error.HTTPError, ValueError, TimeoutError) as e:
                last_error = e
                print(f"named_features: {url} attempt {attempt + 1} failed: {e}", file=sys.stderr)
                if attempt == 0:
                    time.sleep(3)
        if body is not None:
            break

    if body is None:
        print(f"named_features: all mirrors/retries exhausted, last error: {last_error}", file=sys.stderr)
        return []

    seen = set()
    features = []
    for el in body.get("elements", []):
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name or name in seen:
            continue
        seen.add(name)
        features.append({
            "name": name,
            "type": tags.get("amenity") or tags.get("leisure") or tags.get("route"),
            "operator": tags.get("operator"),
        })
    return features


ENRICHMENT_PROMPT_TEMPLATE = """You're gathering grounded background facts about a hike, to help someone \
else write a narrative account of the day. Use web search for anything specific -- don't \
rely on general knowledge, since a plausible-sounding guess is worse than no fact at all.

Here's what's already confirmed about the location (found via OpenStreetMap, not search \
-- treat as reliable, no need to re-verify these specific facts):
{named_features_text}

Here's text read directly off signs/plaques photographed during the hike:
{sign_text_block}

Here's what the hiker said out loud during the hike (voice observations, chronological):
{observations_text}

Your job:
1. If any of the observations above are genuine open questions -- the hiker wondering \
what something is, what it's called, what an abbreviation stands for -- search to \
answer them.
2. Research brief, genuinely interesting background on the named places/things above -- \
history, why they're named what they're named, what a mentioned program or organization \
actually is. Prioritize what would surprise someone; skip generic filler.
3. Budget your searches: use at most 4 total, and prefer one strong source per topic over \
cross-verifying the same fact with multiple searches -- a confident answer from a single \
good source is enough, and each additional search adds real cost.
4. Your ENTIRE final response must be either a flat list of short, independent facts (one \
per line, no bullets or numbering), or the single word NONE and nothing else. Each fact \
must stand alone and not overlap with any other fact in your list -- if two searches turn \
up the same underlying fact, state it once. If you can't find a confident answer to \
something, leave it out entirely rather than guessing.

Critical: your final response is read programmatically as a plain list of facts, one per \
line. Do NOT include any explanation, apology, meta-commentary about your search process, \
or description of tool limitations you hit -- if you have zero confident facts for any \
reason, including a search failure, respond with exactly NONE and nothing else. A line of \
narration about what you tried would be misread as a fact and shown to a reader as if it \
were true.
"""


def _format_named_features(features):
    if not features:
        return "(nothing found nearby)"
    lines = []
    for f in features:
        bits = [f["name"]]
        if f.get("type"):
            bits.append(f"({f['type']})")
        if f.get("operator"):
            bits.append(f"-- operated by {f['operator']}")
        lines.append(" ".join(bits))
    return "\n".join(lines)


# Defense in depth beyond each prompt's explicit "respond NONE, never
# narrate" ban: observed live (2026-07-28) that under a real web_search
# failure, the model narrated what went wrong instead of returning NONE --
# "I'll research...", "Search limit reached..." came back looking exactly
# like facts, since nothing structurally distinguishes narration from a
# real fact once it's just lines of text. Any line that reads as process
# narration invalidates the whole batch -- safer to return nothing than
# risk shipping meta-commentary into the narrative as if it were true.
# Shared by both research calls (per-hike enrichment and regional) since
# both hit the same failure mode.
_NARRATION_MARKERS = (
    "i'll ", "let me ", "i'm unable", "i was unable", "i cannot",
    "search limit", "search tool", "unable to capture", "unable to run",
    "per the instructions", "rather than guess", "rather than risk",
)


def _run_research_call(prompt, api_key, max_tokens, max_uses, cost_tracker=None):
    """Shared Claude + web_search research call for both the per-hike
    enrichment layer and the regional layer -- same strict-format contract
    (NONE sentinel, no narration) enforced identically."""
    client = anthropic.Anthropic(api_key=api_key)
    try:
        # Streamed, not a blocking create() -- a real run 2026-07-28 hit
        # Anthropic's long-request timeout at 1801s and errored out (see
        # docs.anthropic.com/en/api/errors#long-requests): adaptive thinking
        # plus multiple web_search round-trips can genuinely run past the
        # ~10 min a non-streaming call is allowed. Streaming has no such
        # ceiling; get_final_message() still hands back the same complete
        # Message object once the model is done.
        with client.messages.stream(
            model=MODEL,
            max_tokens=max_tokens,
            # Without a dedicated place to think, the model's own research
            # narration landed directly in the final text response,
            # indistinguishable from real facts once split into lines --
            # found live 2026-07-28. Adaptive thinking gives it somewhere
            # else to reason; the narration guard below stays as a
            # backstop, not the primary defense.
            thinking={"type": "adaptive"},
            tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": max_uses}],
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            response = stream.get_final_message()
    except Exception as e:
        # Enrichment is optional -- never let a search failure block the
        # narrative call, same principle as every other enrichment step in
        # this pipeline (photo captions, forecast capture).
        print(f"_run_research_call failed: {e}", file=sys.stderr)
        return []

    if cost_tracker:
        cost_tracker.record(response)

    # A web_search response's .content interleaves text blocks with
    # server_tool_use/web_search_tool_result blocks -- one narration-style
    # text block ("I'll search for...") typically precedes EACH search, with
    # the real final answer as the last text block(s) after the last search
    # result. Found live 2026-07-28: joining every text block (the previous
    # approach) pulled those pre-search narration blocks in alongside good
    # facts, so the narration guard correctly caught a marker and discarded
    # a real, useful research pass. Only the text after the last non-text
    # block is the model's actual final answer.
    last_non_text_idx = -1
    for i, block in enumerate(response.content):
        if block.type != "text":
            last_non_text_idx = i
    final_blocks = response.content[last_non_text_idx + 1:]
    text = "\n".join(b.text for b in final_blocks if b.type == "text").strip()
    if not text or text.upper() == "NONE":
        return []

    facts = [line.strip() for line in text.splitlines() if line.strip()]
    for line in facts:
        if any(marker in line.lower() for marker in _NARRATION_MARKERS):
            print(f"_run_research_call: discarding likely-narration response: {text!r}", file=sys.stderr)
            return []

    return facts


def gather_enrichment(named, sign_texts, observations_text, api_key, cost_tracker=None):
    if not named and not sign_texts and not observations_text:
        return []

    prompt = ENRICHMENT_PROMPT_TEMPLATE.format(
        named_features_text=_format_named_features(named),
        sign_text_block="\n".join(sign_texts) if sign_texts else "(none)",
        observations_text=observations_text or "(none)",
    )
    # Room for both thinking and a genuinely long facts list -- found live
    # (2026-07-28) that a real research pass produces upwards of 15-20
    # substantive facts. max_uses cut 6->4 same day, after a real combined
    # enrichment+regional run cost $1.86 (300K input tokens, 11 searches) --
    # each search's results compound into every later turn's input tokens
    # within the call, so trimming max_uses cuts more than proportionally.
    return _run_research_call(prompt, api_key, max_tokens=3000, max_uses=4, cost_tracker=cost_tracker)


REGIONAL_PROMPT_TEMPLATE = """You're gathering brief, genuinely interesting regional \
background for a hike narrative -- not about the exact spot, but the broader area: \
{region}.

Research using web search -- don't rely on general knowledge, since a plausible-sounding \
guess is worse than no fact at all.

Cover, if you can find confident answers:
1. Geology/landform -- the underlying geology or landform history of this region (e.g. \
glacial history, bedrock type, how the terrain was formed).
2. Biology/ecology -- what ecoregion this falls in, and anything genuinely notable about \
the native plant/wildlife community here (e.g. whether a commonly-seen species is native \
or introduced to this specific region).

Keep it regional, not hyper-local -- these facts should hold true anywhere in {region}, \
not be specific to one exact GPS point (a separate step already handles that). Prioritize \
what would genuinely surprise someone; skip generic filler.

Budget your searches: use at most 3 total, and prefer one strong source per topic over \
cross-verifying the same fact with multiple searches -- a confident answer from a single \
good source is enough, and each additional search adds real cost.

Your ENTIRE final response must be either a flat list of short, independent facts (one \
per line, no bullets or numbering), or the single word NONE and nothing else. If you \
can't find a confident answer, leave it out entirely rather than guessing.

Critical: your final response is read programmatically as a plain list of facts, one per \
line. Do NOT include any explanation, apology, or meta-commentary about your search \
process -- if you have zero confident facts for any reason, respond with exactly NONE and \
nothing else.
"""


def gather_regional_context(region, api_key, cost_tracker=None):
    if not region:
        return []
    prompt = REGIONAL_PROMPT_TEMPLATE.format(region=region)
    # max_uses cut 5->3 same day as the enrichment cut above, same reasoning
    # -- this is a one-time-per-region cost, but still worth trimming since
    # it's the same compounding-input-tokens effect.
    return _run_research_call(prompt, api_key, max_tokens=2000, max_uses=3, cost_tracker=cost_tracker)


def _load_regional_cache(cache_path):
    if not cache_path or not os.path.exists(cache_path):
        return {}
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        print(f"_load_regional_cache failed: {e}", file=sys.stderr)
        return {}


def _save_regional_cache(cache_path, cache):
    if not cache_path:
        return
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except OSError as e:
        print(f"_save_regional_cache failed: {e}", file=sys.stderr)


def gather_regional(region, cache_path, api_key, cost_tracker=None):
    """Regional facts, cached by region key. Only non-empty results are
    cached -- a search that found nothing (including a transient failure)
    is retried on the next hike in the region rather than permanently baked
    in as "nothing here.\" A cache hit costs nothing -- cost_tracker only
    sees a call on an actual (uncached) search."""
    if not region:
        return []

    cache = _load_regional_cache(cache_path)
    if region in cache:
        return cache[region]

    facts = gather_regional_context(region, api_key, cost_tracker=cost_tracker)
    if facts:
        cache[region] = facts
        _save_regional_cache(cache_path, cache)
    return facts


def gather_place_context(hike_data, photos_manifest, api_key, regional_cache_path=None, cost_tracker=None):
    """Top-level entry point. Returns a flat list of short facts for
    narrative.py to weave in -- [] if there's nothing to say (no GPS,
    nothing found, no observations/signs worth searching on)."""
    point = _first_gps_point(hike_data)
    if not point or point.get("lat") is None or point.get("lon") is None:
        return []
    lat, lon = point["lat"], point["lon"]

    # Address/region are about "where is this hike, broadly" -- the first
    # point is a fine anchor for that regardless of route shape, and using
    # it keeps this to one Nominatim call as before.
    nominatim_body = _nominatim_reverse(lat, lon)
    address = nominatim_body.get("display_name") if nominatim_body else None
    region = _region_key(nominatim_body)

    # CARD-0112: named-feature lookup, in contrast, is about "what's actually
    # along the route" -- querying only the first point confirmed wrong on a
    # real hike (a neighborhood loop that starts from the same spot every
    # day surfaced a landmark from a *different* day's hike, since the fixed
    # anchor doesn't reflect which direction that day's hike actually went).
    # Sample a handful of points along the confirmed hike session instead of
    # one, plus every distinct photo capture location when photos exist
    # (step 2) -- the strongest possible signal for what was near a specific
    # photographed moment. Deduped by rounded coordinate first (avoid
    # firing near-identical Overpass queries) and by feature name after.
    #
    # Capped and paced, found necessary against a real hike (2026-07-29):
    # an uncapped run fired 8+ Overpass queries back-to-back and tripped
    # its own "Too Many Requests" almost immediately, on top of Overpass's
    # already-documented flakiness (CARD-0108) -- MAX_NAMED_FEATURE_QUERIES
    # keeps the total request count sane, and the pause between calls gives
    # each a fair shot instead of queuing into the same rate limit. Route
    # samples are prioritized (they define the path); photo locations only
    # fill whatever budget remains.
    hike_points = _hike_session_points(hike_data)
    route_samples = _dedupe_locations(_sample_points(hike_points) if hike_points else [point])
    photo_points = _dedupe_locations((photos_manifest or {}).get("assets", []))
    already_queried = {(round(p["lat"], 4), round(p["lon"], 4)) for p in route_samples}
    photo_samples = [
        p for p in photo_points
        if (round(p["lat"], 4), round(p["lon"], 4)) not in already_queried
    ]
    query_points = (route_samples + photo_samples)[:MAX_NAMED_FEATURE_QUERIES]

    named = []
    seen_names = set()
    for i, p in enumerate(query_points):
        if i > 0:
            time.sleep(NAMED_FEATURE_QUERY_DELAY_S)
        for f in named_features(p["lat"], p["lon"]):
            if f["name"] not in seen_names:
                seen_names.add(f["name"])
                named.append(f)

    facts = []
    if address:
        facts.append(f"Location: {address}")
    for f in named:
        bits = [f["name"]]
        if f.get("type"):
            bits.append(f"a {f['type']}")
        if f.get("operator"):
            bits.append(f"operated by {f['operator']}")
        facts.append(" -- ".join(bits) if len(bits) > 1 else bits[0])

    sign_texts = [
        a["sign_text"] for a in (photos_manifest or {}).get("assets", [])
        if a.get("sign_text")
    ]
    observations_text = "\n".join(
        o.get("observation", "") for o in hike_data.get("hiking_observations", [])
    )

    facts.extend(gather_enrichment(named, sign_texts, observations_text, api_key, cost_tracker=cost_tracker))
    facts.extend(gather_regional(region, regional_cache_path, api_key, cost_tracker=cost_tracker))
    return facts
