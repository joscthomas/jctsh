# garage-radar — Card Archive

Historical record of archived Done/Defer kanban cards for this component (CARD-0193). Not read as part of routine Session Start or component/cluster-session startup (JCTsh-Component-Session-Start.md) -- on-demand lookup only. See this component's own CLAUDE.md for current, curated context.

## Card History

**Archived from `tos/kanban-board.md` on 2026-09-18 (CARD-0193)** — 5500B, over the 5000B size threshold.

### CARD-0281 · [bug] [garage-radar] Dashboard logging silent 2026-06-15 to ~09-10, self-recovered on its own reboot — RESOLVED 2026-09-17 (self-recovered, root cause unconfirmed)

**Status:** Done

**Raised 2026-09-17 (Claude), found while auditing Node-RED tabs for tab-scoped credentials (CARD-0280) — a real device gap, not related to that credential audit itself.** The live Node-RED instance has no "Garage Radar" tab at all (confirmed via the admin API, `GET /flows`), even though `components/garage-radar/garage-radar.flow.json` exists in the repo and is documented in `Node-RED-workflow.md`'s tab-mapping table. Separately, the Pi's durable dashboard log (`/mnt/jctsh-logs/jctsh.log*`) shows **zero log entries from `garage-radar` since 2026-06-15** — three months of silence, no watchdog "silent" alerts either after that date (odd on its own, since the watchdog should keep alerting on an unconditional heartbeat regardless of presence activity).

**Confirmed by Joseph: the device is physically installed and working great**, including `switch.garage_presence_vswitch` in SmartThings — so this is not a dead/decommissioned device. Its core presence function (LD2412 radar → HA automation → SmartThings) doesn't depend on Node-RED or the JCTsh log dashboard at all — that path is real and unaffected.

**What's been checked, and what doesn't (yet) explain it:**
- `components/garage-radar/garage-radar.yaml`'s own comment claims `/log` messages are "routed by Node-RED to log server" — but `core/logging/log_server.py` subscribes directly via `jctsh/+/+/log` (a two-level wildcard), which matches `jctsh/components/garage-radar/log` with no Node-RED involvement needed. This comment is very likely stale documentation from before the direct-subscribe wildcard existed, not a real explanation — every other component's logs reach the dashboard this way with no Node-RED tab required for that specific function.
- The missing Node-RED tab's git history (`git log -- components/garage-radar/garage-radar.flow.json`) shows only one commit, 2026-07-10, backfilling a file "that existed on disk since the component's original build but was never added to version control" — doesn't establish when or why the live tab itself disappeared from Node-RED, only that the repo copy was untracked for a while.
- garage-radar's Node-RED tab's own code (`fn_build_st_request`-style functions) appears to target writing to a SmartThings virtual switch directly — plausibly redundant/superseded once the presence chain moved to HA-native automation (per `garage-radar/integration-notes.md`'s documented chain: radar → HA automation → vswitch), which could explain the tab being deliberately retired at some point without anyone connecting that to the dashboard-logging side effect.

**Resolved via a live MQTT trace, 2026-09-17 — the device is actually healthy right now, not broken.** Subscribed directly to `jctsh/components/garage-radar/#` (via the `jctsh-log-server` MQTT account, documented as the general-purpose CLI subscriber) while Joseph physically triggered the radar. A real `/log` message fired and was captured live: `{"component":"garage-radar","category":"Sensor","message":"Presence detected (distance: 0.8m, still: ON, moving: OFF)"}` — and it landed in the dashboard within seconds, confirmed both via `jctsh.log` and the live `/status` page (`garage-radar | Connected | Online | heartbeat 18m ago | Presence ... 3m ago`). A heartbeat message read live off the dashboard showed `uptime: 162h 29m` as of 12:30:58 MST — meaning the device's last boot was roughly 2026-09-10, and it has been reporting correctly and continuously since.

**Real timeline, corrected from this card's original framing:** silent 2026-06-15 to roughly 2026-09-10 (~87 days) for an unknown reason, then healthy since a reboot around 09-10 — not an ongoing, currently-active bug. **Root cause of the original ~87-day gap not established and likely not recoverable** — nothing logged during a silent window, by definition, leaves no diagnostic trail to examine after the fact.

**Real methodology lesson from this card, folded into CARD-0282:** the original "3 months of silence" finding came from grepping the raw `jctsh.log` file directly, not checking the live `/status` dashboard — an already-documented project convention (raw log only reflects a flush trigger, not live state) that wasn't applied here and produced a stale, misleading picture. The Node-RED-tab question (also raised in this card's original framing) remains genuinely unexplained but is now understood to be unrelated to dashboard logging at all (confirmed: `log_server.py` subscribes directly via MQTT wildcard, no Node-RED relay needed) — not reopened as its own investigation since the SmartThings-writing function that tab likely existed for appears superseded by HA-native automation already, per `garage-radar/integration-notes.md`.

**Done when:** the device is confirmed currently healthy (not "still broken") — **met**. Root cause of the historical gap — **not established, accepted as likely unrecoverable, not blocking closure** (Joseph's call).

**Related:** CARD-0280 (the credential audit that surfaced this as a side finding), CARD-0282 (the Session Start dashboard-check methodology fix this directly motivated), `components/garage-radar/garage-radar.yaml`, `components/garage-radar/garage-radar.flow.json`, `Node-RED-workflow.md`, `core/logging/log_server.py` (`MQTT_TOPIC`).

---
