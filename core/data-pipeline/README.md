# core/data-pipeline — Environmental Data Pipeline

The shared ingest path every environmental reading travels: MQTT (or a direct HTTPS POST,
for the phone-sourced pipelines) → a Node-RED handler on the Pi → a Google Apps Script web
app → the Google Sheets workbook that is the authoritative archive. Not a component with
hardware of its own — it's the pipeline other components publish *into*, which is why it
lives in `core/` rather than `components/`.

**Status:** Production. Four components are configured to publish into it —
`hiking-monitor`, `air-quality-monitor`, `front-porch-temp-sensor`,
`back-patio-temp-sensor` — plus three phone-sourced HTTP pipelines (GPS Track, Hiking
Observations, Hike Start Forecast) that reach the Apps Script directly, never through the
broker.

> **`back-patio-temp-sensor` is configured but currently silent on `/data`** (measured by
> the porch/patio session, 2026-09-22: 6.6 minutes subscribed, longer than the 5-minute
> interval — 4 illuminance messages, zero `/data`). Its BME280 is one of the counterfeit
> BMP280s (chip ID `0x58`, not `0x60`), so ESPHome's `bme280_i2c` marks the component
> FAILED, temp/humidity/pressure all read NaN, and the publish lambda's
> `if (isnan(...)) skip` guard suppresses the payload. A genuine BME280 is on order and
> the swap is drop-in, so this is transient — the YAML and topic are correct.

Payload schema, sheet schemas, Weather Underground integration, and the planned sensor
family are defined in `JCTsh-Environmental-Data-Architecture.md`. **That document is the
standard; this one is the operational reference** — what's in this directory, what runs
where, how to deploy it, and how to verify a deploy landed.

---

## Files

| File | Purpose |
|---|---|
| `JCTsh-Environmental-Data-Architecture.md` | The standard — payload schema, field reference, derived fields, Sheets archive design, Node-RED handler pattern, Weather Underground integration, planned device family. Every environmental component must conform to it. |
| `environmental-data.flow.json` | The Node-RED handler — wildcard subscription on `jctsh/components/+/data`, GPS correlation, derived fields, POST to the Apps Script. Import into Node-RED on the Pi. |
| `environmental-data.gs` | Google Apps Script source, bound to the Sheets workbook and deployed as a web app. Paste into the Apps Script editor; **redeploy after any change** or the old version keeps serving. |
| `CLAUDE.md` | Curated context stub — design rationale/gotchas as they're learned (currently empty by design, CARD-0290). |
| `card-archive.md` | Archived `[data-pipeline]` card history. On-demand only, never routine reading. |

## Flow of a reading

```
ESP32 sensor ──MQTT──► jctsh/components/<name>/data
                              │
                              ▼
                  Node-RED: environmental-data.flow.json
                    ├─ route skip/reset/display-refresh events → component log topic
                    ├─ GPS lookup (throttled) → Apps Script ?action=lookup
                    ├─ compute derived fields (dew point, heat index, rain)
                    └─ POST ──► Apps Script web app ──► Google Sheets workbook
                                       ▲                     (authoritative archive)
Phone pipelines ──direct HTTPS POST────┘
(GPS Track, Hiking Observations, Hike Start Forecast)
```

Phone-sourced pipelines bypass MQTT entirely and post straight to the Apps Script — see
root `CLAUDE.md`'s "MQTT vs. Direct HTTP" section for why (Apps Script has no MQTT client
capability at all, `UrlFetchApp` only).

## Node-RED handler

Subscribes to **`jctsh/components/+/data`** (wildcard), so a new environmental sensor is
captured with **no per-device Node-RED change** — it just has to publish on that pattern
with a conforming payload. Nodes, in order:

| Node | Role |
|---|---|
| `jctsh/components/+/data` (mqtt in) | Wildcard subscription — every component's data topic |
| Route skip/reset/display-refresh events | Diagnostic events split off to the component's own log topic, not the archive (CARD-0195/CARD-0196) |
| Prepare GPS lookup → Throttle → GPS lookup | Correlates the reading to a GPS fix from the `GPS Track` sheet; throttled to protect the Apps Script from bursty replay traffic (CARD-0279) |
| Check GPS lookup response | Retries, then publishes an `Alert` to the log topic after 3 failed attempts (CARD-0279) |
| Compute derived fields + build POST | `dew_point_f`, `heat_index_f`, `rainin`, `dailyrainin` — computed here, never sent by the ESP32 |
| POST to Apps Script → Check response | Writes the row; success/error logged to MQTT |

Rain accumulators (rolling 60-minute buffer, daily total reset at midnight
`America/Phoenix`) are Node-RED flow-context variables, persistent across redeploys via
the context store — not held in the Apps Script.

## Apps Script web app

