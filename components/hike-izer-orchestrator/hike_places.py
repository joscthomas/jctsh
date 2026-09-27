"""CARD-0311: name the area, trail(s), trailhead, and town/county/state of a hike.

Model: a hike is on named trails; a trail starts at a trailhead; trails lie in
an area (park/preserve); an area lies in a town, county, state, country.

ONE Overpass call per hike, for the hike's whole bounding box:
  - is_in() at NSAMPLES evenly spaced track points, each followed by a
    `make sample` marker, so the ordered result stream says which polygons
    contain which samples (area = the named park/preserve containing the most
    samples, not just the one at the start point);
  - every path-type way in the box with geometry (the trail segments);
  - the chosen area's boundary geometry, so the trailhead can be located where
    the track ENTERS the area (a hike often starts on a street some way before
    the trailhead; the first GPS point is not the trailhead);
  - trailhead/parking/guidepost features near that entry point.
The GPS track is matched against the ways to get the trails in the order hiked.

A hike in a town or city (no named park/preserve contains it) is named
differently: the AREA is the neighborhood (an OSM neighborhood/suburb/quarter
or named residential polygon, else Nominatim's) and the SEGMENTS are the named
streets and paths walked, in order. No trailhead is claimed unless OSM tags a
real highway=trailhead.

Everything is optional enrichment: any failure returns {} and the page simply
omits the lines. known-places.json (next to this file) overrides OSM names for
spots Joseph has named himself. Streets are never trails.
"""

import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import place_context as pc

NSAMPLES = 10
TRAIL_TYPES = {"path", "footway", "track", "bridleway", "cycleway", "steps"}
STREET_TYPES = {"residential", "service", "unclassified", "tertiary", "secondary", "primary", "living_street", "pedestrian"}
MATCH_M = 25            # track-to-way match distance
STEP_M = 10             # densified track spacing
GAP_FILL_M = 60         # off-way gap bridged when the same trail is on both sides
MIN_RUN_M = 80          # shorter runs are junction crossings, dropped
TRAILHEAD_RADIUS_M = 150
STREET_RADIUS_M = 100
MIN_AREA_SAMPLES = 3    # an area must contain this many of NSAMPLES
KNOWN_PLACES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "known-places.json")

# OSM name typos, corrected on the page only. Grown as real ones are found.
TYPO_TOKENS = {"Tral": "Trail", "Trai": "Trail", "Tail": "Trail", "Trl": "Trail"}


def fix_name(name):
    return " ".join(TYPO_TOKENS.get(tok, tok) for tok in name.split())


# ---------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------

def _projector(lat0):
    kx = 111320 * math.cos(math.radians(lat0))
    ky = 110540
    return lambda lat, lon: (lon * kx, lat * ky)


def _seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dy * dy
    t = 0 if length2 == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length2))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def _way_dist(p, geom):
    return min(_seg_dist(p, geom[i], geom[i + 1]) for i in range(len(geom) - 1))


def _thin(points_xy, min_gap):
    out = [points_xy[0]]
    for p in points_xy[1:]:
        if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) >= min_gap:
            out.append(p)
    return out


def _densify(points_xy, step):
    out = []
    for a, b in zip(points_xy, points_xy[1:]):
        k = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) // step))
        out += [(a[0] + (b[0] - a[0]) * i / k, a[1] + (b[1] - a[1]) * i / k) for i in range(k)]
    return out + [points_xy[-1]]


# ---------------------------------------------------------------------------
# the Overpass call
# ---------------------------------------------------------------------------

def _build_query(points, bbox):
    idx = [round(i * (len(points) - 1) / (NSAMPLES - 1)) for i in range(NSAMPLES)]
    stmts = ""
    for k, i in enumerate(idx):
        lat, lon = points[i]["lat"], points[i]["lon"]
        stmts += (
            f'is_in({lat},{lon})->.a{k};\n'
            f'(nwr(pivot.a{k})["boundary"~"protected_area|national_park|administrative"];\n'
            f' nwr(pivot.a{k})["leisure"~"nature_reserve|park"];\n'
            f' nwr(pivot.a{k})["place"~"neighbourhood|suburb|quarter"];\n'
            f' nwr(pivot.a{k})["landuse"="residential"]["name"];)->.r{k};\n'
            f'.r{k} out tags;\nmake sample k="{k}";\nout;\n'
        )
    south, west, north, east = bbox
    box = f"{south},{west},{north},{east}"
    union = "".join(f".r{k};" for k in range(NSAMPLES))
    return f"""[out:json][timeout:90];
{stmts}
({union})->.allareas;
(nwr.allareas["boundary"~"protected_area|national_park"]; nwr.allareas["leisure"~"nature_reserve|park"];)->.parkareas;
.parkareas out geom;
way["highway"~"path|footway|track|bridleway|cycleway|steps|residential|service|unclassified|tertiary|secondary|primary|living_street|pedestrian"]({box})->.ways;
.ways out geom tags;
(node["highway"="trailhead"]({box});
 node["amenity"="parking"]({box});
 way["amenity"="parking"]({box});
 node["information"~"guidepost|board"]({box}););
out center tags;
"""


