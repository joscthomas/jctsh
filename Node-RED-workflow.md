# Node-RED Flow Update Workflow

## Editing a function node (code-only changes)

Skip import entirely — edit in place:

1. Double-click the function node in Node-RED
2. Edit the code
3. Done → Deploy
4. Export the flow back to the repo: Hamburger → Export → Download → overwrite the file under `core/node-red/`

## Replacing an entire flow (structural changes, new nodes)

The import dialog's "Import copy" option creates duplicates — don't use it. Instead:

1. Click the tab containing the flow
2. Ctrl+A → Delete → **Deploy** (clears the tab without removing the tab itself)
3. Hamburger → Import → select file → **"current flow"** → Import
4. Deploy

This avoids conflicts because the old nodes are gone before the import runs. The broker node (in `core.flow`) keeps its ID, so MQTT nodes re-attach automatically.

## Identifying which flow a JSON file belongs to

The flow JSON files in `core/node-red/` don't include a tab name. Match by filename:

| File | Node-RED tab |
|---|---|
| `core.flow.json` | Core (import first — contains the MQTT broker node) |
| `watchdog.flow.json` | Watchdog |
| `core/data-pipeline/environmental-data.flow.json` | Environmental Data |

## After any change

Commit the updated JSON to keep the repo in sync with what's running on the Pi. Core and watchdog flows live in `core/node-red/`; the environmental data flow lives in `core/data-pipeline/`.