Auth is a secret key in the URL, checked on every request against the `API_KEY` script
property — no OAuth. The URL and key live in Node-RED environment variables, never in
source control. `SCRIPT_VERSION` (top of the file) is the deploy fingerprint: fetch
`?action=version` to confirm which version is actually serving.

**POST routes** — dispatched on `payload.component`:

| `payload.component` | Destination |
|---|---|
| `hiking-observations` | `Hiking Observations` — keyword-scans the text against an 8-category taxonomy, back-fills coordinates via GPS lookup |
| `wildlife-detection` | `Wildlife Detections` — lock-guarded, retried write |
| anything else | `Environmental Data` — the general sensor path |

**GET routes** — dispatched on `?action=`:

| Action | Role |
|---|---|
| `gps` | GPS Track ingest — GPSLogger's custom-URL endpoint (tolerates epoch-seconds, epoch-ms, or ISO timestamps) |
| `lookup` | Timestamp → coordinates, used by the Node-RED GPS lookup node |
| `export` | Date-ranged sheet export, consumed by the hike-izer pipeline |
| `version` | Returns `SCRIPT_VERSION` — the deploy check above |

**Sheets in the workbook**, as actually referenced by the script: `Environmental Data`,
`GPS Track`, `Hiking Observations`, `Hike Start Forecast`, `Wildlife Detections`,
`Timeline` (built by `refreshTimeline()`), `Correlation Debug` (GPS-correlation
diagnostics).

**Ingest guards** — the archive is the authoritative store, so bad data is rejected at the
door rather than cleaned up later:

- **Physical range checks** on `temp_f` (−20…130), `humidity_pct` (0…100), `pressure_hpa`
  (800…1100), `uv_index` (0…20), applied only when the field is present. Added after a
  mid-crash MQTT publish wrote `temp_f=370.6` / `pressure_hpa=−174.9` / `uv_index=7294.4`
  into the sheet 74 times (CARD-0215).
- **Duplicate rejection**, with a per-sheet key: `(ts, source)` for `Environmental Data`
  (many producers, CARD-0215), `ts` alone for `GPS Track` (CARD-0243 — one real hike's
  data was 29.5% duplicate rows) and `Hiking Observations` (CARD-0244). Reads only the key
  columns, not whole rows, to stay cheap as the sheets grow.
- Maintenance helpers for damage already done: `cleanupDuplicateEnvironmentalData()`,
  `cleanupDuplicateGpsTrack()`, `fixFrontPorchCoordinates()`, exposed via `onOpen()`.

## Known behaviors and limitations

- **Weather Underground cannot be backfilled.** A WU gap is permanent; Sheets gaps can be
  backfilled from a device's own offline log. WU is a display window, not an archive.
- **This pipeline has no MQTT presence of its own.** Apps Script can't reach a broker, so
  log visibility comes from `_relayLog()` POSTing to `hike-izer-orchestrator`'s
  `/webhook/pipeline-log`, which republishes to the log topic on its behalf (CARD-0225).
- **A failed Sheets/WU write is logged and skipped, never queued** — the handler continues
  rather than blocking the flow.
- **A stale Apps Script deploy is silent.** Editing `environmental-data.gs` and pasting it
  in changes nothing until the web app is redeployed — check `?action=version` against
  `SCRIPT_VERSION`, don't assume.

## Deploy

| Piece | How |
|---|---|
| `environmental-data.flow.json` | Import into Node-RED on the Pi (`pi1.local:1880`). Import `core/node-red/core.flow.json` first if the MQTT broker node isn't already present. |
| `environmental-data.gs` | Paste into the bound Apps Script editor, then **Deploy → Manage deployments → redeploy**. Verify with `?action=version`. |

The repo is the source of truth for both — edit here and deploy out, never the reverse.

## Related

- `JCTsh-Environmental-Data-Architecture.md` — the standard every environmental component conforms to.
- Root `CLAUDE.md` — "Environmental Data Architecture" and "MQTT vs. Direct HTTP" sections.
- `core/node-red/` — the broker node this flow depends on, and the watchdog flow alongside it.
- `components/hike-izer-orchestrator/` — hosts `/webhook/pipeline-log` (the MQTT relay) and consumes `?action=export`.
- `components/hiking-monitor/`, `components/air-quality-monitor/`, `components/front-porch-temp-sensor/`, `components/back-patio-temp-sensor/` — the four publishers.
- `kanban-board.md` CARD-0215/CARD-0243/CARD-0244 (ingest guards), CARD-0279 (GPS lookup throttle/retry), CARD-0225 (MQTT-vs-HTTP boundary and the log relay), CARD-0306 (open bug — a stationary device's own coordinates overwritten by the hiker's live GPS), CARD-0291 (the audit whose fifth pass produced this file).
