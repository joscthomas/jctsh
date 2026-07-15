# JCTsh Node-RED NetAlertX Translator

Translates NetAlertX's raw `system-sensors/#` MQTT firehose into JCTsh-shaped log
events, and gives NetAlertX a heartbeat so it stops showing `?` on the log
dashboard's Device Status page.

---

## Why This Exists (CARD-0063)

NetAlertX's own MQTT publisher (`system-sensors/#`) re-publishes the full device
list on every scan cycle — roughly 95 messages per cycle regardless of whether
anything actually changed. Mirroring that straight into `jctsh/components/netalertx/log`
would flood the log dashboard with noise. This flow diffs against cached prior
state and only republishes real transitions:

- A device's presence flips online ↔ offline
- A device NetAlertX has flagged `is_new` shows up for the first time

It also closes the `?`-status gap: `core/logging/log_server.py` marks a component
`?` until it sees a `Heartbeat - `-prefixed message on its log topic (or a message
on `jctsh/+/+/heartbeat`, which the watchdog flow also needs). NetAlertX itself
never publishes anything heartbeat-shaped, so without this flow it can never leave
`?`.

---

## How It Works

1. **Transition detection** — two `mqtt in` nodes subscribe to NetAlertX's raw
   topics:
   - `system-sensors/sensor/+/state` — per-device attributes (vendor, model,
     `is_new`, `last_ip`, ...) plus one aggregate topic (`.../sensor/netalertx/state`,
     scan-wide counts). `fn_device_info` tells them apart by the topic segment:
     `netalertx` → aggregate, cached for the heartbeat; `mac_xx_...` → per-device,
     cached for labeling and checked for a `is_new` transition.
   - `system-sensors/binary_sensor/+/state` — per-device `is_present` ON/OFF.
     `fn_presence` diffs each device's state against what's cached in Node-RED
     context and only emits a message on an actual flip. The very first sighting
     of a device (e.g. right after a Node-RED restart) just establishes the
     baseline — it does not log a "came online" burst for every known device.
2. **Heartbeat** — an `inject` node fires every 5 minutes (matching every other
   JCTsh component's cadence, and the watchdog's 35-minute / 7-heartbeat timeout).
   `fn_heartbeat` builds a `Heartbeat - <N online, N down, N total>` log message
   from the cached aggregate stats, plus a small JSON payload to
   `jctsh/components/netalertx/heartbeat` for the watchdog's wildcard subscription
   to pick up.

Everything is diff/cache-based via Node-RED's built-in `flow` context store —
deliberately `flow.get`/`flow.set`, not the per-node-private `context.get`/`set`
default, since the cache is written by one function node (`fn_device_info`) and
read by others (`fn_presence`, `fn_heartbeat`). `flow` context resets on Node-RED
restart — see "First sighting after restart" below.

---

## Flow: `components/netalertx/netalertx.flow.json`

```
system-sensors/sensor/+/state ──► fn_device_info ──► [new-device only] ──┐
                                    (caches attrs,                       │
                                     caches agg stats)                   │
                                                                          ├──► jctsh/components/netalertx/log
system-sensors/binary_sensor/+/state ──► fn_presence ──► [flip only] ────┘
                                    (diffs is_present)

inject (5 min) ──► fn_heartbeat ──┬──► jctsh/components/netalertx/log       (Heartbeat - ...)
                                   └──► jctsh/components/netalertx/heartbeat (picked up by watchdog)
```

---

## Message Shapes

**Heartbeat — every 5 minutes, always, regardless of activity.** Proof-of-life for
the watchdog and the Device Status page; nothing to act on day to day.
```json
{ "component": "netalertx", "category": "System", "message": "Heartbeat - 37 online, 0 down, 47 total" }
```

**Presence transition — only on a real flip, not every scan cycle.** Name comes
from NetAlertX's own vendor/model field if cached for that device yet, otherwise
falls back to the raw MAC.
```json
{ "component": "netalertx", "category": "System", "message": "Front Porch Sensor (b4:bf:e9:c9:ef:68) came online" }
{ "component": "netalertx", "category": "System", "message": "Ring Doorbell (3c:a3:08:03:f9:b4) went offline" }
```

