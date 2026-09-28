# Migrating the Environmental Data pipeline off Google Sheets to TimescaleDB

**Tracking card:** CARD-0349. **Status:** Planning. Decided so far (Joseph, 2026-09-27): technology is
TimescaleDB; it runs on the M8; Google Sheets is retired once migration is verified, not kept as a
synced mirror; the HTTP API in front of it is redesigned as part of this, not preserved as-is.
Scope covers all 5 sheets, built in two phases — Phase 1 (Environmental Data + GPS Track) first,
Phase 2 (Hiking Observations, Wildlife Detections, Hike Start Forecast) once Phase 1 is proven live.

This document is the planning artifact CARD-0349's own Planning → Design trigger needs
(`JCTsh-Operating-System.md`). It is not final SQL/code — Design/Build fills in exact statements —
but it's specific enough that Design shouldn't need to re-derive the schema or consumer list from
scratch.

---

## 1. Why (recap, full reasoning lives on CARD-0349)

The 2026-09-25 outage (CARD-0226) made an entire spreadsheet document unresponsive for hours, root
cause never identified — a single point of failure for the whole ingest pipeline. CARD-0337 mitigated
by keeping the sheet smaller but deferred the archive step; CARD-0347's 2026-09-26 pipeline review
separately named "storage is a single point of failure" as still-open. Joseph's own motivation, asked
directly: "all of the above, perhaps" — reliability, query/export speed (both `fetch_hike_data.py`'s
exports and the daily backstop probe have hit slow-query/timeout symptoms), and wanting real
dashboards, none singled out as the one driver.

