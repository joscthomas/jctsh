# core/homeassistant — Context

## Card History

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 6781B, over the 5000B size threshold.

### CARD-0152 · [enhancement] [homeassistant] Expose Samsung Groom TV as its own HA device
**Status:** Done

**Raised 2026-08-12, follow-up from CARD-0150.** While closing out CARD-0150 (Traveling Mode TV alert), Joseph asked whether the Samsung TV should also be exposed as its own HA device rather than relying on the Chromecast (`media_player.groom_tv`) as a power-state proxy. Checked at the time: the TV is **not** registered in Joseph's SmartThings account, so the low-effort "enable exposure on the existing SmartThings integration" path (same pattern used for the salt-sensor switches) isn't available — the only route is HA's native Samsung TV integration (WebSocket, added by IP address, requiring a one-time pairing prompt accepted directly on the TV).

**Interviewed:** two motivations, both wanted —
1. **More reliable signal.** The Chromecast entity has proven noisy for alerting purposes during CARD-0150's testing: it churns through `playing`/`idle`/`paused`/`buffering` constantly during real use, and was directly observed dropping to `unavailable` for ~67s during confirmed active use (a Cast-protocol connectivity blip, not a real power change) — CARD-0150's automation had to build a delay-then-recheck debounce specifically to tolerate this. A direct TV entity should give a cleaner, more authoritative on/off signal.
2. **Remote control from HA.** Right now, CARD-0150's alert only notifies Joseph, who has to go turn the TV off himself via Google Home. Joseph wants HA to be able to actually turn the TV off itself when it detects an unexpected-on event, not just notify.

**Pairing readiness confirmed:** Joseph is ready to do the on-TV pairing step (physically at the TV with the remote) whenever this gets built — not a blocker.

**Open design questions for Planning:**
- Does the new TV entity **replace** `media_player.groom_tv` as CARD-0150's alert trigger, or does it supplement it (e.g. cross-check both before alerting)? Leans toward replace, given the whole point is a cleaner signal, but worth confirming once the new entity's real behavior is seen firsthand — no guarantee the native Samsung TV integration is itself perfectly clean (worth the same live-testing rigor CARD-0150 needed).
- Auto-remediation behavior: should the automation turn the TV off **immediately** on detecting an unexpected-on event, after some delay/confirmation, or still leave it as a manual step Joseph takes after the notification? This is a real behavior change from CARD-0150's notify-only design and needs a decision, not just an assumption.
- Does turning the TV off via the new integration also need to go through the same debounce/settle logic CARD-0150 built, or does a direct TV entity avoid that problem entirely (unknown until it's actually tested live)?

**Built 2026-08-12:** two integrations ended up involved, not one —
1. HA had already auto-discovered the TV via SSDP as a `dlna_dmr` (DLNA Digital Media Renderer) entry; Joseph enabled it, creating `media_player.tv_samsung_7_series_75`. Checked in the UI: playback controls only (play/pause/volume), no power control — DLNA doesn't expose that.
2. Added HA's native **Samsung Smart TV** (WebSocket) integration separately, manually, via IP (`192.168.1.152`) — Joseph completed the one-time pairing prompt on the TV itself. Created `media_player.tv_samsung_7_series_75_2` (the `_2` suffix is auto-generated, from the object-id collision with the DLNA entity above) and `remote.tv_samsung_7_series_75`. Confirmed via the recorder DB: reports a clean, plain `on` state — no playing/idle/paused churn like the Chromecast. Confirmed in the UI: has a real power/turn-off button, unlike the DLNA entity.

**Scope changed on Joseph's second thought, same session: CARD-0150's automation is staying exactly as it is — not wired to either new entity.** Reason: `media_player.groom_tv` (the Chromecast) also controls the AVR, a relationship the new Samsung TV entity doesn't capture — switching the trigger over would lose that. `core/homeassistant/automations.yaml` was not touched. Both new entities now exist in HA (confirmed working, on/off signal validated, turn-off capability confirmed) but aren't consumed by any automation yet.

**Done when:** revised down from the original scope — the TV is exposed as its own HA device with a working on/off signal and turn-off control, both confirmed for real (not just "added without errors"). **Met.** The CARD-0150 integration work (trigger swap, auto-remediation) is explicitly out of scope now per Joseph's call above; revisit under a fresh card if the Chromecast/AVR relationship is later understood well enough to combine both signals safely.

**Follow-up, same session:** the Samsung Smart TV integration's config entry pins a fixed IP (`192.168.1.152`) and MAC (`84:c0:ef:d8:5f:fb`) with no DHCP reservation on the router yet — if the TV's IP changes, the integration breaks silently. Joseph asked to reserve it; needs to be done on the router admin UI (`192.168.1.1`, TP-Link Archer AXE75) directly, no access to that from this session. Once reserved, add the entry to `jctsh-network.md` alongside the other reserved devices.

**Joseph also added the Denon AVR-X6400H to HA, same session** — auto-discovered via SSDP (`denonavr` integration), entity `media_player.avr`, confirmed reporting a clean plain `on` state like the new Samsung TV entity. This is the same AVR referenced in the "leave the automation alone" decision above (the Chromecast controls it). Same DHCP-reservation gap applies: fixed IP `192.168.1.204`, MAC `00:05:cd:e4:58:3e` (pulled from the Pi's ARP cache, since `denonavr` doesn't populate MAC into HA's device registry) — needs reserving on the router alongside the TV's.

**Both reserved on the router and recorded in `jctsh-network.md`, same session.** No longer a loose end.

**Closed out 2026-08-12 on Joseph's go-ahead.** Scope ended up smaller than raised — the TV is exposed and both new entities (playback via DLNA, real on/off + power control via the native Samsung Smart TV integration) are confirmed working for real, but per Joseph's own call mid-build, none of it got wired into CARD-0150's alert automation, since the Chromecast already captures the TV+AVR relationship as a single signal and switching away from it would lose that. Both the TV and the newly-added Denon AVR are DHCP-reserved and documented in `jctsh-network.md`. Reopens under a fresh card if the Chromecast/AVR relationship is ever understood well enough to safely combine signals, or if either new entity turns out to need its own live-testing rigor the way CARD-0150's did.

**Related:** CARD-0150 (the TV alert automation this was originally meant to extend, ultimately left untouched), `jctsh-network.md`.

---