def _overpass(query):
    """Same mirror/status-aware retry policy as place_context.named_features
    (CARD-0323): a 429 abandons the mirror, other HTTP errors get one retry
    honoring Retry-After. Returns the parsed body or None."""
    data = ("data=" + urllib.parse.quote(query)).encode("utf-8")
    last_error = None
    for url in pc.OVERPASS_URLS:
        for attempt in range(2):
            req = urllib.request.Request(url, data=data, headers={"User-Agent": pc.USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=100) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                last_error = e
                print(f"hike_places: {url} attempt {attempt + 1} failed: HTTP {e.code} {e.reason}", file=sys.stderr)
                if e.code == 429:
                    break
                if attempt == 0:
                    time.sleep(pc._retry_after_seconds(e.headers, default=3))
            except (urllib.error.URLError, ValueError, TimeoutError) as e:
                last_error = e
                print(f"hike_places: {url} attempt {attempt + 1} failed: {e}", file=sys.stderr)
                if attempt == 0:
                    time.sleep(3)
    print(f"hike_places: all mirrors/retries exhausted, last error: {last_error}", file=sys.stderr)
    return None


# ---------------------------------------------------------------------------
# reading the result
# ---------------------------------------------------------------------------

def _split_elements(body, project):
    """-> (areas {(type,id): [tags, {sample idx}]}, ways [(tags, xy geom)], features [element],
    boundaries {(type,id): [xy segment, ...]})"""
    areas, ways, features, cur, boundaries = {}, [], [], [], {}
    for el in body.get("elements", []):
        lines = []
        if el["type"] == "way" and "highway" not in el.get("tags", {}) and "geometry" in el:
            lines = [el["geometry"]]
        elif el["type"] == "relation" and any("geometry" in m for m in el.get("members", [])):
            lines = [m["geometry"] for m in el["members"] if "geometry" in m]
        if lines:
            segs = []
            for g in lines:
                xs = [project(n["lat"], n["lon"]) for n in g]
                segs += list(zip(xs, xs[1:]))
            boundaries[(el["type"], el["id"])] = segs
            continue
        if el["type"] == "sample":
            k = int(el["tags"]["k"])
            for a in cur:
                areas.setdefault((a["type"], a["id"]), [a.get("tags", {}), set()])[1].add(k)
            cur = []
        elif el["type"] == "way" and "geometry" in el and "highway" in el.get("tags", {}):
            ways.append((el["tags"], [project(n["lat"], n["lon"]) for n in el["geometry"]]))
        elif "center" in el or "lat" in el:
            features.append(el)
        elif el.get("tags"):
            cur.append(el)
    return areas, ways, features, boundaries


def _where(areas):
    admin = sorted(
        (-int(t["admin_level"]), t["name"]) for t, s in areas.values()
        if t.get("boundary") == "administrative" and t.get("name") and 0 in s
        and str(t.get("admin_level", "")).isdigit() and int(t["admin_level"]) <= 8
    )
    return ", ".join(name for _, name in admin) or None


def _area(areas):
    best = None
    for k, (t, s) in areas.items():
        kind = t.get("boundary") if t.get("boundary") in ("protected_area", "national_park") else t.get("leisure")
        if t.get("boundary") == "administrative" or kind not in ("protected_area", "national_park", "nature_reserve", "park"):
            continue
        if not t.get("name") or len(s) < MIN_AREA_SAMPLES:
            continue
        rank = (len(s), kind in ("protected_area", "national_park"))
        if best is None or rank > best[0]:
            best = (rank, t["name"], k)
    return (best[1], best[2]) if best else (None, None)


def _neighborhood(areas):
    """Named neighborhood/suburb/quarter (or named residential) polygon
    containing the most samples; place=* tags beat landuse on a tie."""
    best = None
    for t, s in areas.values():
        is_place = t.get("place") in ("neighbourhood", "suburb", "quarter")
        if not t.get("name") or len(s) < MIN_AREA_SAMPLES or not (is_place or t.get("landuse") == "residential"):
            continue
        rank = (len(s), is_place)
        if best is None or rank > best[0]:
            best = (rank, t["name"])
    return best[1] if best else None


def _nominatim_neighborhood(address):
    if not address:
        return None
    return next((address[k] for k in ("neighbourhood", "suburb", "quarter") if address.get(k)), None)


def _inside(p, segs):
    """Even-odd ray cast over every boundary segment (works for multi-part
    outlines without assembling rings)."""
    c = False
    for (x1, y1), (x2, y2) in segs:
        if (y1 > p[1]) != (y2 > p[1]) and p[0] < (x2 - x1) * (p[1] - y1) / (y2 - y1) + x1:
            c = not c
    return c


def _entry_point(track_xy, segs):
    """Where the track first goes from outside the area to inside it: of the
    two densified samples straddling that crossing, the one nearer the
    boundary. A track that starts inside enters at its first point. None if
    it never gets inside."""
    dense = _densify(_thin(track_xy, STEP_M), STEP_M)
    prev = None
    for p in dense:
        inside = _inside(p, segs)
        if inside:
            if prev is None:
                return p
            return min((prev, p), key=lambda q: min(_seg_dist(q, a, b) for a, b in segs))
        prev = p
    return None


def _collapse(labels):
    """labels: one name-or-None per STEP_M of track -> ordered [name, ...]."""
    def rle(ls):
        runs = []
        for l in ls:
            if runs and runs[-1][0] == l:
                runs[-1][1] += STEP_M
            else:
                runs.append([l, STEP_M])
        return runs

    runs = rle(labels)
    changed = True
    while changed:
        changed = False
        for i in range(1, len(runs) - 1):
            if runs[i][0] is None and runs[i][1] <= GAP_FILL_M and runs[i - 1][0] is not None and runs[i - 1][0] == runs[i + 1][0]:
                runs[i - 1][1] += runs[i][1] + runs[i + 1][1]
                del runs[i:i + 2]
                changed = True
                break
        if changed:
            continue
        for i, (name, length) in enumerate(runs):
            if name is not None and length < MIN_RUN_M:
                runs[i][0] = None
                runs = rle([n for n, ln in runs for _ in range(ln // STEP_M)])
                changed = True
                break
    order = []
    for name, _ in runs:
        if name is not None and (not order or order[-1] != name):
            order.append(name)
    return order


def _trails(track_xy, ways, urban=False):
    """Trail mode: nearest path-type way, so an unnamed path wins over a named
    street beside it (no mislabeling). Urban mode: only NAMED ways count,
    streets and paths alike, since sidewalks are unnamed and run beside the
    street being walked."""
    if urban:
        trail_ways = [(t, g) for t, g in ways if t.get("name") and t.get("highway") in (TRAIL_TYPES | STREET_TYPES)]
    else:
        trail_ways = [(t, g) for t, g in ways if t.get("highway") in TRAIL_TYPES]
    labels = []
    for p in _densify(_thin(track_xy, STEP_M), STEP_M):
        best = None
        for t, g in trail_ways:
            d = _way_dist(p, g)
            if d <= MATCH_M and (best is None or d < best[0]):
                best = (d, t)
        labels.append(fix_name(best[1]["name"]) if best and best[1].get("name") else None)
    return _collapse(labels)


def _trailhead(anchors_xy, project, features, ways, urban=False):
    """anchors_xy[0] is the primary anchor (where the track enters the area,
    else its first point); the first GPS point is also an anchor when it
    differs, since a trailhead lot is often right at the start even when the
    area polygon is entered further along. Named features count if near
    either; the street fallback uses the primary anchor only."""
    ranked = []
    for el in features:
        t = el.get("tags", {})
        c = el.get("center") or {"lat": el["lat"], "lon": el["lon"]}
        cx = project(c["lat"], c["lon"])
        d = min(math.hypot(cx[0] - a[0], cx[1] - a[1]) for a in anchors_xy)
        if d > TRAILHEAD_RADIUS_M:
            continue
        if t.get("highway") == "trailhead":
            rank = 0
        elif urban:
            continue
        elif t.get("amenity") == "parking" and t.get("name"):
            rank = 1
        elif "information" in t and t.get("name"):
            rank = 2
        else:
            continue
        ranked.append((rank, d, t.get("name")))
    named = [r for r in ranked if r[2]]
    if named:
        return fix_name(sorted(named)[0][2]), "trailhead"
    if urban:
        return None, None
    streets = sorted(
        (_way_dist(anchors_xy[0], g), t["name"]) for t, g in ways
        if t.get("highway") in STREET_TYPES and t.get("name")
    )
    if streets and streets[0][0] <= STREET_RADIUS_M:
        return fix_name(streets[0][1]), "street"
    return None, None


# ---------------------------------------------------------------------------
# known places (Joseph's own names)
# ---------------------------------------------------------------------------

_NOMINATIM_CACHE = {}


def _nominatim_address(point):
    """Reverse-geocodes once per (rounded) coordinate per process, not once
    per gather_hike_places() call -- harmless to share across hikes in the
    same run (a daily-refresh pass checks several), and keeps this module's
    own Nominatim usage as light as place_context.py's separate call for
    the same point, not doubled needlessly."""
    key = (round(point["lat"], 5), round(point["lon"], 5))
    if key not in _NOMINATIM_CACHE:
        body = pc._nominatim_reverse(point["lat"], point["lon"])
        _NOMINATIM_CACHE[key] = (body or {}).get("address") or {}
    return _NOMINATIM_CACHE[key]


def _load_known_places(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f).get("places", [])
    except (OSError, ValueError):
        return []


def _apply_known(result, track_xy, project, known):
    """An entry matches when the hike's track passes within the entry's radius
    of its trailhead coordinate (so it still matches when the Overpass call
    failed and no entry point could be computed).
    Its `trailhead`/`area` replace OSM's. Its `trail` renames the OSM trail
    named by `osm_trail`, or, if OSM found no trails at all, stands in for them."""
    for e in known:
        ex = project(e["lat"], e["lon"])
        if min(math.hypot(q[0] - ex[0], q[1] - ex[1]) for q in track_xy) > e.get("radius_m", 150):
            continue
        if e.get("trailhead"):
            result["trailhead"], result["trailhead_kind"] = e["trailhead"], "trailhead"
        if e.get("area"):
            result["area"] = e["area"]
        if e.get("trail"):
            if e.get("osm_trail") and e["osm_trail"] in result["trails"]:
                result["trails"] = [e["trail"] if n == e["osm_trail"] else n for n in result["trails"]]
            elif not result["trails"]:
                result["trails"] = [e["trail"]]
        break
    return result


def nominatim_where(address):
    """Fallback Where line from Nominatim's structured address, used only
    when the Overpass call gave no admin polygons (or failed outright)."""
    if not address:
        return None
    town = next((address[k] for k in ("city", "town", "village", "hamlet") if address.get(k)), None)
    parts = [town, address.get("county"), address.get("state"), address.get("country")]
    return ", ".join(p for p in parts if p) or None


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------

def gather_hike_places(hike_data, known_places_path=KNOWN_PLACES_PATH):
    """-> (result, ok). result is {'where', 'area', 'trails': [names in
    hiked order], 'trailhead', 'trailhead_kind': 'trailhead'|'street'|None},
    or {} if there is nothing to say. Never raises: place naming is
    enrichment, never allowed to block the pipeline.

    ok (CARD-0348) is this call's own success signal, independent of
    place_context.py's: True if the one Overpass call answered (even with
    nothing found) or there were fewer than 2 GPS points to look up in the
    first place (permanently resolved, nothing to retry); False only if
    Overpass itself failed or an unexpected error was caught -- the only
    case worth trying again on a later pass. A caller that gets ok=False
    may still get a real, fully-populated result THIS call (known-places
    and the Nominatim fallback below don't depend on Overpass at all) --
    ok only governs whether to bother re-running the lookup later, not
    whether this run's own result is usable."""
    try:
        points = [p for p in pc._hike_session_points(hike_data) if p.get("lat") is not None and p.get("lon") is not None]
        if len(points) < 2:
            return {}, True
        project = _projector(points[0]["lat"])
        track_xy = [project(p["lat"], p["lon"]) for p in points]
        pad = 0.001
        bbox = (
            min(p["lat"] for p in points) - pad, min(p["lon"] for p in points) - pad,
            max(p["lat"] for p in points) + pad, max(p["lon"] for p in points) + pad,
        )
        result = {"where": None, "area": None, "trails": [], "route_kind": "trail", "trailhead": None, "trailhead_kind": None}
        anchor = track_xy[0]
        body = _overpass(_build_query(points, bbox))
        if body is not None:
            areas, ways, features, boundaries = _split_elements(body, project)
            result["where"] = _where(areas)
            result["area"], area_key = _area(areas)
            urban = area_key is None
            if urban:
                result["area"] = _neighborhood(areas) or _nominatim_neighborhood(_nominatim_address(points[0]))
                result["route_kind"] = "street"
            result["trails"] = _trails(track_xy, ways, urban)
            if area_key is not None:
                anchor = _entry_point(track_xy, boundaries.get(area_key, [])) or anchor
            anchors = [anchor] if anchor == track_xy[0] else [anchor, track_xy[0]]
            result["trailhead"], result["trailhead_kind"] = _trailhead(anchors, project, features, ways, urban)
        result["where"] = result["where"] or nominatim_where(_nominatim_address(points[0]))
        _apply_known(result, track_xy, project, _load_known_places(known_places_path))
        result = result if any(result[k] for k in ("where", "area", "trails", "trailhead")) else {}
        return result, body is not None
    except Exception as e:
        print(f"hike_places: failed, page will omit these lines: {type(e).__name__}: {e}", file=sys.stderr)
        return {}, False
