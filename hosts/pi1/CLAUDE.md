# hosts/pi1 — Context

## Card History

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 7237B, over the 5000B size threshold.

### CARD-0060 · [bug] [pi1] Pi running in active soft thermal throttling &mdash; no cooling &mdash; RESOLVED 2026-07-15
**Status:** Done

**Notes:** Found 2026-07-12 during a Pi health evaluation. `vcgencmd get_throttled` returns `0x80008` (bit 3: soft temperature limit *currently active*; bit 19: has occurred) at a measured 63&ndash;64&deg;C, confirmed on two separate checks. No under-voltage bits set &mdash; power supply is fine, this is purely thermal. No heatsink/fan apparent on this Pi 3B+. Likely compounded by an enclosed/warm install location, matching the pattern of other JCTsh closet-installed devices (photo-server M8, KeepConnect).

**Impact:** the Pi is right now running with reduced ARM clock speed to manage heat. Not causing instability (uptime is solid, no OOM/crash pattern), but is a real, currently-active performance ceiling on the device that hosts Home Assistant, Node-RED, Mosquitto, and the JCTsh log/watchdog server for the whole fleet.

**Location context (2026-07-12):** the Pi sits on a shelf near a 9-foot ceiling in the laundry room, in a plastic case of unknown internal heatsink status &mdash; Joseph doesn't want to open the case to check/add an internal heatsink. Chose an external-airflow approach instead of a case teardown: some of the heat load is plausibly ambient hot air pooling at ceiling height (heat rises) rather than purely the case trapping the Pi's own heat, so moving air across the whole shelf addresses both causes at once and benefits every device up there, not just the Pi.

**Resolution path (revised, no disassembly):** install a continuous-duty USB-powered fan on the shelf, aimed to move air across the shelf and out toward open room space (not just recirculate warm air in place against the ceiling). Recommended: **AC Infinity MULTIFAN S5** (single 80mm, ~52 CFM, dual ball bearings rated ~67,000 hours/~7.6 years continuous duty, USB powered, includes speed controller) &mdash; purpose-built for quiet electronics-cabinet cooling, enough real airflow to matter across an open shelf, unlike gentler terrarium-style USB fans. Step up to the **MULTIFAN S7** (multi-fan set) if one fan's throw doesn't cover the full shelf width. Power the fan from its own USB wall adapter or hub, not from the Pi's own USB ports, to avoid adding current draw to the Pi's own power rail (it currently shows no under-voltage flags &mdash; keep it that way). One ongoing maintenance item: it's a laundry room, so dryer lint will accumulate on the fan grille/blades over months of continuous running &mdash; an occasional wipe-down keeps airflow effective.

**Don't close until:** fan is physically installed and `vcgencmd get_throttled` is re-checked under normal and sustained-load conditions, confirming bit 3 ("soft temperature limit currently active") clears. **Holding verification until Joseph has the fan in place** &mdash; not yet done.

**Pre-install baseline (2026-07-14):** checked temps across the equipment shelf before the fan goes in, both to confirm the Pi's condition is unchanged and as a data point on the shelf-wide-heat-pooling theory.

- **Pi:** 64.5&deg;C, `throttled=0x80008` &mdash; unchanged from the 2026-07-12 finding, still actively soft-throttling.
- **M8 (photo-server), also on this shelf:** running well within normal range &mdash; CPU (real `k10temp` sensor, not the unreliable `acpitz` dummy) 39.3&deg;C, NVMe 40.9/41.9/33.9&deg;C, GPU 38.0&deg;C, 2.5GbE controllers 39.5/43.5&deg;C, WiFi 6E 38.0&deg;C. Worth noting against the shelf-wide-heat-pooling theory: if ambient heat pooling at ceiling height were the dominant factor, expected the M8 to be running warmer too. Doesn't rule the theory out &mdash; the Pi's plastic case with no heatsink at all is far more heat-sensitive than the M8's own active cooling &mdash; but the M8 isn't showing any distress from the shared shelf environment.
- **External USB HDDs (Backup Plus, Momentus, spare Seagate) &mdash; could not check:** needs `smartctl`, not installed; `sudo` on the M8's `jct` account requires an interactive password not available here.
- **Router (TP-Link Archer AXE75) &mdash; could not check:** no SSH/API access on this consumer router; admin web UI already confirmed undrivable via browser automation during CARD-0003.

**Post-install check (2026-07-14, a few hours after fan install):** significant improvement.

- **Pi:** 64.5&deg;C &rarr; **48.9&deg;C** (15.6&deg;C drop). `throttled`: `0x80008` &rarr; **`0x80000`** &mdash; bit 3 ("soft temperature limit *currently active*") is now clear, meeting the card's closing criteria. Remaining bit 19 is just the sticky "has occurred since boot" historical flag; it stays set until next reboot regardless of current temp and doesn't indicate ongoing throttling.
- **M8:** unchanged, still healthy (CPU 39.1&deg;C, NVMe 41.9&deg;C, GPU 37.0&deg;C) &mdash; as expected, confirms it was never the concern.

**Still open before closing:** this check was under normal conditions a few hours post-install, not explicitly a sustained-load test as the closing criteria also calls for. Pi's steady 24/7 workload (HA, Node-RED, Mosquitto, log/watchdog server) arguably already constitutes real sustained load rather than a synthetic spike, but worth a check-in after a longer period (a day or more) to confirm bit 3 stays clear rather than closing on a single few-hours-later reading.

Joseph is installing the fan next; re-check `vcgencmd get_throttled` afterward per the closing criteria above.

**Progress (2026-07-12):** Joseph ordered the **AC Infinity MULTIFAN S7** &mdash; dual 120mm (larger than the single-80mm S5 suggested above), UL-certified, marketed for receiver/DVR/console/computer cabinet cooling. Larger fans, more shelf coverage &mdash; a reasonable upgrade over the original suggestion. Not yet installed; verification still pending arrival/install.

**Sustained-load re-check (2026-07-15), checked remotely via Tailscale (Joseph at Xerocraft):** roughly a day after the 2026-07-14 post-install check, under the Pi's normal steady 24/7 workload &mdash; the sustained-load condition the earlier check was missing.

- **Pi:** `throttled=0x80000` &mdash; bit 3 ("soft temperature limit *currently active*") still clear, confirming the 2026-07-14 result wasn't a fluke. Temp **47.2&deg;C**, consistent with the post-install reading (48.9&deg;C), not drifting back up. Bit 19 remains set (sticky "has occurred since boot" flag) &mdash; expected, clears only on next reboot, not a sign of ongoing throttling.
- **M8 (photo-server):** still healthy &mdash; CPU (`k10temp` Tctl) 40.8&deg;C, GPU 36.0&deg;C, NVMe 40.9/31.9&deg;C, 2.5GbE 41.5/37.0&deg;C, WiFi 6E 34.0&deg;C. `lm-sensors` was reinstalled on photo-server for this check (it wasn't present in this session; installed via `apt-get install lm-sensors`, same real `k10temp` source as the 2026-07-14 baseline, not the unreliable `acpitz` dummy).

**Resolution:** fan install (AC Infinity MULTIFAN S7) confirmed effective across two separate checks a day apart &mdash; both under real sustained load, not just a synthetic spike. Soft thermal throttling is no longer active. Closing criteria fully met.

**Closed 2026-07-15 &mdash; Joseph confirmed and directed the close.**

---
