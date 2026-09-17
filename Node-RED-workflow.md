# Node-RED Flow Update Workflow

## Editing a function node (code-only changes)

Skip import entirely — edit in place:

1. Double-click the function node in Node-RED
2. Edit the code
3. Done → Deploy
4. Export the flow back to the repo: Hamburger → Export → Download → overwrite the file under `core/node-red/`

## Replacing an entire flow (structural changes, new nodes)

**Before doing anything else: check the tab's Environment Variables and back them up** (double right-click the tab to open its properties, then the hamburger menu inside that window → Environment Variables). Some tabs carry real per-tab config here (e.g. Salt Sensor's `HA_TOKEN`) — others source their credentials entirely from a systemd `EnvironmentFile` instead (e.g. Environmental Data's `APPS_SCRIPT_URL`/`APPS_SCRIPT_KEY`, defined in `/home/pi/.node-red/environment` on the Pi, nothing to do with the tab at all). This varies per tab — always check the specific tab you're about to touch, don't assume based on another tab's behavior. If there's anything there, write it down or screenshot it before proceeding — see "Real gotcha" below for why this step is the one that actually matters, not which deletion method you pick.

1. Click the tab containing the flow
2. Ctrl+A → Delete → **Deploy** (clears the tab without removing the tab itself)
3. Hamburger → Import → select file → import
4. If Node-RED reports nodes already existing, click **"View nodes..."** to see exactly what's flagged (expect only the tab itself, not the child nodes, if step 2 actually cleared everything) → **Import selected**
5. Deploy

**Real gotcha, found live 2026-09-17 (CARD-0279's Environmental Data update): this procedure does NOT reliably avoid creating a duplicate tab.** Even with the tab's contents fully cleared first, "View nodes..." → "Import selected" still produced a second, separate "Environmental Data" tab (a fresh tab ID) alongside the original, now-empty one — Node-RED's conflict-resolution here doesn't merge into the existing tab by ID the way earlier guidance assumed. **The actual safeguard is the Environment Variables backup above, not the choice between deleting the tab outright vs. clearing its contents** — treat a new tab as a realistic outcome of *either* method, not a mistake:
- If a duplicate tab appears: copy any backed-up Environment Variables into the new tab, delete the old (now-redundant) one, and rename the new tab back to its original name (Node-RED may append a suffix).
- The broker node (in `core.flow`) is a separate, global config node — it isn't affected either way and MQTT nodes re-attach to it automatically regardless of which tab ends up holding the flow.

## Identifying which flow a JSON file belongs to

The flow JSON files don't include a tab name. Match by filename:

| File | Node-RED tab |
|---|---|
| `core/node-red/core.flow.json` | Core (import first — contains the MQTT broker node) |
| `core/node-red/watchdog.flow.json` | Watchdog |
| `core/data-pipeline/environmental-data.flow.json` | Environmental Data |
| `components/garage-radar/garage-radar.flow.json` | Garage Radar |
| `components/hiking-monitor/hiking-hike-events.flow.json` | Hiking Hike Events |
| `components/salt-sensor/salt-sensor.flow.json` | Salt Sensor |
| `components/netalertx/netalertx.flow.json` | NetAlertX |

## Where flow files live

`core/node-red/` is reserved for genuinely cross-cutting infrastructure: the
shared MQTT broker config (`core.flow.json`) and the watchdog that monitors
every component's heartbeat regardless of type. Flows scoped to a single
integration or physical component live inside that component's own directory
instead, alongside its other docs — matching where every other component's
non-flow documentation already lives.

## After any change

Commit the updated JSON to keep the repo in sync with what's running on the Pi.