CARD-0349's own comparison concluded TimescaleDB over InfluxDB: only 2 of the 5 tables
(Environmental Data, GPS Track) are genuinely metrics-shaped; the other 3 are relational event logs
with real join needs (GPS correlation, hike-izer's multi-table export) that a pure time-series
database is comparatively weak at. TimescaleDB is Postgres with time-series extensions — known SQL,
real joins, standard Postgres backup tooling.

## 2. Current state (grounded in the actual code, not assumption)

### 2.1 The five sheets

| Sheet | Rows (as of 2026-09-25) | Shape | Producers |
|---|---|---|---|
| `Environmental Data` | ~33,000 | Metric: `(ts, source, lat, lon, ~18 numeric fields)` | Node-RED (MQTT sensors) |
| `GPS Track` | large, one hike's worth per session | Metric: `(ts, lat, lon, acc, alt, direction)` | Phone (GPSLogger custom URL, direct HTTP, no MQTT) |
| `Hiking Observations` | small | Event log: `(ts, observation text, categories[], source)` | Phone (Tasker voice queue, direct HTTP) |
| `Wildlife Detections` | small | Event log: `(ts, hike_file_stem, common_name, scientific_name, count, best_confidence, lat, lon)` | hike-izer-orchestrator (BirdNET pass) |
| `Hike Start Forecast` | tiny, ~1/hike-day | Event snapshot: `(ts, date_local, lat, lon, temp_f, precip_pct, wind_mph, humidity_pct, uv_index, provider)` | Apps Script itself, triggered by the first GPS point or Hiking Observation of a new local day (calls Open-Meteo) |

Two more sheets are derived, not archives, and don't need a migration equivalent as data: `Timeline`
(manually rebuilt human-readable merge of Environmental Data + Hiking Observations — becomes a SQL
view or a simple query, not a stored/rebuilt sheet) and `Correlation Debug` (diagnostic log of
GPS-correlation attempts — becomes an ordinary log table or is dropped; not load-bearing).

### 2.2 Current API surface (`core/data-pipeline/environmental-data.gs`)

**POST** (`doPost`, routed on `payload.component`): `hiking-observations` → Hiking Observations (does
its own keyword-taxonomy category scan inline); `wildlife-detection` → Wildlife Detections; anything
else → Environmental Data (the general sensor path, computes `dew_point_f`/`heat_index_f` — actually
computed by Node-RED before POSTing, per the architecture doc — and applies physical-range ingest
guards).

**GET**, dispatched on `?action=`:

| Action | Role | Caller |
|---|---|---|
| `gps` | GPS Track ingest, plus triggers `_maybeCaptureHikeStartForecast` on a new day | Phone (GPSLogger) |
| `lookup` | timestamp → nearest GPS coordinates | Node-RED's throttled per-reading GPS correlation |
| `export` | date-ranged export of any sheet (`full=1` variant for the whole sheet) | `fetch_hike_data.py` (both interactive Skill and hike-izer-orchestrator's `generate()`) |
| `health` | opens the spreadsheet, reads one cell — the exact operation that hung 2026-09-25 | `sheet_health.py`, `run_daily_refresh_and_log()`'s pre-flight check |
| `version` | deploy fingerprint, never touches the spreadsheet | Manual deploy verification |

**Ingest guards already in `environmental-data.gs`, worth preserving in spirit, not code:** physical
range checks on `temp_f`/`humidity_pct`/`pressure_hpa`/`uv_index` (CARD-0215); duplicate rejection by
reading all existing timestamps in a column and string-comparing (CARD-0215/CARD-0243/CARD-0244) —
this is exactly the "duplicate check compares timestamps as strings" and "per-point full-sheet scans"
findings CARD-0347 flagged as getting slower as sheets grow. **A real database fixes both of these
by construction**, not by more careful hand-written code: a `UNIQUE` constraint plus
`INSERT ... ON CONFLICT DO NOTHING` replaces the full-column dedup scan entirely, and a native
`timestamptz` column replaces string comparison entirely. This migration is also, as a side effect,
the fix for CARD-0347 findings #1, #3, and #4 — worth closing or superseding those specific findings
once this ships, not tracking them separately.

### 2.3 Every real consumer (what has to change)

| Consumer | Today | Change needed |
|---|---|---|
| `environmental-data.flow.json` (Node-RED, Pi) | POSTs sensor readings; GETs `?action=lookup` for GPS correlation, throttled | Point at the new gateway's write endpoint; GPS correlation becomes a real query the gateway does server-side (a nearest-neighbor SQL query), so Node-RED's own throttle/retry logic around `lookup` may simplify or disappear |
| Phone (GPSLogger custom URL) | GET `?action=gps&...` direct to Apps Script | Point the custom URL at the new gateway's equivalent endpoint — same query-string shape achievable, phone-side change is just the base URL |
| Phone (Tasker hiking-observations queue) | POST direct to Apps Script | Same — new gateway URL, same POST body shape achievable |
| `components/hike-izer/fetch_hike_data.py` | GET `?action=export&sheet=...&start=...&end=...` | Rewritten against the new API — this is explicitly in scope since the API is being redesigned, not preserved |
| `hike-izer-orchestrator`'s wildlife/scat archiving | POST `component: wildlife-detection` | New gateway's equivalent write endpoint |
| `sheet_health.py`, `run_daily_refresh_and_log()`'s pre-flight check | GET `?action=health`/`?action=version` | New gateway's own health/version endpoints — a Postgres/Timescale health check is a real connection+query, cheaper and more meaningful than "did opening a spreadsheet document hang" |
| Weather Underground upload, Home Assistant entity updates | Done by Node-RED itself, not the Sheet | **Unaffected** — Node-RED's own responsibilities 5-7 (WU post, HA REST updates, SmartThings routing) don't touch the Sheet at all today and don't need to change |

## 3. Target architecture

**New Docker Compose service on the M8**, alongside the existing `hike-izer-web`/`photo-server`
projects (same self-hosted pattern already used for everything else on that host):

- **`timescaledb`** — the `timescale/timescaledb` Postgres image (Postgres + the Timescale extension),
  with a named volume for data, matching how other stateful M8 services persist data today.
- **A new gateway service** (name TBD in Design — e.g. `data-pipeline-api`) replacing
  `environmental-data.gs` entirely: owns writes (validation, dedup via `ON CONFLICT`, the physical
  range guards), owns the export/query API, owns GPS correlation as a real SQL query, and owns
  `_maybeCaptureHikeStartForecast`'s job (call Open-Meteo on the appropriate trigger). Language choice
  is a Design decision, not fixed here — Python fits this codebase's existing convention
  (`hike-izer-orchestrator` is already a Python HTTP service on this same host) more than introducing
  a new stack.
- **Exposure**: same pattern already proven for `hike-izer-web` — Caddy + Cloudflare Tunnel, or a
  Tailscale-only endpoint if nothing outside the LAN/Tailnet needs to reach it (GPSLogger and Tasker
  both need public reachability today since the phone isn't always on the home network; this needs
  the same public-but-authenticated shape the current Apps Script URL has).

### 3.1 Schema sketch, Phase 1

```sql
-- Environmental Data: one hypertable, partitioned on ts.
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
  PRIMARY KEY (ts, source)          -- replaces the (ts, source) string-based dedup scan
);
SELECT create_hypertable('environmental_data', 'ts');

-- GPS Track: one point per fix, one producer, ts alone is the natural key.
CREATE TABLE gps_track (
  ts         timestamptz PRIMARY KEY,   -- replaces the ts-alone dedup scan
  lat        double precision NOT NULL,
  lon        double precision NOT NULL,
  accuracy_m double precision,
  altitude_m double precision,
  bearing_deg double precision
);
SELECT create_hypertable('gps_track', 'ts');
```

GPS correlation (today's `?action=lookup`, and the derived-field back-fill Node-RED does per
reading) becomes a straightforward nearest-neighbor query instead of a full-sheet scan:

```sql
SELECT lat, lon FROM gps_track
ORDER BY abs(extract(epoch from (ts - $1))) ASC
LIMIT 1;
```

(An index on `ts` — automatic via the hypertable — keeps this fast without the throttling Node-RED
currently needs to protect the Apps Script from bursty replay traffic, CARD-0279.)

### 3.2 Schema sketch, Phase 2 (not built first, sketched so Phase 1's design doesn't paint it into a corner)

```sql
CREATE TABLE hiking_observations (
  ts          timestamptz PRIMARY KEY,
  observation text NOT NULL,
  categories  text[] NOT NULL DEFAULT '{}',
  source      text NOT NULL DEFAULT 'voice'
);

CREATE TABLE wildlife_detections (
  ts               timestamptz NOT NULL,
  hike_file_stem   text NOT NULL,
  common_name      text NOT NULL,
  scientific_name  text,
  count            integer NOT NULL,
  best_confidence  double precision,
  lat              double precision,
  lon              double precision,
  PRIMARY KEY (hike_file_stem, scientific_name)   -- matches today's dedup-on-(hike, species)
);

CREATE TABLE hike_start_forecast (
  ts            timestamptz NOT NULL,
  date_local    date NOT NULL,
  lat           double precision,
  lon           double precision,
  temp_f        double precision,
  precip_pct    double precision,
  wind_mph      double precision,
  humidity_pct  double precision,
  uv_index      double precision,
  provider      text NOT NULL DEFAULT 'open-meteo',
  PRIMARY KEY (date_local)   -- one per local day, matches today's dedup rule
);
```

Plain Postgres tables, not hypertables — these are low-volume event logs, not metrics; no benefit
from Timescale's chunking here.

## 4. Migration / backfill

1. Export the existing sheets via the **current** `action=export&full=1` (still working during
   Phase 1's build) to get every historical row.
2. Bulk-load into the new tables via a one-time script (`COPY` or batched `INSERT`), transforming
   field names/types as needed (e.g. Sheets' string timestamps -> `timestamptz`).
3. Verify: row counts match, spot-check a real hike's export against `fetch_hike_data.py`'s existing
   output for the same date range (same pattern CARD-0311/CARD-0348 already used -- compare a known
   real hike's numbers before and after).
4. Old spreadsheet stays untouched and reachable during this whole process -- no write traffic is
   redirected until the new store is verified.

## 5. Cutover

Given the API itself is being redesigned (not preserved), a dual-write period across two different
API shapes adds real complexity for a personal project with one write path per producer. Preferred
approach: build and verify the new gateway + TimescaleDB fully against backfilled historical data
first (no live traffic), then cut each producer over one at a time (Node-RED, GPSLogger's custom URL,
Tasker's queue endpoint, hike-izer's export calls) on a chosen day, verifying each before moving to
the next. Keep the old spreadsheet reachable and untouched for some period after cutover as a
read-only fallback, per Joseph's own "retire once verified" decision -- not deleted immediately on
cutover day.

## 6. Phasing

- **Phase 1 (build first):** Environmental Data + GPS Track, the new gateway service, GPS
  correlation as a SQL query, Node-RED and GPSLogger cut over. This is the pair that actually
  motivated the whole card (2026-09-25's outage was on Environmental Data) and the pair CARD-0349's
  own comparison confirmed is genuinely metrics-shaped.
- **Phase 2:** Hiking Observations, Wildlife Detections, Hike Start Forecast, and their producers
  (Tasker's queue, hike-izer-orchestrator's wildlife archiving, the Open-Meteo capture trigger) --
  only after Phase 1 has run live and proven stable.
- Sheets retirement happens per-phase as each phase's data/producers are fully cut over and verified,
  not as one single event at the very end.

## 7. Open questions for Design

- Exact gateway language/framework (Python fits the existing `hike-izer-orchestrator` convention on
  this same host; not fixed here).
- Exact new API shape replacing `action=export`/`lookup`/`gps`/`health`/`version` and `doPost`'s
  component-routing -- a real redesign opportunity, deliberately left to Design rather than assumed
  here, beyond noting every current consumer this needs to keep serving (section 2.3).
- Backup strategy for the new Postgres/Timescale instance (the M8 already has some backup patterns
  for other stateful services worth checking for reuse, e.g. Immich's photo-library backup approach).
- Whether `Correlation Debug`'s diagnostic value is worth a real log table or whether ordinary
  container logs already cover it -- leaning toward the latter, not carried forward as a stored table
  by default.
- Whether GPSLogger's and Tasker's phone-side configuration can point at a new URL with zero other
  changes (expected yes -- same query-string/POST-body shape is achievable at the gateway), to be
  confirmed once the gateway's exact routes are designed.

## 8. Related

CARD-0349 (tracking card, full background/comparison/recommendation), CARD-0337 (built only the
"keep Sheets small" mitigation), CARD-0347 (pipeline review findings #1/#3/#4 this migration fixes
by construction), CARD-0226 (the outage that started this), `JCTsh-Environmental-Data-Architecture.md`
(the current-state reference this plan is grounded in), `environmental-data.gs`/
`environmental-data.flow.json` (what's being replaced).
