# core/node-red — Card Archive

Historical record of archived Done/Defer kanban cards for this component (CARD-0193). Not read as part of routine Session Start or component/cluster-session startup (JCTsh-Component-Session-Start.md) -- on-demand lookup only. See this component's own CLAUDE.md for current, curated context.

## Card History

### CARD-0328 · [enhancement] [mqtt] [node-red] [homeassistant] Version-controlled-copy directories have no drift check — generalize CARD-0326's one-line diff

Archived in full to `core/mqtt/card-archive.md` on 2026-09-27 (CARD-0193) — 19459B, over the 5000B size threshold. Also tagged here; this is a pointer only, not a duplicate.

**Archived from `tos/kanban-board.md` on 2026-09-28 (CARD-0193)** — 2609B, over the 2000B size threshold.

### CARD-0339 · [bug] [node-red] AQM buffered event lines (`wifi_attempt_start`) were mistaken for readings -- surfaced as "undefined reading @ undefined" alerts

**Status:** Done -- RESOLVED 2026-09-25 16:22 MST

**Found 2026-09-25 (Joseph: "do we have a card?" after the AQM capture test).** During the CARD-0226 incident, two `node-red` Alerts read `GPS lookup failed ... for undefined reading @ undefined` (11:35) and `Environmental Data POST failed for undefined reading @ undefined` (13:05). The first was timed to the AQM's replay at 11:29:45 (three 2-minute GPS-lookup timeouts later). A live capture on 2026-09-25 16:18 MST -- subscribing to `jctsh/components/air-quality-monitor/#`, then publishing to the AQM's `command/replay` topic -- showed the AQM's buffered log holds **`{"event":"wifi_attempt_start"}` event lines, not readings**, which its replay publishes on `/data`. The Node-RED router (`env-data-route-skip-reset`) only knew the hiking-monitor's `skip`/`reset`/`display_refresh` events, so an AQM event fell through as a reading with no `component` or `ts`.

**Fixed and deployed 2026-09-25 (commit `eee0b70`):** the router now turns *any* `{"event": ...}` record into a System log line on that component's own `/log` topic (`Device event: {...}`), and drops anything that has neither an event nor `component` + `ts` with an Alert naming the topic and the first 140 characters of the payload (readings carry no secrets), instead of letting it travel the pipeline. Mock-tested across the AQM event, the three hiking-monitor events, a good reading, and a reading with no `ts`. Side result of the same capture: the AQM's `command/replay` topic and log retention work (`Replaying 2 buffered readings...` after an earlier replay, then `Buffered-data replay complete.`).

**Watch for (RESOLVED 2026-09-25 16:22 MST, see below):** the AQM's next replay after a connect (or a `command/replay`) logging `Device event: {"event":"wifi_attempt_start"}` as **System** lines on its own log with **no** `Dropped a /data message` Alert -- that confirms the live deploy; not yet observed after the second deploy.

**Related:** CARD-0226 (the incident that exposed it), CARD-0012 (the AQM's own log-retention port, flashed 2026-09-25), `core/data-pipeline/environmental-data.flow.json`.


**Verified live 2026-09-25 16:22 MST:** a second `command/replay` capture after the final router deploy showed the AQM's two `wifi_attempt_start` lines arriving on `/data` and appearing on its own log as `Device event: {"event":"wifi_attempt_start"}` (category System) with no `Dropped a /data message` Alert.
---

**Archived from `tos/kanban-board.md` on 2026-09-28 (CARD-0193)** — 3796B, over the 2000B size threshold.

### CARD-0331 · [bug] [node-red] Watchdog silence alert fires once and never re-alerts -- badly understates real outage duration

**Status:** Done — RESOLVED 2026-09-23

**Raised 2026-09-22 16:13 MST, found live cross-checking a "back-patio-temp-sensor silent for 35 minutes" alert against the Pi's actual log (the porch/patio component session, `jctsh-6a`, and the general session working together).** The real outage was **~15h53m** (2026-09-21 16:42:25 -> 2026-09-22 08:35:19), not the ~35 minutes the alert text implies -- the watchdog (`core/node-red/watchdog.flow.json`, `fn_timer_manager`'s per-component silence timers) only ever fires once, at the 35-minute threshold, and never re-alerts while a component stays down. As currently designed, a device down for 35 minutes and a device down for 16 hours are indistinguishable from the alert stream alone. **Correction, 2026-09-22 (folded in after `jctsh-6a` verified live on CARD-0219):** this card originally also cited a second, ~55min same-day gap (14:44-15:39) as a corroborating instance -- that one wasn't an unexplained dropout at all, it was Joseph's own BME280 physical swap and reboot, and it still produced the identical generic one-line alert text despite being a known, deliberate event. Kept as a weaker supporting data point (even a known-cause restart gets the same undifferentiated alert), not as a second real mystery -- the 2026-09-21 overnight ~15h53m gap is this card's actual motivating evidence. Full incident detail lives on CARD-0219, not repeated here.

**Interviewed 2026-09-23 (Joseph) -- two decisions:**
1. **Fix direction: periodic re-alert** (not duration-on-recovery, not both) -- keep re-firing while a component stays silent, until it recovers.
2. **Interval: every 2 hours.**

**Built and deployed, 2026-09-23:**
1. `core/node-red/watchdog.flow.json`, `fn_timer_manager`: on heartbeat receipt, now clears both the 35-min silence timer *and* any active re-alert interval (needed so a component that recovers mid-outage stops getting "still silent" pushes). When the 35-min timer fires, it now also starts a `setInterval` (2h) that re-sends every 2 hours while still silent, carrying the accumulated downtime in minutes -- cleared the moment a heartbeat arrives.
2. `fn_build_alert`: now branches on payload shape -- a plain component-name string (the original 35-min alert, unchanged wording) vs. an object carrying `component`/`downtimeMinutes` (a repeat alert, worded "still silent -- down 2h15m" via a new `formatDuration()` helper).
3. `watchdog-README.md`: updated How It Works, Alert Message, and Testing sections to document the repeat-alert behavior and its message format.

**Deployed live via Node-RED's Admin API** (`PUT /flow/tab_watchdog`, not a manual UI import) -- fetched the live flow, applied the same two function-node edits, pushed back, confirmed 200 and re-fetched to verify the new code is what's actually running on the Pi. A function-node syntax error would have failed this deploy outright, so the successful PUT is itself a validity check, not just a file write.

**Not independently verified end-to-end** (a real multi-hour outage, confirming an actual repeat push arrives on the Pixel with correct wording) -- that requires either a real outage or a manual timer-shortening test per the README's own Testing section, neither performed this session. The mechanism is deployed and live; a real silent-component event is this feature's next real test.

**Related:** CARD-0219 (the concrete incident this generalizes from), `core/node-red/watchdog.flow.json` / `watchdog-README.md` (the mechanism itself), CARD-0330 (found and fixed in the same session, unrelated mechanism -- that one's the Session Start credential gap, this one's the watchdog's own alerting design).

---

