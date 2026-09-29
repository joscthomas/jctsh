# core/data-pipeline — Environmental Data Pipeline

The shared ingest path every environmental reading travels: MQTT (or a direct HTTPS
request, for the phone-sourced pipelines) → `data-pipeline-api` on the M8 → a TimescaleDB
(PostgreSQL) database that is the authoritative archive. Not a component with hardware of
its own — it's the pipeline other components publish *into*, which is why it lives in
`core/` rather than `components/`.

**Status:** Production. Since CARD-0349 (cut over 2026-09-28/29) the store is TimescaleDB,
not Google Sheets. `environmental-data.gs` and the workbook are retired and kept only as a
historical reference — nothing writes to them. Four components publish sensor readings
through it — `hiking-monitor`, `air-quality-monitor`, `front-porch-temp-sensor`,
`back-patio-temp-sensor` — and the phone-sourced HTTP pipelines (GPS Track, Hiking
Observations) plus the hike-izer orchestrator (Hike Start Forecast, Wildlife Detections,
Hike-izer Costs) call the gateway directly, never through the broker.

Payload schema and the planned sensor family are in
`JCTsh-Environmental-Data-Architecture.md`. **That document is the standard; this one is
the operational reference** — what runs where, how to deploy it, and how to check it.
Table definitions live in `init/schema.sql`, which is the source of truth for columns.

---

## Files

| File | Purpose |
|---|---|
| `JCTsh-Environmental-Data-Architecture.md` | The standard — payload schema, field reference, derived fields, Node-RED handler pattern, planned device family. Its Sheets-era sections are marked historical. |
| `docker-compose.yml` | The M8 compose project: `timescaledb` + `data-pipeline-api`. |
| `api/app.py`, `api/Dockerfile`, `api/requirements.txt` | The gateway (`data-pipeline-api`): stdlib `http.server` + `psycopg2`, same handler convention as `hike-izer-orchestrator/app.py`. |
| `init/schema.sql` | Table definitions. Runs once, only against an empty `pgdata` volume — a schema change after go-live needs a real migration, not an edit here. |
| `.env.example` | Names the secrets `.env` must carry. Real values live in `credentials.local.md`. |
| `environmental-data.flow.json` | The Node-RED handler tab (`jctsh/components/+/data` → derived fields → GPS lookup → POST to the gateway). Import into Node-RED on the Pi. |
| `sheet-health.flow.json` | The Node-RED "Sheet Health" tab — a 5-minute probe of the gateway's `/health`. The name is historical; it now probes the database. |
| `pg-backup.sh`, `pg-backup.service`, `pg-backup.timer` | Daily 04:00 `pg_dump` on the M8 (CARD-0362). |
| `migrate_to_timescale.py` | One-time Sheets → TimescaleDB backfill script. Historical; not part of the running system. |
| `timescaledb-design.md`, `timescaledb-migration-plan.md` | CARD-0349's Planning and Design artifacts — the record of how the decision was made. Written before the build; where they differ from `init/schema.sql` or `api/app.py`, the code is right. |
| `environmental-data.gs` | **Retired** Apps Script source. Reference only. |
| `RUNBOOK-sheets-outage.md` | **Retired**, kept for its incident history (CARD-0226). |
| `pipeline-review-2026-09-26.md` | The review that motivated the migration (CARD-0347). |
| `CLAUDE.md` | Curated gotchas as they're learned. |
| `card-archive.md` | Archived `[data-pipeline]` card history. On-demand only. |

## Flow of a reading

```
ESP32 sensor ──MQTT──► jctsh/components/<name>/data
                              │
                              ▼
                  Node-RED (Pi): environmental-data.flow.json
                    ├─ route skip/reset/display-refresh events → component log topic
                    ├─ GPS lookup (throttled) → gateway  GET /lookup-gps
                    ├─ compute derived fields (dew point, heat index, rain)
                    └─ serial queue, retry, alert ─► gateway  POST /environmental-data
                                                              │
GPSLogger (phone) ──► GET /gps ───────────────────────────────┤
Tasker (phone) ────► POST /hiking-observations ───────────────┤   data-pipeline-api
hike-izer-orchestrator ► POST /wildlife-detection,            ├─► (M8, :8080)
                         /hike-izer-cost ─────────────────────┤        │
fetch_hike_data.py ◄── GET /export ───────────────────────────┘        ▼
                                                                TimescaleDB (M8)
```

Phone-sourced pipelines bypass MQTT entirely — see root `CLAUDE.md`'s "MQTT vs. Direct
HTTP" section. The gateway has no MQTT client of its own, so its log lines reach the
dashboard by POSTing to `hike-izer-orchestrator`'s `/webhook/pipeline-log`, which
republishes on its behalf (CARD-0225).

## Where it runs

New Docker Compose project on the **M8**, deployed to `~/data-pipeline-app/` (scp'd, no git
checkout there — same pattern as `~/hike-izer-web-app/`). Two containers:

