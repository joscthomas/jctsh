#!/usr/bin/env python
"""
data-pipeline-api -- CARD-0349 Phase 1. Replaces
core/data-pipeline/environmental-data.gs for Environmental Data + GPS Track
only (Phase 2 covers Hiking Observations/Wildlife Detections/Hike Start
Forecast, not built yet). Design doc: core/data-pipeline/timescaledb-design.md.

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
from datetime import datetime, date, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs

import psycopg2
import psycopg2.errors
import psycopg2.extras
import psycopg2.pool
import psycopg2.sql

VERSION = "2026-09-28.1"  # action=version fingerprint, same "confirm a
# redeploy actually landed" convention as environmental-data.gs's own
# SCRIPT_VERSION.

API_KEY = os.environ.get("API_KEY", "")
PORT = int(os.environ.get("PORT", "8080"))
DB_HOST = os.environ.get("DB_HOST", "timescaledb")
DB_NAME = os.environ.get("DB_NAME", "jctsh")
DB_USER = os.environ.get("DB_USER", "jctsh")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")

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

EXPORT_TABLES = ("environmental_data", "gps_track")

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


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # explicit logging below instead of the default per-request line

    def _authorized(self, parts):
        provided_key = parse_qs(parts.query).get("key", [""])[0]
        return bool(API_KEY) and hmac.compare_digest(provided_key, API_KEY)

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
        self._respond(404, {"status": "error", "message": "not found"})

    def _handle_gps(self, parts):
        if not self._authorized(parts):
            log("Rejected GPS GET: missing or incorrect key", err=True)
            self._respond(401, {"status": "error", "message": "unauthorized"})
            return

        qs = parse_qs(parts.query)

        def qf(name):
            v = qs.get(name, [None])[0]
            return float(v) if v not in (None, "") else None

        try:
            lat = qf("lat")
            lon = qf("lon")
            acc = qf("acc")
            alt = qf("alt")
            direction = qf("direction")  # CARD-0085: not sent by every
            # GPSLogger config -- stays None rather than erroring when absent,
            # same tolerance environmental-data.gs's own action=gps had.
        except ValueError as e:
            log(f"Rejected GPS GET: unparseable numeric field ({e})", err=True)
            self._respond(400, {"status": "error", "message": f"unparseable numeric field: {e}"})
            return

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
                cur.execute(
                    "SELECT lat, lon, accuracy_m FROM gps_track "
                    "ORDER BY abs(extract(epoch from (ts - %s))) LIMIT 1",
                    (target_ts,),
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

    # -- POST -------------------------------------------------------------

    def do_POST(self):
        parts = urlsplit(self.path)
        if parts.path == "/environmental-data":
            self._handle_environmental_data(parts)
            return
        self._respond(404, {"status": "error", "message": "not found"})

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

        columns = ["ts", "source"] + list(ENV_OPTIONAL_FIELDS)
        row_values = [ts, source] + [values[f] for f in ENV_OPTIONAL_FIELDS]

        conn = _pool.getconn()
        try:
            query = psycopg2.sql.SQL("INSERT INTO environmental_data ({cols}) VALUES ({vals})").format(
                cols=psycopg2.sql.SQL(", ").join(map(psycopg2.sql.Identifier, columns)),
                vals=psycopg2.sql.SQL(", ").join([psycopg2.sql.Placeholder()] * len(columns)),
            )
            with conn.cursor() as cur:
                cur.execute(query, row_values)
            conn.commit()
        except psycopg2.errors.UniqueViolation:
            # CARD-0215's (ts, source) dedup case. Same {"status":
            # "duplicate"} shape the old doPost returned, so Node-RED's
            # existing retry-tolerant handling needs no change.
            conn.rollback()
            self._respond(200, {"status": "duplicate", "ts": ts.isoformat(), "source": source})
            return
        except psycopg2.errors.CheckViolation as e:
            # CARD-0215's physical range-check case, now a DB constraint
            # instead of application code -- constraints are named chk_<field>
            # (init/schema.sql), so the violated field is recoverable from the
            # constraint name without re-validating in Python too.
            conn.rollback()
            field = (e.diag.constraint_name or "").removeprefix("chk_")
            self._respond(200, {"status": "rejected", "reason": "out_of_range", "field": field, "value": payload.get(field)})
            return
        except Exception as e:
            conn.rollback()
            log(f"environmental_data insert failed: {e}", err=True)
            self._respond(500, {"status": "error", "message": str(e)})
            return
        finally:
            _pool.putconn(conn)

        self._respond(200, {"status": "ok"})


def main():
    global _pool
    if not API_KEY:
        log("FATAL: API_KEY not set -- refusing to start", err=True)
        sys.exit(1)
    if not DB_PASSWORD:
        log("FATAL: DB_PASSWORD not set -- refusing to start", err=True)
        sys.exit(1)

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