**New device — the one actually worth looking at.** `Alert` category (not
`System`), fires once per `is_new` flag; can fire again later if NetAlertX clears
and later re-sets `is_new` for that MAC (e.g. re-discovered after being archived).
```json
{ "component": "netalertx", "category": "Alert", "message": "New device detected: <model|vendor> (<mac>, <ip>)" }
```

All of the above land on the main log dashboard (`/`) next to every other
component, and the aggregate Online/Offline classification on the Device Status
page (`/status`) is driven purely by heartbeat recency — nothing else to check
there day to day.

---

## Configuration

Nothing to configure in Node-RED beyond importing the flow — it uses the shared
`mqtt_broker` config node from `core.flow.json` (must already be imported).

On the NetAlertX side (already done live for CARD-0063's MQTT test, see
`components/netalertx/naming-workflow.md` history): Settings → Publishers → MQTT
must be enabled with `MQTT_RUN = always_after_scan`, broker `localhost:1883`,
credentials from `credentials.local.md` (`netalertx` account).

---

## Adding This to the Watchdog

Nothing to do — same as any other component. The watchdog's `jctsh/+/+/heartbeat`
wildcard picks up `jctsh/components/netalertx/heartbeat` automatically once this
flow is deployed.

---

## Testing

1. Deploy the flow in Node-RED, confirm no red "missing config" badges on either
   `mqtt in` node (broker `mqtt_broker` must resolve — import `core.flow.json` first
   if not already present).
2. Watch the `debug: log output` node in the Node-RED debug sidebar through one
   full NetAlertX scan cycle — expect silence unless a device's presence actually
   changed, plus one heartbeat every 5 minutes.
3. Confirm on the log dashboard (`/`) that `netalertx` starts showing entries and,
   after up to 5 minutes, the Device Status page (`/status`) no longer shows `?`
   for it.
4. To force a transition for testing: temporarily block a known device's traffic
   (e.g. disconnect its Wi-Fi) and wait for the next NetAlertX scan cycle; confirm
   an offline message appears, then reconnect and confirm the online message.

---

## Troubleshooting

| Symptom | Check |
|---|---|
| Still shows `?` on Device Status | Confirm `jctsh/components/netalertx/heartbeat` is actually being published — check Node-RED debug sidebar; confirm `inject_heartbeat` is not disabled |
| No transition messages ever | Confirm NetAlertX MQTT publisher is enabled and `MQTT_RUN=always_after_scan`; check Node-RED debug panel for raw `system-sensors/#` traffic arriving at all |
| Every device shows "came online" right after a Node-RED deploy/restart | Expected — `flow` context resets on restart, so the first per-device message after that is treated as a new baseline, not a transition. Confirm no message logged, only the baseline set silently |
| New-device alert doesn't fire | Check NetAlertX is actually setting `is_new` on that device in its own DB/UI; `newflag_<mac>` in `flow` context blocks a repeat alert until NetAlertX clears `is_new` |
| Heartbeat stats show "no scan data yet" indefinitely | Aggregate topic `system-sensors/sensor/netalertx/state` never arrived — confirm NetAlertX's MQTT plugin publishes it (it does on every `always_after_scan` cycle) |
| Presence messages show a raw MAC instead of a device name | Expected until a `sensor/mac_xx/state` message has landed for that device this session (populates the name cache) — self-corrects on the next scan cycle |
| `"Bad JSON on ..."` warnings in the debug sidebar for every message | Regression of a real bug hit during CARD-0063's initial deploy: the `mqtt in` nodes use `datatype: "auto-detect"`, which already parses valid JSON into an object — re-parsing with `JSON.parse()` throws. Fix already in the flow (only parse `if (typeof payload === 'string')`); if this reappears after an edit, check that guard wasn't removed |
| Heartbeat/labels silently stay stale despite messages clearly arriving in the debug sidebar | Regression of a second real bug: `context.get`/`context.set` inside a function node default to that *node's own private* store, not something other nodes can read. `agg_stats` and `devinfo_<mac>` are written by `fn_device_info` and read by different nodes (`fn_heartbeat`, `fn_presence`) — they must use `flow.get`/`flow.set`, not `context.get`/`context.set`. If someone reintroduces `context.*` for these keys, the symptom is exactly what CARD-0063 hit: heartbeat stuck on "no scan data yet," transitions showing raw MACs, despite no errors anywhere |
