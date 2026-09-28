# Design: Phase 1 (Environmental Data + GPS Track) -- TimescaleDB migration

**Tracking card:** CARD-0349. **Depends on:** `timescaledb-migration-plan.md` (Planning). This document
resolves that plan's "open questions for Design" and is specific enough for Build to execute against.
Scoped to Phase 1 only (Environmental Data + GPS Track) -- Phase 2 (the other three tables) gets its
own Design pass once Phase 1 is live and proven, per this project's own iterative/incremental
discipline (don't design what isn't being built next).

---

## 1. Where it runs

New Docker Compose project on the M8: `~/data-pipeline-app/`, matching the existing
`~/hike-izer-web-app/` naming convention. Two services:

```yaml
# ~/data-pipeline-app/docker-compose.yml
services:
  timescaledb:
    image: timescale/timescaledb:latest-pg16
    restart: unless-stopped
    environment:
      POSTGRES_DB: jctsh
      POSTGRES_USER: jctsh
      POSTGRES_PASSWORD_FILE: /run/secrets/pg_password   # or an env file, matching credentials.local.md's existing pattern
    volumes:
      - ./pgdata:/var/lib/postgresql/data
      - ./init:/docker-entrypoint-initdb.d:ro   # schema.sql runs once, on first container start
    # Not published to the host/LAN -- only the gateway service (below) needs to reach it,
    # over this compose project's own default Docker network, same pattern hike-izer-web-app
    # uses between `web`/`orchestrator`.

  data-pipeline-api:
    build: ./api
    restart: unless-stopped
    depends_on: [timescaledb]
    environment:
      DB_HOST: timescaledb
      DB_NAME: jctsh
      DB_USER: jctsh
      DB_PASSWORD_FILE: /run/secrets/pg_password
      API_KEY: ${API_KEY}          # same shared-secret pattern as today's Apps Script
    ports:
      - "127.0.0.1:8091:8080"      # local-only, matching hike-izer-web's own 127.0.0.1:8090 debug-port pattern
```

**Exposure:** reuse the Cloudflare Tunnel + Caddy already running for `hike-izer-web-app` rather than
provisioning a second tunnel/domain for a personal project with one public-facing host. Add one more
route to that project's existing Caddyfile (`data.jctnet.com` or a path under the existing domain --
Joseph's call in Build, matching whichever is less disruptive to GPSLogger's/Tasker's existing
saved-URL configs) pointing at `data-pipeline-api:8080` over the two compose projects' shared network
(same mechanism `hike-izer-web`'s own `orchestrator` service already uses to be reachable via Caddy's
`/webhook/*` route -- Docker Compose supports one container joining a second project's network by
name).

## 2. Schema (finalized from the Planning doc's sketch)

```sql
-- ~/data-pipeline-app/init/schema.sql -- runs once, automatically, on first container start.

CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE environmental_data (
  ts              timestamptz NOT NULL,
  source          text        NOT NULL,
  lat             double precision,
  lon             double precision,
  temp_f          double precision,
  humidity_pct    double precision,
  pressure_hpa    double precision,
  dew_point_f     double precision,
  heat_index_f    double precision,
  uv_index        double precision,
  irradiance_wm2  double precision,
  wind_speed_mph  double precision,
  wind_dir_deg    double precision,
  rain_tips       integer,
  rainin          double precision,
  dailyrainin     double precision,
  battery_v       double precision,
  rssi_dbm        integer,
  pm1_ug_m3       double precision,
  pm25_ug_m3      double precision,
  pm4_ug_m3       double precision,
  pm10_ug_m3      double precision,
  voc_index       double precision,
  nox_index       double precision,
  illuminance_lx  double precision,
  solar_v         double precision,
  PRIMARY KEY (ts, source)
);
SELECT create_hypertable('environmental_data', 'ts');
-- Added beyond the Planning sketch: an index on source alone, for queries scoped to one
-- sensor across a wide date range (e.g. "all hiking-monitor readings this month") that
-- don't want to scan every source's rows in a chunk.
CREATE INDEX idx_environmental_data_source ON environmental_data (source, ts DESC);

-- Ingest guards (CARD-0215's physical range checks), enforced by the database itself now,
-- not application code that has to remember to call them:
ALTER TABLE environmental_data ADD CONSTRAINT chk_temp_f CHECK (temp_f IS NULL OR temp_f BETWEEN -20 AND 130);
ALTER TABLE environmental_data ADD CONSTRAINT chk_humidity CHECK (humidity_pct IS NULL OR humidity_pct BETWEEN 0 AND 100);
ALTER TABLE environmental_data ADD CONSTRAINT chk_pressure CHECK (pressure_hpa IS NULL OR pressure_hpa BETWEEN 800 AND 1100);
ALTER TABLE environmental_data ADD CONSTRAINT chk_uv CHECK (uv_index IS NULL OR uv_index BETWEEN 0 AND 20);

CREATE TABLE gps_track (
  ts          timestamptz PRIMARY KEY,
  lat         double precision NOT NULL,
  lon         double precision NOT NULL,
  accuracy_m  double precision,
  altitude_m  double precision,
  bearing_deg double precision
);
SELECT create_hypertable('gps_track', 'ts');
```

