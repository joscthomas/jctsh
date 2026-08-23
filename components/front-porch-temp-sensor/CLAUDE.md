# front-porch-temp-sensor — Context

## Card History

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 5639B, over the 5000B size threshold.

### CARD-0165 · [enhancement] [front-porch-temp-sensor] Ask Google Home for the front porch temperature — RESOLVED 2026-08-14
**Status:** Done

**Raised 2026-08-14, mid-CARD-0159 session.** Voice query — "Hey Google, what's the front porch temperature?" — should answer from the existing sensor, no new hardware.

**Confirmed low-effort, entity already exists and already in production use:** `sensor.front_porch_temp_sensor_temperature`, published via the `front-porch-temp-sensor` ESPHome component's MQTT discovery (`discovery_prefix: homeassistant` in `components/front-porch-temp-sensor/front-porch-temp-sensor.yaml`). Already consumed by two real HA automations (`automation-front-porch-cool-open-door.yaml`, `automation-front-porch-warm-close-door.yaml`), so the entity is known-reliable, not something to newly trust.

**Approach:** expose this one entity to Google Assistant via the Nabu Casa integration already active on this HA instance (Settings → Home Assistant Cloud → Google Assistant → expose entity) — no new integration, no SmartThings involvement, same mechanism CARD-0146/CARD-0164's research identified as available for voice-bridging without SmartThings as a middleman.

**Interview note (2026-08-14):** set a clean voice alias (e.g. "Front Porch Temperature") rather than exposing under the entity's auto-generated friendly name — Joseph's preference, for natural voice matching and a sensible spoken response. **Turned out unnecessary** — checked the entity registry directly and its `name` is already "Front Porch Temperature" (overriding `original_name: "Temperature"`), already clean for voice purposes.

**Built 2026-08-14 — exposure toggle done via HA's WebSocket admin API** (the entity-exposure setting lives in the entity registry's `options.cloud.google_assistant.should_expose` field, not reachable through the plain REST API — used the `homeassistant/expose_entity` WS command instead of the UI). Confirmed via the registry directly: `cloud.google_assistant.should_expose` flipped `false` → `true`. No manual "sync now" service exists in this HA version (`2026.8.1` — the old `cloud.google_actions_sync` service is gone from the `cloud` domain's service list); exposure changes appear to sync automatically now.

**Area assigned, 2026-08-14.** Checked and found neither the entity nor its parent device had an HA Area — meaning it would show up "unassigned" in the Google Home app and room-based phrasing wouldn't work (only the direct entity-name phrasing would). Assigned the parent device (`Front Porch Sensor`) to the area. **Real mistake caught and fixed in the same pass**: an exact-string area-name check missed the existing `Porch (Front)` area (already used by the doorbell/front-door entities) due to word-order difference, and created a duplicate `Front Porch` area instead. Caught immediately, device reassigned to the correct existing `Porch (Front)` area, duplicate deleted — confirmed via `area_name()` template that the entity now correctly resolves to `Porch (Front)`, no orphaned duplicate left behind.

**Real blocker found and fixed: Google Assistant was never actually linked to HA at all.** Checked HA Cloud's status directly (`cloud/status` over the WS API) — `"google_registered": false`. Nabu Casa Cloud itself was connected (remote access, SmartThings OAuth callback), but the Google Assistant link specifically — a separate one-time step inside the Google Home app itself (Settings → linked services → link "Home Assistant") — had never been completed. Every exposure/area change up to that point was real but inert, since nothing was actually syncing to Google. Joseph completed that linking step; the device then appeared in Google Home.

**Second issue, voice-query-specific: Google answered from the wrong device even with an exact name/phrase match.** Asking "what's the front porch temperature" (matching the device's exact Google-side name) kept answering with a pre-existing SmartThings front-door sensor's reading instead — confirmed that sensor is a SmartThings multi-purpose contact sensor (door open/close + temperature + battery), not Ring, and explicitly *not* exposed via HA's Google Assistant setting, so the collision wasn't an HA-side config problem. Root cause: Google Assistant appears to route temperature-type queries by room/context rather than literal device name, unlike most other device queries — confirmed by testing "what's the **porch** temperature" (dropping "front") and getting the correct answer. The word "front" itself was steering Google toward the front-door sensor via some room/primary-sensor association on Google's own side, outside HA's or this repo's control.

**Verified live, 2026-08-14 — Joseph confirmed "what's the porch temperature" correctly returns the front porch sensor's reading.** Satisfies the card's own "or a natural phrasing close to it" clause. The literal "front porch temperature" phrasing still collides with the SmartThings sensor on Google's side; not pursued further since a working natural phrasing already exists and the collision lives entirely in Google's room-routing logic, not anything this repo can fix.

**Done when:** "Hey Google, what's the front porch temperature?" (or a natural phrasing close to it) reliably returns the current reading, tested live, not just configured. ✅ — via "what's the porch temperature."

**Related:** `components/front-porch-temp-sensor/` (the existing sensor this exposes), CARD-0146/CARD-0164 (where Nabu Casa's Google Assistant bridge was identified as an alternative to SmartThings for reaching Google Home).

---
