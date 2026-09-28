#!/usr/bin/env python
"""
CARD-0349 Step 2 -- one-time backfill from the current, still-live Google
Sheets/Apps Script pipeline into the new TimescaleDB gateway. Design doc:
core/data-pipeline/timescaledb-design.md, section 5.

Run by hand during Build, not part of the deployed gateway (never COPY'd
into api/Dockerfile's image) -- invoke it against the already-deployed
data-pipeline-api container so it gets psycopg2 and network access to
`timescaledb` for free, without baking a one-time script into the service
image:

    docker compose run --rm \\
      -v "$(pwd)/migrate_to_timescale.py:/app/migrate_to_timescale.py:ro" \\
      data-pipeline-api python3 /app/migrate_to_timescale.py \\
        --sheets-url <Apps Script Deployment URL> --sheets-key <API_KEY> \\
      # DB_HOST/DB_NAME/DB_USER/DB_PASSWORD already present in that
      # container's own environment (docker-compose.yml's env_file) --
      # see credentials.local.md "Google Apps Script -- Environmental Data
      # Pipeline" for --sheets-url/--sheets-key.

Safe to re-run: every insert uses ON CONFLICT DO NOTHING against the same
(ts, source) / ts primary keys the live gateway itself enforces (CARD-0215/
CARD-0243), so a second run against unchanged source data inserts zero new
rows rather than erroring or duplicating.

Verification here is row-count accounting only (fetched vs. inserted vs.
already-present) -- the design doc's other mandatory check, "a real recent
hike's fetch_hike_data.py output reproduces the same stats/coverage numbers
against the new /export," depends on Step 6 (fetch_hike_data.py rewritten
against the new API) and isn't run by this script.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import psycopg2
import psycopg2.extras

FETCH_RETRY_ATTEMPTS = 5
FETCH_RETRY_BACKOFF_SEC = (3, 6, 12, 24)

# (Sheets tab name, Postgres table name, ordered column list) -- column
# order matches init/schema.sql and api/app.py's ENV_OPTIONAL_FIELDS
# exactly, verified against environmental-data.gs's own doPost appendRow
# order, not assumed.
TABLES = [
    (
        "Environmental Data",
        "environmental_data",
        [
            "ts", "source", "lat", "lon", "temp_f", "humidity_pct",
            "pressure_hpa", "dew_point_f", "heat_index_f", "uv_index",
            "irradiance_wm2", "wind_speed_mph", "wind_dir_deg", "rain_tips",
            "rainin", "dailyrainin", "battery_v", "rssi_dbm", "pm1_ug_m3",
            "pm25_ug_m3", "pm4_ug_m3", "pm10_ug_m3", "voc_index",
            "nox_index", "illuminance_lx", "solar_v",
        ],
    ),
    (
        "GPS Track",
        "gps_track",
        ["ts", "lat", "lon", "accuracy_m", "altitude_m", "bearing_deg"],
    ),
]


def fetch_sheet_full(base_url, api_key, sheet):
    """action=export&full=1 -- the whole tab, no tail-optimization games
    (those exist in environmental-data.gs only to keep a live, latency-
    sensitive query fast; a one-time backfill has no such constraint).
    Same retry/backoff shape as fetch_hike_data.py's own fetch_sheet()."""
    params = {"key": api_key, "action": "export", "full": "1", "sheet": sheet}
    url = base_url + "?" + urllib.parse.urlencode(params)
    data = None
    for attempt in range(1, FETCH_RETRY_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(url, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            break
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            if attempt == FETCH_RETRY_ATTEMPTS:
                raise
            print(f"fetch_sheet_full: attempt {attempt}/{FETCH_RETRY_ATTEMPTS} failed for sheet={sheet} ({e}) -- retrying", file=sys.stderr)
            time.sleep(FETCH_RETRY_BACKOFF_SEC[attempt - 1])
    if data.get("status") != "ok":
        raise RuntimeError(f"Export failed for sheet={sheet}: {data.get('message')}")
    return data["rows"]


def _clean(value):
    """Sheets' getValues() returns '' for a truly empty cell, never null --
    Postgres can't cast '' to a numeric column, so this is the one
    transform every field needs (design doc section 5, step 2: 'blank
    cells -> NULL'). Everything else is passed through as the same string
    Sheets returned and left to Postgres' own implicit text->type cast on
    INSERT, same as a normal parameterized query already does for any
    numeric literal typed as text."""
    return None if value in (None, "") else value


def migrate_table(conn, sheets_url, sheets_key, sheet_name, table_name, columns):
    print(f"Fetching '{sheet_name}' (full export)...")
    rows = fetch_sheet_full(sheets_url, sheets_key, sheet_name)
    print(f"  {len(rows)} rows fetched from Sheets.")

    values = [tuple(_clean(row.get(col)) for col in columns) for row in rows]

    cols_sql = ", ".join(columns)
    # A duplicate here is a real, already-known condition (CARD-0215/
    # CARD-0243's own dedup findings -- the live sheets still hold rows
    # that predate those guards), not a migration failure -- skip it, same
    # as the live gateway's own UniqueViolation handling does for a resent
    # reading.
    insert_sql = (
        f"INSERT INTO {table_name} ({cols_sql}) VALUES %s "
        f"ON CONFLICT DO NOTHING"
    )
    with conn.cursor() as cur:
        before = _count(cur, table_name)
        psycopg2.extras.execute_values(cur, insert_sql, values, page_size=1000)
        conn.commit()
        after = _count(cur, table_name)

    inserted = after - before
    skipped = len(rows) - inserted
    print(f"  {inserted} rows inserted, {skipped} already present (or duplicate) -- table now holds {after} rows.")
    return len(rows), inserted, after


def _count(cur, table_name):
    cur.execute(f"SELECT count(*) FROM {table_name}")
    return cur.fetchone()[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sheets-url", required=True, help="Apps Script Deployment URL (credentials.local.md)")
    parser.add_argument("--sheets-key", required=True, help="Apps Script API_KEY (credentials.local.md)")
    args = parser.parse_args()

    db_host = os.environ.get("DB_HOST", "timescaledb")
    db_name = os.environ.get("DB_NAME", "jctsh")
    db_user = os.environ.get("DB_USER", "jctsh")
    db_password = os.environ.get("DB_PASSWORD", "")
    if not db_password:
        print("FATAL: DB_PASSWORD not set in this container's environment", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(host=db_host, dbname=db_name, user=db_user, password=db_password)
    try:
        summary = []
        for sheet_name, table_name, columns in TABLES:
            fetched, inserted, total = migrate_table(conn, args.sheets_url, args.sheets_key, sheet_name, table_name, columns)
            summary.append((table_name, fetched, inserted, total))
    finally:
        conn.close()

    print("\nSummary:")
    for table_name, fetched, inserted, total in summary:
        print(f"  {table_name}: {fetched} fetched, {inserted} newly inserted, {total} now in table.")
    print(
        "\nRow counts intentionally won't match 1:1 if the source sheets hold pre-CARD-0215/"
        "CARD-0243 duplicates -- those are correctly skipped here, not a migration bug.\n"
        "This script does NOT verify fetch_hike_data.py output against the new API (Step 6, "
        "not built yet) -- do that comparison before treating this migration as fully verified."
    )


if __name__ == "__main__":
    main()
