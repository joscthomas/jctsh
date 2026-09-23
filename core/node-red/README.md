# core/node-red — Node-RED Settings and Core Flows

Version-controlled copies of the Node-RED configuration running on the Pi (`pi1.local:1880`).
Node-RED is the "brain" (root `CLAUDE.md`): it subscribes to component topics, applies logic, and routes
log messages to the Python log server.

**Status:** Production.

## Files

| File | Purpose |
|---|---|
| `core.flow.json` | The shared MQTT broker config node (`mqtt_broker`) — import first when re-importing flows; every other flow depends on it |
| `watchdog.flow.json` | Component heartbeat watchdog — see `watchdog-README.md` |
| `settings.js` | Node-RED settings, deployed to `/home/pi/.node-red/settings.js`. Contains a bcrypt password hash |

Other components keep their own flow file next to their code (`components/<name>/<name>.flow.json`,
`core/data-pipeline/environmental-data.flow.json`); this directory only holds the core ones.

## How live differs from the repo

The repo keeps one `*.flow.json` per flow, but the live instance keeps every flow merged in a single
`/home/pi/.node-red/flows.json`, so the two don't map file-to-file. Node ids are usually preserved on
import, but not always: the live `Environmental Data` tab has a different id than its repo file, and the Hike Events
flow's repo file has no tab node at all — so matching a live tab to a repo file needs its label or member node ids, not just the tab id.
Node-RED also adds load-time default properties (e.g. `inputs: 0`) to nodes it loads.

**`flows.json` is not secret-free.** Node-RED's own `global-config` node stores its environment variables there,
including a Home Assistant access token, in plaintext, and the file is world-readable on the Pi. Flow credentials
proper live in the separate encrypted `flows_cred.json`. Nothing that reads `flows.json` should print
`global-config`.

## Deploying a flow change

`deploy_flow.py` pushes one tab from a repo flow file to the live instance through Node-RED's Admin API
(what CARD-0331 did by hand), from **your own terminal** — it prompts for the admin password and never
writes it anywhere, since a Claude Code session isn't allowed to read that credential:

```
python core/node-red/deploy_flow.py core/node-red/watchdog.flow.json tab_watchdog [--trigger <inject-id>]
```

It shows which node ids would be added/changed/removed, asks to confirm, replaces only that tab, then
re-fetches and verifies every function node's code matches the repo. Replacing a tab restarts that flow,
so in-memory state (the watchdog's silence timers) resets. Commit the flow file to `main` only *after*
deploying, or the daily drift check flags repo != live.

## Drift Check

`settings.js`, `core.flow.json` and `watchdog.flow.json` are checked daily against the live instance by
`core/maintenance/config-drift-check.py` (CARD-0328): flow files are compared node-by-node by id (editor x/y
ignored), and a live tab or config node that no repo flow file contains is reported too. Secrets are masked and
`global-config` is never compared or shown. A live edit that never came back here opens a kanban PR.
By hand: `ssh pi@pi1.local "sudo python3 /usr/local/bin/config-drift-check.py --dry-run"`.