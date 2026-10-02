#!/usr/bin/env python
"""
data-pipeline-api -- CARD-0349, all components migrated as of 2026-09-29
(Environmental Data, GPS Track, Hike Start Forecast, Wildlife Detections,
Hiking Observations, and Hike-izer Costs -- the last of these was outside
CARD-0349's original "5 tables" scope, migrated as a same-day follow-on).
scat-detection deliberately has no route -- already unused before this
migration. Fully replaces core/data-pipeline/environmental-data.gs.
Design doc: core/data-pipeline/timescaledb-design.md.

Explicit per-purpose routes (not one POST keyed on a hidden `component`
string, per Joseph's decision to redesign rather than preserve
environmental-data.gs's old shape) -- see the design doc's section 3 table
for the full route/replaces/caller mapping. GPS ingest stays a GET with
query-string params: GPSLogger's own "custom URL" logging feature only
supports templated GET URLs, a real device constraint, not a design choice.

Handler shape matches components/hike-izer-orchestrator/app.py's existing
convention (investigate existing patterns first, don't invent a new house
style for one more Python HTTP service on this same host): stdlib
http.server, a shared _authorized(parts) check against ?key=, a
_respond(status, dict) helper.
"""

import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, date, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs

import psycopg2
import psycopg2.errors
import psycopg2.extras
import psycopg2.pool
import psycopg2.sql

VERSION = "2026-10-01.1-env-bulk"  # action=version fingerprint, same "confirm a
# redeploy actually landed" convention as environmental-data.gs's own
# SCRIPT_VERSION.

# CARD-0377: .strip() every env var read here -- found live that .env's CRLF
# line endings left a trailing \r on every value (API_KEY included), which
# curl would send without complaint but which silently desynced the stdlib
# http.server's header/body parsing on the receiving end. .env has been fixed
# directly too, but stripping here means a future CRLF-contaminated edit
# (e.g. saved from a Windows editor again) can't reintroduce the same bug.
API_KEY = os.environ.get("API_KEY", "").strip()

# CARD-0372: dual-accept window for key rotation. During a rotation the OLD key
# is moved to API_KEY_PREVIOUS and stays valid until API_KEY_PREVIOUS_EXPIRES
# (ISO 8601 UTC, or epoch seconds). The gateway enforces the expiry itself, so
# the window closes on schedule whether or not anything else runs. A previous
# key with no valid expiry is ignored entirely -- an unbounded second key is
# exactly what the window exists to avoid.
API_KEY_PREVIOUS = os.environ.get("API_KEY_PREVIOUS", "").strip()


def _parse_expiry(raw):
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromtimestamp(float(raw), tz=timezone.utc)
    except ValueError:
        pass
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


API_KEY_PREVIOUS_EXPIRES = _parse_expiry(os.environ.get("API_KEY_PREVIOUS_EXPIRES", ""))
PORT = int(os.environ.get("PORT", "8080"))
DB_HOST = os.environ.get("DB_HOST", "timescaledb")
DB_NAME = os.environ.get("DB_NAME", "jctsh")
DB_USER = os.environ.get("DB_USER", "jctsh")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "").strip()

# CARD-0349 Phase 2: this container has no MQTT client of its own (same
# constraint environmental-data.gs had -- see CLAUDE.md's "MQTT vs Direct
# HTTP" section), so dashboard visibility for GPS Track/Hike Start Forecast/
# Wildlife Detections goes through hike-izer-orchestrator's existing
# /webhook/pipeline-log relay, same as the old Apps Script used.
PIPELINE_LOG_URL = os.environ.get("PIPELINE_LOG_URL", "https://hikes.jctnet.com/webhook/pipeline-log").strip()
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "").strip()

# Field list matches environmental-data.gs's doPost appendRow column order
# exactly (core/data-pipeline/environmental-data.gs, ~line 457) and
# init/schema.sql. rain_tips/rssi_dbm are the only integer columns; every
# other sensor field is double precision.
ENV_INT_FIELDS = ("rain_tips", "rssi_dbm")
ENV_FLOAT_FIELDS = (
    "lat", "lon", "temp_f", "humidity_pct", "pressure_hpa", "dew_point_f",
    "heat_index_f", "uv_index", "irradiance_wm2", "wind_speed_mph",
    "wind_dir_deg", "rainin", "dailyrainin", "battery_v", "pm1_ug_m3",
    "pm25_ug_m3", "pm4_ug_m3", "pm10_ug_m3", "voc_index", "nox_index",
    "illuminance_lx", "solar_v",
)
ENV_OPTIONAL_FIELDS = ENV_FLOAT_FIELDS + ENV_INT_FIELDS

EXPORT_TABLES = ("environmental_data", "gps_track", "wildlife_detections", "hike_start_forecast", "hiking_observations", "hike_izer_cost")

_pool = None  # set in main(); psycopg2.pool.ThreadedConnectionPool


def log(message, err=False):
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[{ts}] {message}", file=sys.stderr if err else None, flush=True)


class _BadField(Exception):
    """Raised by _coerce() -- caught once in the POST handler to produce a
    single, consistent 400 response instead of duplicating validation-error
    handling at every call site."""
    def __init__(self, field, value):
        self.field = field
        self.value = value
        super().__init__(f"invalid value for {field}: {value!r}")


def _coerce(payload, field):
    """None/'' -> None (column stays NULL, same "most sources leave most
    fields blank" tolerance environmental-data.gs's own v() helper had).
    Otherwise casts to int (rain_tips/rssi_dbm) or float (everything else),
    raising _BadField on anything that doesn't parse -- Postgres would
    otherwise reject the whole INSERT with a much less specific error."""
    value = payload.get(field)
    if value is None or value == "":
        return None
    try:
        return int(value) if field in ENV_INT_FIELDS else float(value)
    except (TypeError, ValueError):
        raise _BadField(field, value)