**Why `PRIMARY KEY` alone replaces CARD-0215/CARD-0243's manual dedup scans:** a duplicate `INSERT`
now fails the constraint instead of needing a full-column read-and-compare first; the gateway catches
that specific error and returns the same `{"status": "duplicate"}` shape Node-RED/GPSLogger/Tasker
already expect, so their own retry-tolerant behavior needs no change.

## 3. API (replaces `environmental-data.gs` entirely)

Explicit per-purpose routes instead of one `doPost` keyed on a hidden `component` string -- the one
real redesign choice here, per Joseph's decision to redesign rather than preserve the old shape.
GPS ingest stays a `GET` with query-string parameters: GPSLogger's own "custom URL" logging feature
only supports templated `GET` URLs, a real device/app constraint, not a design choice.

| Method | Path | Replaces | Caller |
|---|---|---|---|
| `POST /environmental-data?key=` | `doPost` (default branch) | Node-RED | Body: today's same JSON payload shape (`component`, `ts`, `lat`, `lon`, sensor fields) -- kept as-is, only the URL and routing change |
| `GET /gps?key=&lat=&lon=&acc=&alt=&direction=&ts=` | `?action=gps` | GPSLogger (phone) | Same query-string shape as today, so the phone's saved custom-URL template only needs its base URL changed |
| `GET /export?key=&table=environmental_data\|gps_track&start=&end=` | `?action=export` | `fetch_hike_data.py` (rewritten in Build) | `table` names an actual table, not a spreadsheet tab; returns a native JSON array, not Sheets' string-typed cell values |
| `GET /lookup-gps?key=&ts=` | `?action=lookup` | Node-RED's GPS correlation | Server does the nearest-neighbor SQL query (section 4) instead of Node-RED throttling calls to protect a spreadsheet |
| `GET /health?key=` | `?action=health` | `sheet_health.py` (rewritten in Build) | A real `SELECT 1` against the DB -- a connection failure or query timeout is the real, meaningful signal now, not "did opening a spreadsheet document hang" |
| `GET /version?key=` | `?action=version` | Manual deploy verification | A `VERSION` constant in the gateway's own source, same fingerprint-on-deploy convention as `SCRIPT_VERSION` |

**Handler shape matches `hike-izer-orchestrator/app.py`'s existing convention** (investigate existing
patterns first, don't invent a new house style for one more Python HTTP service on the same host):
stdlib `http.server.BaseHTTPRequestHandler` / `ThreadingHTTPServer`, a shared `_authorized(parts)`
check against `?key=`, and a `_respond(status, dict)` helper returning JSON -- not a new framework
dependency (Flask/FastAPI) for a single-purpose internal service this small.

**New Python dependency, unavoidable:** `psycopg2-binary`, for Postgres connectivity -- the one real
addition to this host's existing Python stack (`anthropic`/`paho-mqtt` are already pip dependencies
for the sibling `hike-izer-orchestrator` service, so one more well-known, widely-used library matches
the existing bar, not a new category of risk).

## 4. GPS correlation

