# garage-presence — Card Archive

Historical record of archived Done/Defer kanban cards for this component (CARD-0193). Not read as part of routine Session Start or component/cluster-session startup (JCTsh-Component-Session-Start.md) -- on-demand lookup only. See this component's own CLAUDE.md for current, curated context.

## Card History

**Archived from `tos/kanban-board.md` on 2026-09-28 (CARD-0193)** — 3829B, over the 2000B size threshold.

### CARD-0055 · [bug] [garage-presence] Reconcile garage-radar/SmartThings light control — lights sometimes don't turn on — RESOLVED 2026-09-12 MST (Joseph's call)
**Status:** Done

**Closed 2026-09-12 — no longer a problem, especially when the SmartThings/HA integration is working, or refreshed if it isn't.** This matches the already-documented, generic pattern in root `CLAUDE.md`'s "Post-update entity-availability check" (and CARD-0240's own precedent): a SmartThings config entry can report `state: loaded` without actually having resynced its entities — including, presumably, the vswitch state the "presence on" lights routine depends on — and a manual `POST /api/config/config_entries/entry/<id>/reload` clears it. The intermittent "lights sometimes don't come on" symptom is consistent with this known sync-staleness class of issue rather than a distinct routine-logic bug worth auditing separately. The original audit plan (capture the undocumented SmartThings "presence on" routine, correlate HA/ST history on a real failure) is no longer needed — reload-when-it-happens is the accepted fix.

**Notes:** Joseph reports lights sometimes don't come on when entering the garage. Found during a components-vs-backlog reconciliation pass (2026-07-11): the repo fully documents the "presence off" SmartThings routine (closes door, turns off lights — `garage-presence/CLAUDE.md`) but has **no documentation anywhere of the "presence on" routine** presumably responsible for turning lights on when `switch.garage_presence_vswitch` turns on. `garage-radar/README.md` and `garage-presence/README.md` both reference "lights on" only as an outcome label on the vswitch, never as a documented ST routine with its own trigger/conditions — it exists only inside the SmartThings app, unaudited.

**Known chain (from `garage-radar/integration-notes.md`):** LD2412 radar → `binary_sensor.garage_radar_presence` (30s `delayed_off` filter) → triggers HA's "Garage Presence - Restart timer on activity" automation → starts `timer.garage_presence_timer` and turns on `switch.garage_presence_vswitch` → HA is the sole owner of the vswitch state (SmartThings routines must not set it directly, since ST→HA sync is documented unreliable for other sensors — `garage-presence/CLAUDE.md`) → SmartThings observes the vswitch turning on and is presumed to fire a "lights on" routine, which is undocumented and unverified.

**Suspected failure points (not yet confirmed):**
- HA→SmartThings state propagation lag/unreliability for the vswitch itself — existing docs only warn about the *reverse* direction (ST→HA sync unreliable for `binary_sensor.back_door_door` and the PIR motion sensors); nothing confirms the HA→ST direction this flow actually depends on is solid.
- Radar/PIR detection gaps delaying the first `binary_sensor.garage_radar_presence` → on transition (same class of issue already documented for `binary_sensor.garage_motion_motion`/`garage_cam_motion` sticking in Arizona heat).
- Whatever conditions the SmartThings "presence on" routine actually has configured today — unknown, never captured in the repo.

**Resolution path:** (1) audit the SmartThings app directly to capture and document the actual "presence on"/lights-on routine (trigger, conditions, actions), mirroring how the "presence off" routine is already documented in `garage-presence/CLAUDE.md`; (2) next time lights fail to come on, correlate HA logbook history for `switch.garage_presence_vswitch` against SmartThings app history to determine whether the vswitch turned on but ST didn't react, or the vswitch itself never turned on; (3) once root cause is identified, fix it (likely an ST routine condition or a sync-timing issue) and add the missing documentation so this chain is fully traceable end to end.

---