| Container | Image | Exposure |
|---|---|---|
| `data-pipeline-timescaledb` | `timescale/timescaledb:2.30.1-pg16` (pinned, CARD-0362 — bump deliberately, never by rebuild accident) | `127.0.0.1:5432` only. For DBeaver, tunnel over SSH to the M8; never bound to the LAN. |
| `data-pipeline-api` | built from `api/` | `127.0.0.1:8091` locally; publicly at **`https://hikes.jctnet.com/data/…`** via the existing Cloudflare Tunnel + Caddy (`components/hike-izer-web/Caddyfile`'s `handle_path /data/*`, which strips the `/data` prefix — the gateway's own routes are `/gps`, not `/data/gps`). |

Every route authenticates with a shared secret, checked with a constant-time compare:
**`Authorization: Bearer <API_KEY>` is the form to use** (CARD-0365). `?key=<API_KEY>` is still
accepted while GPSLogger and Tasker are moved over, but a key in the URL lands in every access
log on the way here, so the gateway logs each legacy use (rate-limited, never the key) and
Caddy redacts `key=` from its access log. The URL and key reach callers as
`DATA_PIPELINE_URL` / `DATA_PIPELINE_KEY` (Node-RED env vars, the orchestrator's `.env`) and
in GPSLogger's saved URL.

**Key rotation window (CARD-0372).** Set `API_KEY_PREVIOUS` and `API_KEY_PREVIOUS_EXPIRES` (ISO 8601 UTC
or epoch seconds) in the gateway's `.env` and both keys are accepted until that instant, after which the
gateway ignores the old one **on its own** — no runner or timer is needed for the window to close. A
previous key with no valid expiry is ignored outright. Leave both unset normally. Uses of the old key are
logged (rate-limited, never the key) and visible through `/auth-status`.

## Gateway routes

| Method | Path | Caller | Notes |
|---|---|---|---|
| POST | `/environmental-data` | Node-RED | JSON body with `ts`, `source`, and any sensor fields; absent fields are stored NULL. `400` on a missing `ts`/`source` or a value that can't be coerced; a duplicate `(ts, source)` gets the duplicate response, not an error. |
| GET | `/gps` | GPSLogger | Query-string ingest (GPSLogger's custom-URL feature only does templated GETs — a device constraint). `lat`/`lon`/`ts` are strict; `acc`/`alt`/`direction` are optional, and a garbled value is logged and ignored rather than rejecting the point. A stored, non-duplicate point may also trigger the Hike Start Forecast capture. |
| GET | `/lookup-gps` | Node-RED | `?ts=` → the nearest GPS fix by absolute time distance. |
| GET | `/export` | `fetch_hike_data.py` | `?table=&start=&end=` (ISO 8601). `table` is one of `environmental_data`, `gps_track`, `wildlife_detections`, `hike_start_forecast`, `hiking_observations`, `hike_izer_cost`. Returns native JSON types. |
| POST | `/hiking-observations` | Tasker | Keyword-categorizes the text; back-fills coordinates from the GPS track. |
| POST | `/wildlife-detection` | orchestrator | One species per hike; first write wins. |
| POST | `/hike-izer-cost` | orchestrator | One row per generation run. |
| GET | `/health` | Node-RED probe, orchestrator pre-flight, the container's own healthcheck | Runs a real `SELECT 1`; `500` with the error text on failure. |
| GET | `/version` | manual deploy check | Returns `VERSION` from `api/app.py`. |
| GET | `/auth-status` | rotation runner (CARD-0372) | Whether a previous key is configured/active and when it expires, plus the latest time each path authenticated with the `current` and the `previous` key (in memory since start). Never returns a key. |

`scat-detection` has no route — it was unused before the migration and was not ported.

## Tables

Defined in `init/schema.sql`. Two hypertables (`environmental_data`, `gps_track`), four
ordinary tables.

| Table | A row is | Dedup key |
|---|---|---|
| `environmental_data` | one sensor reading, any source | `(ts, source)` |
| `gps_track` | one GPS fix | `ts` |
| `hike_start_forecast` | one detected hike session (a long gap since the previous fix starts a new one) | `ts` |
| `hiking_observations` | one voice note (`categories` is a real `text[]`) | `ts` |
| `wildlife_detections` | one species per hike | `(hike_file_stem, scientific_name)` |
| `hike_izer_cost` | one generation run | every cost field together, deliberately not `ts` |

**Ingest guards live in the database now.** The physical range checks (`temp_f` −20…130,
`humidity_pct` 0…100, `pressure_hpa` 800…1100, `uv_index` 0…20) are `CHECK` constraints on
`environmental_data`, and the duplicate rules are the primary keys — the gateway catches the
violation and answers with the response shape callers already expect. There is no per-write
duplicate scan to go stale.

## Node-RED handler

Subscribes to **`jctsh/components/+/data`** (wildcard), so a new environmental sensor is
captured with **no per-device Node-RED change** — it just has to publish on that pattern
with a conforming payload. Nodes, in order:

| Node | Role |
|---|---|
| `jctsh/components/+/data` (mqtt in) | Wildcard subscription |
| Route skip/reset/display-refresh events | Diagnostic events split off to the component's own log topic, not the archive (CARD-0195/0196) |
| Prepare GPS lookup → GPS lookup → Check response | Correlates a reading with no coordinates to a GPS fix via `/lookup-gps`; retries, then publishes an `Alert` after 3 failures (CARD-0279) |
| Compute derived fields + build POST | `dew_point_f`, `heat_index_f`, `rainin`, `dailyrainin` — computed here, never sent by the ESP32 |
| POST queue → POST → Check response | Serial queue, one request in flight, retry every 5 minutes, alert at most once per 30 minutes, discard only after 24 hours (CARD-0226). **The queue is in memory** — redeploying the tab or restarting Node-RED empties it. |

Three node names still say "Apps Script" (`POST to Apps Script (no redirect follow)`,
`Follow Apps Script redirect`, `Get Apps Script result`). They are left over from the old
target, and the redirect-follow pair is vestigial now that the gateway answers directly.
Rain accumulators (rolling 60-minute buffer, daily total reset at midnight
`America/Phoenix`) are flow-context variables, persistent across redeploys.

## Health, backup, and what to do when it's down

- **Probe:** the Node-RED "Sheet Health" tab calls `/health` every 5 minutes and pushes to
  the Pixel and logs under component `sheet-health` after two consecutive bad or >10 s
  checks. The orchestrator's daily refresh and backstop also pre-flight `/health` and skip
  themselves while it's bad — a skipped daily refresh is re-run by hand:
  `docker exec hike-izer-orchestrator python3 generation.py --daily-refresh`.
- **Nothing is lost while it's down:** Node-RED's queue holds readings (up to 24 h, in
  memory), the phone apps queue their own posts, and hiking-monitor/air-quality-monitor keep
  their logs on-device until the next run and can replay them.
- **Backup:** `pg-backup.timer` runs daily at 04:00 MST on the M8, writing a custom-format
  `pg_dump` to `~/data-pipeline-app/backups/` and pruning dumps older than 14 days.
  **Local only** — it covers a corrupted container or data directory, not loss of the M8
  itself. Off-host backup is not yet built.
- **Restore:** `docker exec -i data-pipeline-timescaledb pg_restore -U jctsh -d jctsh --clean --if-exists < <dump>`.
  Not rehearsed end to end — treat it as untested until it has been.

## Deploy

On the M8, from a checkout on the workstation:

```bash
scp -r core/data-pipeline/{docker-compose.yml,api,init,pg-backup.sh} jct@m8.local:~/data-pipeline-app/
ssh jct@m8.local "cd ~/data-pipeline-app && docker compose up -d --build data-pipeline-api"
curl -s "https://hikes.jctnet.com/data/version?key=$DATA_PIPELINE_KEY"   # confirm the new VERSION is serving
```

Bump `VERSION` in `api/app.py` on every gateway change — it is the only way to tell a
landed deploy from a stale one. `init/schema.sql` does **not** re-run; a schema change needs
a hand-written `ALTER` against the live database and a matching edit to `schema.sql`.

`environmental-data.flow.json` and `sheet-health.flow.json`: import into Node-RED on the Pi
(`pi1.local:1880`); import `core/node-red/core.flow.json` first if the MQTT broker node isn't
there. **The live Node-RED file (`/home/pi/.node-red/flows.json`) is what runs** — after any
edit in the editor, re-export the tab back into this directory, or the repo copy goes stale
(it did, silently, through the cutover — CARD-0369).

The repo is the source of truth for everything else — edit here and deploy out.

## Known behaviors and limitations

- **Weather Underground cannot be backfilled.** A WU gap is permanent; database gaps can be
  backfilled from a device's own offline log. WU is a display window, not an archive. (No
  WU upload node exists in the handler today — `weather-station` isn't built; see the
  Architecture doc's WU section.)
- **A stale gateway deploy is silent.** Check `/version` against `VERSION`, don't assume.
- **A failed write is retried by Node-RED's queue, then discarded after 24 h** — it never
  blocks the flow.
- **`back-patio-temp-sensor` history:** its original counterfeit BMP280 (chip ID `0x58`)
  made ESPHome mark the component FAILED and suppressed every `/data` payload until the
  genuine BME280 swap (2026-09-22). See CARD-0219 for current status.

## Related

- `JCTsh-Environmental-Data-Architecture.md` — the standard every environmental component conforms to.
- Root `CLAUDE.md` — "MQTT vs. Direct HTTP" and the M8/Pi placement convention.
- `core/node-red/` — the broker node this flow depends on, and the watchdog flow alongside it.
- `components/hike-izer-web/Caddyfile` — the public `/data/*` route.
- `components/hike-izer-orchestrator/` — hosts `/webhook/pipeline-log` and is the gateway's heaviest caller.
- `components/hiking-monitor/`, `components/air-quality-monitor/`, `components/front-porch-temp-sensor/`, `components/back-patio-temp-sensor/` — the four publishers.
- `tos/kanban-board.md` CARD-0349 (the migration), CARD-0347 (the review), CARD-0362 (pinning and backup), CARD-0338/0369 (health probe), CARD-0279 (GPS lookup throttle/retry), CARD-0225 (MQTT-vs-HTTP boundary and log relay).