Replaces both `?action=lookup` (Node-RED's per-reading call) and the derived-field back-fill:

```sql
SELECT lat, lon, accuracy_m
FROM gps_track
ORDER BY abs(extract(epoch from (ts - %(target_ts)s)))
LIMIT 1;
```

The hypertable's own time-partitioned index keeps this fast without the throttling Node-RED currently
needs (CARD-0279) to protect a spreadsheet from bursty replay traffic -- a real Postgres query under
concurrent load doesn't have Apps Script's per-call ceiling. Node-RED's existing throttle node can
likely be removed in Build once this is confirmed live; not assumed here.

## 5. Migration / backfill script

A one-time Python script (`core/data-pipeline/migrate_to_timescale.py`, run by hand during Build, not
part of the deployed gateway):

1. Calls the **current, still-live** `?action=export&full=1` for `Environmental Data` and `GPS Track`.
2. Transforms each row: Sheets' timestamp strings -> `timestamptz`, blank cells -> `NULL`.
3. Bulk-loads via `psycopg2`'s `execute_values` (or `COPY FROM STDIN` if row count makes that
   meaningfully faster -- decide in Build against the real ~33k-row count at migration time).
4. Verification step, mandatory before cutover (Note on Build, `JCTsh-Operating-System.md`: live
   verification beats inferred confidence): row counts match source; a real recent hike's
   `fetch_hike_data.py` output (rewritten against the new `/export`) reproduces the same
   stats/coverage numbers as its current Sheets-backed output for the same date range -- same
   before/after comparison pattern CARD-0311/CARD-0348 already used successfully.

## 6. Cutover sequence (one producer at a time, per the Plan's own decision)

1. Deploy `timescaledb` + `data-pipeline-api` on the M8; run the migration script; verify (section 5).
   No live traffic yet -- old spreadsheet and Apps Script keep running unchanged.
2. Point Node-RED's `environmental-data.flow.json` at the new `/environmental-data` and `/lookup-gps`
   routes. Verify a real sensor's next reading lands correctly (check via `/export` or a direct
   `psql` query), then verify the old Sheet has stopped receiving new rows from this source.
3. Point GPSLogger's custom-URL template at `/gps` on the new host. Verify on the next real hike
   (or a manual test fix) before relying on it for a real hike.
4. Point `fetch_hike_data.py` (both the interactive Skill's manual flow and
   `hike-izer-orchestrator`'s `generate()`) at the new `/export`. Verify against a real hike, same
   before/after comparison as step 1's migration check.
5. Point `sheet_health.py`/`run_daily_refresh_and_log()`'s pre-flight check at `/health`.
6. Once all of the above are live and stable for a real stretch of use (Joseph's own call on how
   long is enough -- not fixed here), retire the old spreadsheet and Apps Script deployment per the
   Plan's "retire once verified" decision. Not deleted immediately on the day everything's pointed at
   the new system.

## 7. Backup

The M8 has no existing general backup story to extend cleanly (photo-server's own backup drives are
specific to Immich's asset library, not a host-wide pattern). For Phase 1: a `pg_dump` to a local
file on a schedule, via a systemd timer matching the existing `hike-izer-daily-refresh.timer`
pattern already proven on this host -- daily, retaining some number of recent dumps (exact retention
a Build detail, not fixed here). **Explicitly an accepted limitation for Phase 1, not a gap silently
left unaddressed:** this covers "the container/data directory got corrupted," not "the M8 itself is
lost" -- true off-host backup (an equivalent to photo-server's own external-drive mirrors) is real
future work, not blocking Phase 1's own goals (this migration's whole point is fixing a
document-level Google-side failure mode, which a local dump already fully addresses).

## 8. `Correlation Debug`

Dropped, not carried forward as a stored table. Its diagnostic value (how closely a reading matched
a GPS fix) is fully covered by the gateway's own container logs (`docker logs data-pipeline-api`) --
one more log line per correlation, same visibility, no extra table to maintain.

## 9. Related

`timescaledb-migration-plan.md` (Planning, the document this resolves), CARD-0349 (tracking card),
`components/hike-izer-orchestrator/app.py` (the HTTP-handler convention this matches),
`core/data-pipeline/environmental-data.gs`/`environmental-data.flow.json` (what's being replaced).