def _relay_log(component, category, message):
    """Best-effort dashboard visibility via hike-izer-orchestrator's relay --
    never allowed to break the caller (matches environmental-data.gs's own
    _relayLog, which likewise never let a log failure break real work)."""
    if not WEBHOOK_SECRET:
        return
    try:
        body = json.dumps({"component": component, "category": category, "message": message}).encode()
        # CARD-0349 Step 6/7's own finding, ported here proactively: Cloudflare's
        # Bot Fight Mode (fronting hikes.jctnet.com) silently 403s urllib's
        # default User-Agent before the request ever reaches the orchestrator.
        req = urllib.request.Request(
            f"{PIPELINE_LOG_URL}?key={WEBHOOK_SECRET}", data=body,
            headers={"Content-Type": "application/json", "User-Agent": "jctsh-hike-izer/1.0"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10).read()
    except (urllib.error.URLError, OSError) as e:
        log(f"_relay_log failed ({component}/{category}): {e}", err=True)


# CARD-0349 Phase 2: ported verbatim from environmental-data.gs's own
# hiking-observations branch -- category keyword scan, all-matching (not
# first-match), lowercase substring search.
OBSERVATION_TAXONOMY = {
    "vegetation": ["saguaro", "bloom", "cactus", "tree", "shrub", "flower", "plant", "grass", "palo verde", "ocotillo"],
    "wildlife": ["bird", "hawk", "coyote", "snake", "rabbit", "deer", "javelina", "lizard", "butterfly", "insect"],
    "weather": ["cloud", "rain", "wind", "storm", "thunder", "lightning", "temperature", "hot", "cold", "warm", "cool"],
    "visibility": ["clear", "hazy", "smoke", "dust", "fog", "smoggy", "murky"],
    "sky": ["moon", "sun", "stars", "sunrise", "sunset", "rainbow", "shadow"],
    "air_quality": ["smoky", "dusty", "smell", "odor", "particulate", "ash"],
    "trail": ["trail", "path", "wash", "ridge", "peak", "summit", "canyon", "rock", "boulder", "erosion"],
    "subjective": ["feels", "seems", "appears", "noticed", "unusual", "different", "surprising"],
}


def _categorize_observation(text):
    lower = text.lower()
    return [cat for cat, keywords in OBSERVATION_TAXONOMY.items() if any(k in lower for k in keywords)]


SESSION_GAP_MIN = 10  # CARD-0115: matches fetch_hike_data.py's own
# session_gap_min=10 convention -- kept in sync deliberately, ported unchanged
# from environmental-data.gs's own _maybeCaptureHikeStartForecast.


def _maybe_capture_hike_start_forecast(conn, ts, lat, lon):
    """Ported from environmental-data.gs's _maybeCaptureHikeStartForecast
    (CARD-0083/CARD-0097/CARD-0115) -- CARD-0349 Phase 2. Called after a real
    (non-duplicate) GPS point is stored. Captures a forecast snapshot at the
    start of each detected hike *session* (a gap of more than
    SESSION_GAP_MIN minutes since the previous point ever recorded), not
    once per calendar day. Never allowed to break the GPS point's own
    success response -- every failure path here only logs, same as the
    original's try/catch-and-relay shape."""
    try:
        with conn.cursor() as cur:
            # CARD-0245: the true most-recent-prior point by timestamp, not
            # whichever row happens to be last -- ts alone is the primary
            # key here (unlike the old sheet's insertion-order ambiguity),
            # so this is a straightforward indexed lookup, not a full scan.
            cur.execute(
                "SELECT ts FROM gps_track WHERE ts < %s ORDER BY ts DESC LIMIT 1",
                (ts,),
            )
            prior = cur.fetchone()
        if prior is not None:
            gap_min = (ts - prior[0]).total_seconds() / 60
            if gap_min <= SESSION_GAP_MIN:
                return  # continuing an existing session

        _relay_log("gps-track", "System", "New GPS session started.")

        req = urllib.request.Request(
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&hourly=temperature_2m,relative_humidity_2m,precipitation_probability,"
            "wind_speed_10m,uv_index&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read())
        hourly = body.get("hourly") or {}
        times = hourly.get("time") or []
        if not times:
            _relay_log("hike-start-forecast", "Alert", "Forecast capture failed: Open-Meteo response had no hourly data.")
            return

        offset_sec = body["utc_offset_seconds"]
        target_ms = ts.timestamp() * 1000
        date_local = datetime.fromtimestamp(target_ms / 1000 + offset_sec, tz=timezone.utc).date().isoformat()

        idx, best_diff = 0, float("inf")
        for h, t in enumerate(times):
            instant_ms = datetime.fromisoformat(t + ":00+00:00").timestamp() * 1000 - offset_sec * 1000
            diff = abs(instant_ms - target_ms)
            if diff < best_diff:
                best_diff, idx = diff, h

        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO hike_start_forecast "
                "(ts, date_local, lat, lon, temp_f, precip_pct, wind_mph, humidity_pct, uv_index, provider) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'open-meteo')",
                (
                    ts, date_local, body["latitude"], body["longitude"],
                    hourly["temperature_2m"][idx], hourly["precipitation_probability"][idx],
                    hourly["wind_speed_10m"][idx], hourly["relative_humidity_2m"][idx],
                    hourly["uv_index"][idx],
                ),
            )
        conn.commit()
        _relay_log("hike-start-forecast", "System", f"Captured hike-start forecast for {date_local}.")
    except psycopg2.errors.UniqueViolation:
        # Two GPS points from the same new session racing this check --
        # harmless, the first one already captured it.
        conn.rollback()
    except Exception as e:
        conn.rollback()
        log(f"Forecast capture failed: {e}", err=True)
        _relay_log("hike-start-forecast", "Alert", f"Forecast capture failed: {e}")


def _gps_lookup(conn, ts):
    """Same nearest-neighbor-within-5-minutes query as _handle_lookup_gps
    (design doc section 4 / environmental-data.gs's own _gpsLookup) --
    a standalone copy, not a refactor of that already-verified live route,
    used internally by _maybe_capture_hike_start_forecast and
    _handle_hiking_observations (CARD-0349 Phase 2)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT lat, lon FROM gps_track "
            "WHERE abs(extract(epoch from (ts - %s))) <= 300 "
            "ORDER BY abs(extract(epoch from (ts - %s))) LIMIT 1",
            (ts, ts),
        )
        row = cur.fetchone()
    return (row[0], row[1]) if row else (None, None)


def _insert_boot_events(conn, source, boot_events):
    """CARD-0377 Phase 3: records every boot a device's upload mentions, so a
    per-session reset count is queryable later (not just visible once in the
    relay message below). (source, boot_id) is the dedup key -- a retried
    upload re-sending the same boot_events is a no-op, not a double-count."""
    inserted = 0
    for ev in boot_events:
        if not isinstance(ev, dict):
            continue
        boot_id = ev.get("boot")
        if not boot_id:
            continue
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO device_boot_events (source, boot_id, reset_reason) "
                    "VALUES (%s, %s, %s) ON CONFLICT (source, boot_id) DO NOTHING",
                    (source, boot_id, ev.get("reset_reason")),
                )
                inserted += cur.rowcount
            conn.commit()
        except Exception as e:
            conn.rollback()
            log(f"device_boot_events insert failed (source={source}, boot={boot_id}): {e}", err=True)
    return inserted


def _insert_env_row(conn, ts, source, values):
    """CARD-0377: the actual INSERT, extracted out of _handle_environmental_data
    so the new bulk handler can reuse the identical dedup/range-check behavior
    instead of duplicating it. Returns a result dict, never calls _respond --
    callers decide how/whether to report each row (one HTTP response for the
    single-row caller, one aggregate response for the bulk caller)."""
    columns = ["ts", "source"] + list(ENV_OPTIONAL_FIELDS)
    row_values = [ts, source] + [values[f] for f in ENV_OPTIONAL_FIELDS]
    try:
        query = psycopg2.sql.SQL("INSERT INTO environmental_data ({cols}) VALUES ({vals})").format(
            cols=psycopg2.sql.SQL(", ").join(map(psycopg2.sql.Identifier, columns)),
            vals=psycopg2.sql.SQL(", ").join([psycopg2.sql.Placeholder()] * len(columns)),
        )
        with conn.cursor() as cur:
            cur.execute(query, row_values)
        conn.commit()
        return {"status": "ok"}
    except psycopg2.errors.UniqueViolation:
        # CARD-0215's (ts, source) dedup case.
        conn.rollback()
        return {"status": "duplicate", "ts": ts.isoformat(), "source": source}
    except psycopg2.errors.CheckViolation as e:
        # CARD-0215's physical range-check case -- constraints are named
        # chk_<field> (init/schema.sql), so the violated field is recoverable
        # from the constraint name without re-validating in Python too.
        conn.rollback()
        field = (e.diag.constraint_name or "").removeprefix("chk_")
        return {"status": "rejected", "reason": "out_of_range", "field": field, "value": values.get(field)}
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}


def _row_to_json(row):
    """psycopg2 hands back real datetime objects for timestamptz columns --
    the old Sheets-backed export always returned ISO strings
    (environmental-data.gs's own `if (val instanceof Date) val =
    val.toISOString()`), so match that here rather than changing every
    downstream consumer's parsing."""
    out = {}
    for k, v in row.items():
        if isinstance(v, (datetime, date)):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


def _previous_key_active():
    return bool(API_KEY_PREVIOUS) and API_KEY_PREVIOUS_EXPIRES is not None \
        and datetime.now(timezone.utc) < API_KEY_PREVIOUS_EXPIRES


def _key_kind(provided):
    """'current', 'previous' (only inside its window), or None. Both comparisons
    are constant-time and both always run, so timing doesn't reveal which."""
    pb = provided.encode()
    is_current = bool(API_KEY) and hmac.compare_digest(pb, API_KEY.encode())
    is_previous = _previous_key_active() and hmac.compare_digest(pb, API_KEY_PREVIOUS.encode())
    if is_current:
        return "current"
    if is_previous:
        return "previous"
    return None


AUTH_LOG_INTERVAL_SEC = 300
_auth_last_logged = {}
# (path, kind) -> ISO time of the latest accepted request, in memory since
# start -- read back through GET /auth-status so a rotation runner can see that
# a manual holder (GPSLogger, Tasker) has moved to the new key without
# scraping logs.
_auth_seen = {}


def _note_auth(path, form, kind):
    _auth_seen[(path, kind)] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    # Only the two things worth a log line: a key in the query string (CARD-0365)
    # and the old key still in use (CARD-0372). Current key + header is the goal.
    if form == "query" or kind == "previous":
        now = time.monotonic()
        k = (path, form, kind)
        if now - _auth_last_logged.get(k, -AUTH_LOG_INTERVAL_SEC) >= AUTH_LOG_INTERVAL_SEC:
            _auth_last_logged[k] = now
            if kind == "previous":
                log(f"previous API key used on {path} via {form} (CARD-0372: this caller has not moved to the new key)")
            else:
                log(f"legacy ?key= auth used on {path} (CARD-0365: move this caller to an Authorization: Bearer header)")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # explicit logging below instead of the default per-request line

    def _authorized(self, parts):
        # CARD-0365: `Authorization: Bearer <key>` is the preferred form -- a
        # key in the query string lands in every access log between the
        # caller and here (Caddy's, Cloudflare's). `?key=` is still accepted
        # until every caller (GPSLogger, Tasker, Node-RED) has moved; each
        # legacy use is logged (rate-limited, never the key) so the day it
        # can be removed is visible rather than guessed.
        header = self.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            form, provided = "header", header[7:].strip()
        else:
            form, provided = "query", parse_qs(parts.query).get("key", [""])[0]
        kind = _key_kind(provided)
        if kind is None:
            return False
        _note_auth(parts.path, form, kind)
        return True

    def _respond(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # -- GET ------------------------------------------------------------

    def do_GET(self):
        parts = urlsplit(self.path)
        if parts.path == "/gps":
            self._handle_gps(parts)
            return
        if parts.path == "/lookup-gps":
            self._handle_lookup_gps(parts)
            return
        if parts.path == "/export":
            self._handle_export(parts)
            return
        if parts.path == "/health":
            self._handle_health(parts)
            return
        if parts.path == "/version":
            self._handle_version(parts)
            return
        if parts.path == "/auth-status":
            self._handle_auth_status(parts)
            return
        self._respond(404, {"status": "error", "message": "not found"})

    def _handle_gps(self, parts):
        if not self._authorized(parts):
            log("Rejected GPS GET: missing or incorrect key", err=True)
            self._respond(401, {"status": "error", "message": "unauthorized"})
            return

        qs = parse_qs(parts.query)

        def qf_strict(name):
            v = qs.get(name, [None])[0]
            return float(v) if v not in (None, "") else None

        def qf_lenient(name):
            # acc/alt/direction are optional AND tolerated-if-garbled --
            # environmental-data.gs's own action=gps used JS parseFloat(),
            # which returns NaN (not a thrown error) on a bad value, so a
            # malformed optional field never blocked the point from being
            # recorded. A strict float() here would (and once did, live --
            # a GPSLogger macro-name mismatch sent a garbled 'direction'
            # and got every point rejected outright, losing real GPS data
            # over one optional field). Match the old tolerance instead.
            v = qs.get(name, [None])[0]
            if v in (None, ""):
                return None
            try:
                return float(v)
            except (TypeError, ValueError):
                log(f"GPS GET: ignoring unparseable optional field {name}={v!r}", err=True)
                return None

        try:
            lat = qf_strict("lat")
            lon = qf_strict("lon")
        except ValueError as e:
            log(f"Rejected GPS GET: unparseable lat/lon ({e})", err=True)
            self._respond(400, {"status": "error", "message": f"unparseable lat/lon: {e}"})
            return
        acc = qf_lenient("acc")
        alt = qf_lenient("alt")
        direction = qf_lenient("direction")  # CARD-0085: not sent by every
        # GPSLogger config -- stays None rather than erroring when absent,
        # same tolerance environmental-data.gs's own action=gps had.

        ts_raw = qs.get("ts", [None])[0]
        if not ts_raw or lat is None or lon is None:
            log(f"Rejected GPS GET: missing required field (ts={ts_raw!r}, lat={lat!r}, lon={lon!r})", err=True)
            self._respond(400, {"status": "error", "message": "ts, lat, and lon are required"})
            return

        # %TIME from GPSLogger may be a Unix epoch integer (seconds or ms) or
        # an ISO date string depending on app version -- same robust parsing
        # environmental-data.gs's own action=gps used.
        try:
            if ts_raw.isdigit():
                n = int(ts_raw)
                ts = datetime.fromtimestamp(n if len(ts_raw) < 13 else n / 1000, tz=timezone.utc)
            else:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        except ValueError as e:
            log(f"Rejected GPS GET: unparseable ts ({ts_raw!r}): {e}", err=True)
            self._respond(400, {"status": "error", "message": f"unparseable ts: {e}"})
            return

        conn = _pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO gps_track (ts, lat, lon, accuracy_m, altitude_m, direction) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (ts, lat, lon, acc, alt, direction),
                )
            conn.commit()
            # CARD-0349 Phase 2: ported from environmental-data.gs's own
            # action=gps branch, which called _maybeCaptureHikeStartForecast
            # right after the real (non-duplicate) point was stored. Runs on
            # the same connection, after the GPS point's own commit -- a
            # forecast-capture failure must never affect the point already
            # safely stored.
            _maybe_capture_hike_start_forecast(conn, ts, lat, lon)
        except psycopg2.errors.UniqueViolation:
            # CARD-0243's dedup case -- GPSLogger retrying a slow/unconfirmed
            # response resubmits the same point. Same {"status": "duplicate"}
            # shape the old action=gps returned.
            conn.rollback()
            self._respond(200, {"status": "duplicate", "ts": ts.isoformat()})
            return
        except Exception as e:
            conn.rollback()
            log(f"GPS insert failed: {e}", err=True)
            self._respond(500, {"status": "error", "message": str(e)})
            return
        finally:
            _pool.putconn(conn)

        self._respond(200, {"status": "ok"})

    def _handle_lookup_gps(self, parts):
        if not self._authorized(parts):
            log("Rejected lookup-gps GET: missing or incorrect key", err=True)
            self._respond(401, {"status": "error", "message": "unauthorized"})
            return

        ts_raw = parse_qs(parts.query).get("ts", [None])[0]
        if not ts_raw:
            self._respond(400, {"status": "error", "message": "ts is required"})
            return
        try:
            target_ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        except ValueError as e:
            self._respond(400, {"status": "error", "message": f"unparseable ts: {e}"})
            return

        conn = _pool.getconn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Design doc section 4: nearest-neighbor by absolute time
                # distance. The hypertable's own time-partitioned index keeps
                # this fast without the throttling Node-RED currently needs
                # (CARD-0279) to protect a spreadsheet from bursty replay
                # traffic.
                #
                # The design doc's own SQL sketch omitted the old
                # _gpsLookup()'s 5-minute cutoff (environmental-data.gs) --
                # caught before Node-RED was ever pointed at this route
                # (2026-09-28): without it, a reading taken hours from any
                # real hike (e.g. hiking-monitor sitting at home overnight)
                # would silently match whatever GPS point happens to be
                # nearest in time, even a stale point from a previous hike,
                # geotagging it wrong instead of correctly returning no
                # match. WHERE bounds the candidate set to the same window
                # the old system used, not just the ORDER BY/LIMIT.
                cur.execute(
                    "SELECT lat, lon, accuracy_m FROM gps_track "
                    "WHERE abs(extract(epoch from (ts - %s))) <= 300 "
                    "ORDER BY abs(extract(epoch from (ts - %s))) LIMIT 1",
                    (target_ts, target_ts),
                )
                row = cur.fetchone()
        except Exception as e:
            log(f"lookup-gps failed: {e}", err=True)
            self._respond(500, {"status": "error", "message": str(e)})
            return
        finally:
            _pool.putconn(conn)

        if row is None:
            self._respond(200, {})
            return
        self._respond(200, _row_to_json(dict(row)))

    def _handle_export(self, parts):
        if not self._authorized(parts):
            log("Rejected export GET: missing or incorrect key", err=True)
            self._respond(401, {"status": "error", "message": "unauthorized"})
            return

        qs = parse_qs(parts.query)
        table = qs.get("table", [None])[0]
        if table not in EXPORT_TABLES:
            self._respond(400, {"status": "error", "message": f"table must be one of {EXPORT_TABLES}"})
            return

        start_raw = qs.get("start", [None])[0]
        end_raw = qs.get("end", [None])[0]
        try:
            start = datetime.fromisoformat(start_raw.replace("Z", "+00:00")) if start_raw else None
            end = datetime.fromisoformat(end_raw.replace("Z", "+00:00")) if end_raw else None
        except ValueError as e:
            self._respond(400, {"status": "error", "message": f"unparseable start/end: {e}"})
            return

        query = psycopg2.sql.SQL("SELECT * FROM {table} WHERE 1=1").format(
            table=psycopg2.sql.Identifier(table)
        )
        params = []
        if start is not None:
            query += psycopg2.sql.SQL(" AND ts >= %s")
            params.append(start)
        if end is not None:
            query += psycopg2.sql.SQL(" AND ts <= %s")
            params.append(end)
        query += psycopg2.sql.SQL(" ORDER BY ts")

        conn = _pool.getconn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                rows = [_row_to_json(dict(r)) for r in cur.fetchall()]
        except Exception as e:
            log(f"export failed (table={table}): {e}", err=True)
            self._respond(500, {"status": "error", "message": str(e)})
            return
        finally:
            _pool.putconn(conn)

        self._respond(200, {"status": "ok", "table": table, "count": len(rows), "rows": rows})

    def _handle_health(self, parts):
        # CARD-0338's early-warning probe, ported: a real SELECT against the
        # DB, not a bare "process is up" check -- the same thing
        # sheet_health.py currently calls against environmental-data.gs's
        # own action=health.
        if not self._authorized(parts):
            self._respond(401, {"status": "error", "message": "unauthorized"})
            return
        start = datetime.now(timezone.utc)
        conn = None
        try:
            conn = _pool.getconn()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        except Exception as e:
            log(f"Health check failed: {e}", err=True)
            self._respond(500, {"status": "error", "message": str(e), "version": VERSION})
            return
        finally:
            if conn is not None:
                _pool.putconn(conn)
        ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
        self._respond(200, {"status": "ok", "ms": ms, "version": VERSION})

    def _handle_version(self, parts):
        if not self._authorized(parts):
            self._respond(401, {"status": "error", "message": "unauthorized"})
            return
        self._respond(200, {"status": "ok", "version": VERSION})

    def _handle_auth_status(self, parts):
        # CARD-0372: read-only view of the rotation window and of which paths
        # have recently authenticated with which key -- what a rotation runner
        # polls to know a manual holder has moved. Never returns a key.
        if not self._authorized(parts):
            self._respond(401, {"status": "error", "message": "unauthorized"})
            return
        seen = {}
        for (path, kind), ts in _auth_seen.items():
            seen.setdefault(path, {})[kind] = ts
        self._respond(200, {
            "status": "ok",
            "version": VERSION,
            "previous_key_configured": bool(API_KEY_PREVIOUS),
            "previous_key_active": _previous_key_active(),
            "previous_key_expires": API_KEY_PREVIOUS_EXPIRES.isoformat(timespec="seconds") if API_KEY_PREVIOUS_EXPIRES else None,
            "last_seen": seen,
        })

    # -- POST -------------------------------------------------------------

    def do_POST(self):
        parts = urlsplit(self.path)
        if parts.path == "/environmental-data":
            self._handle_environmental_data(parts)
            return
        if parts.path == "/environmental-data-bulk":
            self._handle_environmental_data_bulk(parts)
            return
        if parts.path == "/wildlife-detection":
            self._handle_wildlife_detection(parts)
            return
        if parts.path == "/hiking-observations":
            self._handle_hiking_observations(parts)
            return
        if parts.path == "/hike-izer-cost":
            self._handle_hike_izer_cost(parts)
            return
        self._respond(404, {"status": "error", "message": "not found"})

    def _handle_hike_izer_cost(self, parts):
        """CARD-0349 follow-on, 2026-09-29 -- replaces environmental-data.gs's
        hike-izer-cost doPost branch, the last component still on the old
        Apps Script. Dedup is intentionally NOT (file_stem, run_type) alone
        -- see init/schema.sql's own comment on the UNIQUE constraint this
        relies on: a legitimate second run on the same hike gets its own
        row unless every cost field also matches exactly."""
        if not self._authorized(parts):
            log("Rejected hike-izer-cost POST: missing or incorrect key", err=True)
            self._respond(401, {"status": "error", "message": "unauthorized"})
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            log(f"Rejected hike-izer-cost POST: invalid JSON body ({raw!r})", err=True)
            self._respond(400, {"status": "error", "message": "invalid JSON"})
            return

        ts_raw = payload.get("ts")
        file_stem = payload.get("file_stem")
        run_type = payload.get("run_type")
        if not ts_raw or not file_stem or not run_type:
            log(f"Rejected hike-izer-cost POST: missing required field (payload={payload!r})", err=True)
            self._respond(400, {"status": "error", "message": "ts, file_stem, and run_type are required"})
            return
        try:
            ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
        except ValueError as e:
            self._respond(400, {"status": "error", "message": f"unparseable ts: {e}"})
            return

        conn = _pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO hike_izer_cost "
                    "(ts, file_stem, run_type, dollars, calls, input_tokens, output_tokens, web_searches) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        ts, file_stem, run_type, payload.get("dollars"), payload.get("calls"),
                        payload.get("input_tokens"), payload.get("output_tokens"), payload.get("web_searches"),
                    ),
                )
            conn.commit()
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            self._respond(200, {"status": "duplicate", "file_stem": file_stem, "run_type": run_type})
            return
        except Exception as e:
            conn.rollback()
            log(f"hike_izer_cost insert failed: {e}", err=True)
            self._respond(500, {"status": "error", "message": str(e)})
            return
        finally:
            _pool.putconn(conn)

        _relay_log("hike-izer-cost", "System", f"Logged hike-izer generation cost for {file_stem} ({run_type}).")
        self._respond(200, {"status": "ok"})

    def _handle_hiking_observations(self, parts):
        """CARD-0349 Phase 2 -- replaces environmental-data.gs's
        hiking-observations doPost branch. Staged, not yet the live target:
        Tasker's "Flush Observation Queue" task still POSTs to the old
        Apps Script until that phone-side URL is switched (a real device
        config change, not something built here)."""
        if not self._authorized(parts):
            log("Rejected hiking-observations POST: missing or incorrect key", err=True)
            self._respond(401, {"status": "error", "message": "unauthorized"})
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            log(f"Rejected hiking-observations POST: invalid JSON body ({raw!r})", err=True)
            self._respond(400, {"status": "error", "message": "invalid JSON"})
            return

        # Tasker's actual payload also carries lat/lon/categories (always
        # null/[] -- this pipeline has never attached a GPS fix at the
        # speaking moment, per observations-pipeline.md) and source
        # ("voice") -- environmental-data.gs's own doPost ignored all of
        # those client-sent fields and computed categories/GPS server-side;
        # matched here, not just carried through blindly.
        obs_text = str(payload.get("observation") or "").strip()
        ts_raw = payload.get("ts")
        if not obs_text or not ts_raw:
            log(f"Rejected hiking-observations POST: missing observation/ts (payload={payload!r})", err=True)
            self._respond(400, {"status": "error", "message": "observation and ts are required"})
            return

        # %TIMES (Tasker's own epoch-seconds variable) or an ISO string --
        # same tolerant parsing as the GPS/environmental-data routes.
        try:
            ts_str = str(ts_raw)
            if ts_str.isdigit():
                ts = datetime.fromtimestamp(int(ts_str), tz=timezone.utc)
            else:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError as e:
            self._respond(400, {"status": "error", "message": f"unparseable ts: {e}"})
            return

        categories = _categorize_observation(obs_text)
        source = payload.get("source") or "voice"

        conn = _pool.getconn()
        try:
            lat, lon = _gps_lookup(conn, ts)
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO hiking_observations (ts, observation, categories, source, lat, lon) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (ts, obs_text, categories, source, lat, lon),
                )
            conn.commit()
        except psycopg2.errors.UniqueViolation:
            # CARD-0244's dedup case, ported -- Hiking Observations has
            # exactly one producer (Tasker's own flush loop), so ts alone
            # is a sufficient key, same as GPS Track.
            conn.rollback()
            self._respond(200, {"status": "duplicate", "ts": ts.isoformat()})
            return
        except Exception as e:
            conn.rollback()
            log(f"hiking_observations insert failed: {e}", err=True)
            self._respond(500, {"status": "error", "message": str(e)})
            return
        finally:
            _pool.putconn(conn)

        _relay_log("hiking-observations", "System", "Logged hiking observation.")
        self._respond(200, {"status": "ok"})

    def _handle_wildlife_detection(self, parts):
        """CARD-0349 Phase 2 -- replaces environmental-data.gs's
        wildlife-detection doPost branch. scat-detection deliberately has no
        equivalent route here -- retired before this migration, not ported."""
        if not self._authorized(parts):
            log("Rejected wildlife-detection POST: missing or incorrect key", err=True)
            self._respond(401, {"status": "error", "message": "unauthorized"})
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            log(f"Rejected wildlife-detection POST: invalid JSON body ({raw!r})", err=True)
            self._respond(400, {"status": "error", "message": "invalid JSON"})
            return

        ts_raw = payload.get("ts")
        hike_file_stem = payload.get("hike_file_stem")
        scientific_name = payload.get("scientific_name")
        if not ts_raw or not hike_file_stem or not scientific_name:
            log(f"Rejected wildlife-detection POST: missing required field (payload={payload!r})", err=True)
            self._respond(400, {"status": "error", "message": "ts, hike_file_stem, and scientific_name are required"})
            return
        try:
            ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
        except ValueError as e:
            self._respond(400, {"status": "error", "message": f"unparseable ts: {e}"})
            return

        conn = _pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO wildlife_detections "
                    "(ts, hike_file_stem, common_name, scientific_name, count, best_confidence, lat, lon) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        ts, hike_file_stem, payload.get("common_name"), scientific_name,
                        payload.get("count"), payload.get("best_confidence"),
                        payload.get("lat"), payload.get("lon"),
                    ),
                )
            conn.commit()
        except psycopg2.errors.UniqueViolation:
            # CARD-0276's own dedup case, ported -- (hike_file_stem,
            # scientific_name) identity dedup, first write wins. A retried
            # POST of an already-committed detection is "duplicate", not an
            # overwrite -- same shape generation.py's caller already treats
            # as success, no client-side change needed for this part.
            conn.rollback()
            self._respond(200, {"status": "duplicate", "hike_file_stem": hike_file_stem, "scientific_name": scientific_name})
            return
        except Exception as e:
            conn.rollback()
            log(f"wildlife_detections insert failed: {e}", err=True)
            self._respond(500, {"status": "error", "message": str(e)})
            return
        finally:
            _pool.putconn(conn)

        _relay_log("wildlife-detection", "System", f"Logged wildlife detection for {hike_file_stem}: {payload.get('common_name')}.")
        self._respond(200, {"status": "ok"})

    def _handle_environmental_data(self, parts):
        if not self._authorized(parts):
            log("Rejected environmental-data POST: missing or incorrect key", err=True)
            self._respond(401, {"status": "error", "message": "unauthorized"})
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            log(f"Rejected environmental-data POST: invalid JSON body ({raw!r})", err=True)
            self._respond(400, {"status": "error", "message": "invalid JSON"})
            return

        ts_raw = payload.get("ts")
        source = payload.get("source")
        if not ts_raw or not source:
            log(f"Rejected environmental-data POST: missing ts/source (payload={payload!r})", err=True)
            self._respond(400, {"status": "error", "message": "ts and source are required"})
            return
        try:
            ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
        except ValueError as e:
            self._respond(400, {"status": "error", "message": f"unparseable ts: {e}"})
            return

        try:
            values = {f: _coerce(payload, f) for f in ENV_OPTIONAL_FIELDS}
        except _BadField as e:
            log(f"Rejected environmental-data POST: {e}", err=True)
            self._respond(400, {"status": "error", "message": str(e)})
            return

        conn = _pool.getconn()
        try:
            # CARD-0377: fill lat/lon from the GPS track when the caller didn't
            # supply them, in-process -- the same lookup Node-RED's live flow
            # already does over its own HTTP round-trip (_handle_lookup_gps),
            # just called directly here so a caller with no GPS of its own
            # (e.g. AQM, which always sends null) doesn't need a relay hop.
            if values.get("lat") is None and values.get("lon") is None:
                values["lat"], values["lon"] = _gps_lookup(conn, ts)
            result = _insert_env_row(conn, ts, source, values)
        finally:
            _pool.putconn(conn)

        if result["status"] == "error":
            log(f"environmental_data insert failed: {result['message']}", err=True)
            self._respond(500, result)
            return
        self._respond(200, result)

    def _handle_environmental_data_bulk(self, parts):
        """CARD-0377: AQM's bulk catch-up upload -- one request replaces what
        used to be N individual MQTT publishes from the device. Also resolves
        CARD-0343's "ts: null, uptime_s, boot" buffered-reading shape
        server-side (ported from the ESP32 C++ in air-quality-monitor.yaml's
        attempt_aqm_replay), since the whole point of this endpoint is to let
        the device forward its raw log lines unmodified rather than doing
        per-reading math itself."""
        if not self._authorized(parts):
            log("Rejected environmental-data-bulk POST: missing or incorrect key", err=True)
            self._respond(401, {"status": "error", "message": "unauthorized"})
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            log(f"Rejected environmental-data-bulk POST: invalid JSON body ({raw!r})", err=True)
            self._respond(400, {"status": "error", "message": "invalid JSON"})
            return

        readings = payload.get("readings")
        if not isinstance(readings, list):
            self._respond(400, {"status": "error", "message": "readings must be a list"})
            return
        # CARD-0377 Phase 3: optional -- older firmware/synthetic test batches
        # won't carry this key at all, which is fine, just no session summary.
        boot_events = payload.get("boot_events")
        if not isinstance(boot_events, list):
            boot_events = []

        current_time_raw = payload.get("current_time")
        current_boot = payload.get("current_boot")
        current_uptime_s = payload.get("current_uptime_s")
        current_time = None
        if current_time_raw:
            try:
                current_time = datetime.fromisoformat(str(current_time_raw).replace("Z", "+00:00"))
            except ValueError:
                current_time = None

        counts = {"inserted": 0, "duplicate": 0, "rejected": 0, "unresolved": 0, "invalid": 0}
        inserted_rows = []  # CARD-0377 Phase 3: (ts, battery_v) for each row actually inserted this request
        conn = _pool.getconn()
        try:
            for reading in readings:
                if not isinstance(reading, dict):
                    counts["invalid"] += 1
                    continue
                # Device's own raw log lines use "component", not "source" --
                # accept either so the device can forward its SPIFFS lines
                # byte-for-byte, with no field-renaming step of its own.
                source = reading.get("source") or reading.get("component")
                ts_raw = reading.get("ts")
                ts = None
                if ts_raw:
                    try:
                        ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
                    except ValueError:
                        ts = None
                elif reading.get("uptime_s") is not None and reading.get("boot"):
                    # CARD-0343's resolution: only solvable if this reading is
                    # from the SAME boot the device is in right now, and that
                    # boot has already reached at least as much uptime as the
                    # reading was taken at.
                    if (current_time is not None and current_boot and current_uptime_s is not None
                            and reading["boot"] == current_boot
                            and current_uptime_s >= reading["uptime_s"]):
                        ts = current_time - timedelta(seconds=(current_uptime_s - reading["uptime_s"]))
                if not source:
                    counts["invalid"] += 1
                    continue
                if ts is None:
                    counts["unresolved"] += 1
                    log(f"environmental-data-bulk: unresolved reading kept out (source={source}, "
                        f"boot={reading.get('boot')}, uptime_s={reading.get('uptime_s')})")
                    continue
                try:
                    values = {f: _coerce(reading, f) for f in ENV_OPTIONAL_FIELDS}
                except _BadField:
                    counts["invalid"] += 1
                    continue
                if values.get("lat") is None and values.get("lon") is None:
                    values["lat"], values["lon"] = _gps_lookup(conn, ts)
                result = _insert_env_row(conn, ts, source, values)
                if result["status"] == "ok":
                    counts["inserted"] += 1
                    inserted_rows.append((ts, values.get("battery_v")))
                elif result["status"] == "duplicate":
                    counts["duplicate"] += 1
                elif result["status"] == "rejected":
                    counts["rejected"] += 1
                else:
                    counts["invalid"] += 1
            boot_events_inserted = _insert_boot_events(conn, "air-quality-monitor", boot_events)
        finally:
            _pool.putconn(conn)

        log(f"environmental-data-bulk: {len(readings)} readings -> {counts}")
        _relay_log("air-quality-monitor", "System",
                   f"Bulk upload: {counts['inserted']} inserted, {counts['duplicate']} duplicate, "
                   f"{counts['rejected']} rejected, {counts['unresolved']} unresolved, {counts['invalid']} invalid "
                   f"(of {len(readings)} total)")

        # CARD-0377 Phase 3: "did the last session go well" -- the question a
        # heartbeat used to answer badly (it could only report "reachable
        # right now", which is never true mid-hike). Computed from the rows
        # just inserted plus the boot events this same upload carried, not
        # from any new device-side state.
        if inserted_rows:
            inserted_rows.sort(key=lambda r: r[0])
            session_start = inserted_rows[0][0]
            session_end = inserted_rows[-1][0]
            duration_s = (session_end - session_start).total_seconds()
            # Readings land every 2 min -- the first and last are both real
            # samples, so a span of N intervals holds N+1 readings.
            expected = int(duration_s / 120) + 1 if duration_s > 0 else 1
            actual = len(inserted_rows)
            pct = int(round(100 * actual / expected)) if expected else 100
            batt_first = inserted_rows[0][1]
            batt_last = inserted_rows[-1][1]
            batt_str = ""
            if batt_first is not None and batt_last is not None:
                batt_str = f", battery {batt_first:.2f}V -> {batt_last:.2f}V ({batt_last - batt_first:+.2f}V)"
            # Reset count from THIS upload's own boot_events list, not the
            # dedup-aware DB insert count -- a retried upload re-sending the
            # same boots should still describe the same session the same way.
            reset_count = max(0, len(boot_events) - 1)
            h = int(duration_s // 3600)
            m = int((duration_s % 3600) // 60)
            _relay_log("air-quality-monitor", "System",
                       f"Session complete: {h}h{m:02d}m, {actual}/{expected} readings ({pct}%)"
                       f"{batt_str}, {reset_count} reset{'s' if reset_count != 1 else ''} "
                       f"({boot_events_inserted} new boot event{'s' if boot_events_inserted != 1 else ''} recorded)")

        self._respond(200, {"status": "ok", **counts, "total": len(readings)})


def main():
    global _pool
    if not API_KEY:
        log("FATAL: API_KEY not set -- refusing to start", err=True)
        sys.exit(1)
    if not DB_PASSWORD:
        log("FATAL: DB_PASSWORD not set -- refusing to start", err=True)
        sys.exit(1)

    if API_KEY_PREVIOUS:
        if API_KEY_PREVIOUS_EXPIRES is None:
            log("WARNING: API_KEY_PREVIOUS is set but API_KEY_PREVIOUS_EXPIRES is missing/unparseable -- previous key IGNORED", err=True)
        elif not _previous_key_active():
            log(f"NOTE: API_KEY_PREVIOUS expired at {API_KEY_PREVIOUS_EXPIRES.isoformat(timespec='seconds')} -- ignored; remove it from .env")
        else:
            log(f"Previous API key accepted until {API_KEY_PREVIOUS_EXPIRES.isoformat(timespec='seconds')} (CARD-0372 rotation window)")

    log(f"Connecting to Postgres at {DB_HOST}...")
    _pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=1, maxconn=10,
        host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
    )

    log(f"Starting data-pipeline-api on :{PORT} (version {VERSION})")
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
