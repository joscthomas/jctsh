-- CARD-0349 Phase 1 -- runs once, automatically, on first container start
-- against a brand-new pgdata volume (Postgres' own
-- docker-entrypoint-initdb.d convention). Not re-run on restart -- a schema
-- change after go-live needs a real migration, not an edit here.
--
-- Field list matches environmental-data.gs's doPost appendRow column order
-- exactly (core/data-pipeline/environmental-data.gs, ~line 457) -- verified
-- against the live script, not assumed from the architecture doc alone.

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
-- Index on source alone, for queries scoped to one sensor across a wide
-- date range (e.g. "all hiking-monitor readings this month") that don't
-- want to scan every source's rows in a chunk.
CREATE INDEX idx_environmental_data_source ON environmental_data (source, ts DESC);

-- Ingest guards (CARD-0215's physical range checks), enforced by the
-- database itself now, not application code that has to remember to call
-- them -- same bounds as environmental-data.gs's doPost rangeChecks.
ALTER TABLE environmental_data ADD CONSTRAINT chk_temp_f CHECK (temp_f IS NULL OR temp_f BETWEEN -20 AND 130);
ALTER TABLE environmental_data ADD CONSTRAINT chk_humidity CHECK (humidity_pct IS NULL OR humidity_pct BETWEEN 0 AND 100);
ALTER TABLE environmental_data ADD CONSTRAINT chk_pressure CHECK (pressure_hpa IS NULL OR pressure_hpa BETWEEN 800 AND 1100);
ALTER TABLE environmental_data ADD CONSTRAINT chk_uv CHECK (uv_index IS NULL OR uv_index BETWEEN 0 AND 20);

-- GPS Track: one producer (GPSLogger's custom-URL POST), so ts alone is a
-- sufficient dedup key (PRIMARY KEY), matching the environmental-data.gs
-- action=gps dedup logic it replaces (CARD-0243). Column names verified
-- directly against components/hiking-monitor/gps-pipeline.md's real
-- documented sheet schema (2026-09-28, live migration run) -- the design
-- doc's own sketch had invented "bearing_deg"; the sheet's real column F
-- is "direction" (same name the GET ingest route's own ?direction= query
-- param already uses), corrected here rather than carried forward.
CREATE TABLE gps_track (
  ts          timestamptz PRIMARY KEY,
  lat         double precision NOT NULL,
  lon         double precision NOT NULL,
  accuracy_m  double precision,
  altitude_m  double precision,
  direction   double precision
);
SELECT create_hypertable('gps_track', 'ts');

-- Hike Start Forecast: one row per detected hike session (CARD-0083/CARD-0097/
-- CARD-0115's session-gap logic, ported from environmental-data.gs's
-- _maybeCaptureHikeStartForecast -- CARD-0349 Phase 2). Not a hypertable --
-- CARD-0349's own comparison already judged this table "barely time-series
-- at all, a handful of rows", unlike environmental_data/gps_track.
CREATE TABLE hike_start_forecast (
  ts            timestamptz PRIMARY KEY,
  date_local    text,
  lat           double precision,
  lon           double precision,
  temp_f        double precision,
  precip_pct    double precision,
  wind_mph      double precision,
  humidity_pct  double precision,
  uv_index      double precision,
  provider      text
);

-- Hiking Observations: one row per Tasker voice note (CARD-0156, ported from
-- environmental-data.gs's hiking-observations branch -- CARD-0349 Phase 2).
-- categories is a real array here, not JSON.stringify()'d into a text
-- column like the old sheet -- nothing downstream (fetch_hike_data.py)
-- parses it back out, it's carried through raw either way.
CREATE TABLE hiking_observations (
  ts           timestamptz PRIMARY KEY,
  observation  text NOT NULL,
  categories   text[],
  source       text,
  lat          double precision,
  lon          double precision
);

-- Wildlife Detections: one row per species per hike (CARD-0229/CARD-0235/
-- CARD-0276, ported from environmental-data.gs's wildlife-detection branch --
-- CARD-0349 Phase 2). Dedup key matches the old sheet's own identity guard
-- (hike_file_stem, scientific_name), not (ts, source) -- identity dedup,
-- first write wins: a retried POST of an already-committed detection
-- (CARD-0276's own read-timeout-after-real-commit case) is a no-op
-- duplicate, never an overwrite of the existing row.
CREATE TABLE wildlife_detections (
  ts               timestamptz NOT NULL,
  hike_file_stem   text NOT NULL,
  common_name      text,
  scientific_name  text NOT NULL,
  count            integer,
  best_confidence  double precision,
  lat              double precision,
  lon              double precision,
  PRIMARY KEY (hike_file_stem, scientific_name)
);

-- Hike-izer Costs: one row per generation run (CARD-0270, ported from
-- environmental-data.gs's hike-izer-cost branch -- CARD-0349 follow-on,
-- 2026-09-29, the one component originally scoped OUT of CARD-0349's "5
-- tables" because it's generation-pipeline telemetry, not environmental
-- sensor data -- migrated anyway once asked. Dedup is NOT (file_stem,
-- run_type) alone -- the old sheet's own CARD-0270 follow-on deliberately
-- widened it to every cost field too, since a *legitimate* second run on
-- the same hike (e.g. a manual re-run) shares (file_stem, run_type) with
-- the first but has its own real, possibly-different cost, and must get
-- its own row -- only an exact full-content repeat (the CARD-0276
-- read-timeout-but-actually-committed case) counts as a duplicate. ts is
-- deliberately NOT part of the unique constraint, matching the old
-- sheet's own comparison exactly.
-- Device Boot Events: one row per boot a field device has ever reported
-- (CARD-0377 Phase 3). Not a hypertable -- same "barely time-series, a
-- handful of rows" case as hike_start_forecast. (source, boot_id) is the
-- dedup key so a retried upload can't inflate the reset count: boot_id is
-- a fresh random value generated once per boot (air-quality-monitor.yaml's
-- on_boot), so the same boot's event always collides harmlessly on retry.
-- received_at is when the gateway saw it, not when the boot itself
-- happened (the device doesn't timestamp these -- SNTP may not even be
-- synced yet at boot) -- good enough for "how many resets this session",
-- not meant for precise boot-time queries.
CREATE TABLE device_boot_events (
  received_at   timestamptz NOT NULL DEFAULT now(),
  source        text        NOT NULL,
  boot_id       text        NOT NULL,
  reset_reason  text,
  PRIMARY KEY (source, boot_id)
);

CREATE TABLE hike_izer_cost (
  ts             timestamptz NOT NULL,
  file_stem      text NOT NULL,
  run_type       text NOT NULL,
  dollars        double precision,
  calls          integer,
  input_tokens   integer,
  output_tokens  integer,
  web_searches   integer,
  UNIQUE (file_stem, run_type, dollars, calls, input_tokens, output_tokens, web_searches)
);
