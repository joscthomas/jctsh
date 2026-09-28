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
-- action=gps dedup logic it replaces (CARD-0243). Column names match
-- components/hiking-monitor/gps-pipeline.md's schema (accuracy_m/
-- altitude_m, not acc/alt).
CREATE TABLE gps_track (
  ts          timestamptz PRIMARY KEY,
  lat         double precision NOT NULL,
  lon         double precision NOT NULL,
  accuracy_m  double precision,
  altitude_m  double precision,
  bearing_deg double precision
);
SELECT create_hypertable('gps_track', 'ts');
