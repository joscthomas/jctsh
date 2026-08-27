# Air Quality Monitor — Power System Redesign
**Component:** air-quality-monitor
**Purpose:** Applies `JCTsh-Build-Standards.md` §2.14 points 9-10 (added 2026-08-25, CARD-0213) to this device's actual power path — replaces the original MCP1700 LDO, which CARD-0198's investigation found marginal against the real coincident peak load.
**Status:** Design only — not yet built or ordered. Parent thread: CARD-0198.

---

## 1. Coincident Peak Load

Per §2.14 point 9: size the regulator for everything that can plausibly draw current at the same moment, not the average.

| Source | Current | Basis |
|---|---|---|
| WiFi TX/association burst | ~250-300mA (design figure) | This project's own real measurement (CARD-0026, hiking-monitor rig) showed 109-154mA *whole-device* current during active boot/WiFi, never settling — that figure already includes MCU baseline, so the TX-burst component alone is plausibly higher. A basic ammeter also can't fully resolve true microsecond-scale peaks. Using a conservative 250-300mA design figure for the TX burst itself, not the lower whole-device average, given how repeatedly marginal the original 250mA-rated LDO proved in practice. |
| SEN55 active Measurement mode | ~63mA | Documented in `air-quality-monitor.yaml`'s own comments; boot-time sequencing keeps this idle during WiFi connect, but steady-state operation (SEN55 polling every 10s while periodic MQTT publishes happen) does not guarantee the two never overlap after boot. |
| ESP32 baseline (I2C, RGB LED, MCU logic) | ~80mA | Consistent with the low end of hiking-monitor's own 109-154mA whole-device reading when WiFi TX isn't actively spiking. |
| **Design peak (sum)** | **~450mA** | |

**Regulator target, per §2.14 point 9's 2-3x rule: ≥900mA-1.35A.** Rounding to a clean, comfortably-available rating: **≥1A.**

## 2. Regulator Selection — deliberate deviation from a pure LDO, explained

**Chosen: Pololu D24V10F3 — 3.3V, 1A Step-Down (buck/switching) Regulator**, small breakout board with 0.1" pin headers (hand-solder/breadboard friendly, same practical constraint that shaped every other part choice in this project).

**Why a switching buck regulator instead of another linear LDO, given §2.14 point 7's stated LDO preference:** point 7's guidance is specifically about avoiding a **boost-then-buck double conversion** (stepping the battery voltage *up* to 5V then back *down* to 3.3V, as hiking-monitor's TP4056+boost module does) — not about avoiding a **direct buck** from raw battery voltage straight to 3.3V, which is still a single conversion stage. A linear LDO's only response to a current spike beyond its rating is to run out of headroom and let the output sag; a good small buck regulator (the Pololu D24V-series is specifically well-regarded in the hobbyist/robotics community for exactly this kind of transient load) handles a spike far more gracefully and reaches 1A in a small, cheap, still hand-solderable package — a comparable low-quiescent LDO at this current rating either doesn't exist in an easy through-hole/breakout form, or needs a much larger package to dissipate the heat at that current. Quiescent current is higher than the MCP1700's ~1.6µA (Pololu's own datasheet lists roughly 180µA no-load) — a real, accepted tradeoff, and a minor one next to the actual problem this redesign solves.

**Pinout (Pololu D24V10F3 breakout, silkscreen-labeled):**

| Pin | Signal |
|---|---|
| VIN | Battery+ (post-switch), same node as the old MCP1700 VIN tap |
| GND | Common ground |
| VOUT | Regulated 3.3V out |

**Minimum input voltage — checked against Pololu's own spec page, 2026-08-27, not assumed.** Being a pure buck (step-down-only) topology, this regulator cannot manufacture voltage from nothing — if VIN drops below VOUT, it can't boost to compensate; it just runs out of duty-cycle headroom and the output sags along with the input. Pololu's own documented input range is **3.4V-36V**, with the explicit caveat that "the effective lower limit of VIN is VOUT plus the regulator's dropout voltage" and that dropout *increases* under load — meaning the practical floor under a real current spike (the WiFi-burst scenario this whole redesign exists for) is plausibly higher than the bare 3.4V figure.

**Real tension with §2.14 point 2's existing low-battery cutoff, flagged here rather than assumed fine:** point 2's firmware cutoff threshold (3.4V) was chosen generically — margin above the LiPo cell's own PCM trip point and boost-converter end-of-charge instability — not chosen with this specific regulator's own spec in mind. Since the D24V10F3's documented minimum input is *also* 3.4V, the firmware cutoff and the regulator's own failure floor now sit right on top of each other rather than the cutoff having real margin above it, especially once dropout-under-load is accounted for. **Needs resolving before this is considered done**, either by real bench measurement (does the output actually hold 3.3V clean at 3.4V VIN under a real WiFi-burst load, or has it already started sagging by then?) or by raising this device's own low-battery cutoff threshold above the generic 3.4V standard to give real margin against this specific regulator's dropout behavior. Added to Open Items below.

## 3. Bulk Capacitance at the Point of Load

Per §2.14 point 9: real capacitance, placed as close to the ESP32's own 3V3/GND pins as physically possible — a complement to the regulator's headroom, not a substitute for it (this project's own 2026-08-24 testing found a bulk cap alone did not reliably fix an undersized regulator).

- **470µF electrolytic** — from the 28-value 0.1µF-4700µF assortment kit already in inventory (`jctsh-parts-inventory.md`, Plastic Box). Any of the 10V+ rated values in that kit is fine for a 3.3V rail.
- **4.7µF ceramic** — small, fast-responding, catches the sub-millisecond edge of a transient the electrolytic's own ESR can't fully absorb. Not currently in inventory — add to the parts list before build.

Placement: both capacitors in parallel, directly across the ESP32's 3V3 pin and an adjacent GND pin — not just "somewhere on the rail."

## 4. Battery — unchanged, already adequate

The existing EEMB 1100mAh PCM-protected LiPo (§2.14 point 1 compliant) is not the bottleneck here — a healthy single-cell LiPo of this size comfortably supports continuous discharge well above the ~450mA design peak. Tonight's earlier battery-connector fault (CARD-0198) was a real, separate issue (an intermittent internal short at the JST connector, already fixed by swapping to a spare cell) — not evidence the battery itself needs to be upsized.

## 5. Wiring Diagram

```
LiPo BAT+ (via inline switch) ──┬──── TP4056 BAT+ (charging only — unchanged)
                                 │
                                 ├──── Pololu D24V10F3 VIN
                                 │     D24V10F3 GND ──── common GND
                                 │     D24V10F3 VOUT ──┬── 470µF electrolytic ──┐
                                 │                      ├── 4.7µF ceramic ──────┤
                                 │                      │         (both to GND) │
                                 │                      └─────────────────────────► ESP32 3V3 pin directly
                                 │
                                 └──── Battery Voltage Divider — R1 (100kΩ) top leg
                                       (unchanged — same node as before, see
                                       Battery Voltage Divider Wiring in wiring.md)

Everything downstream of the ESP32's 3V3 pin is UNCHANGED from the current
design: SEN55/Adafruit adapter (VIN direct off 3V3, no gate), RGB LED module,
dock-detect divider (taps TP4056 IN+, independent of this regulator entirely),
debug UART (UART2/GPIO17, independent of the power path).
```

**What's changing vs. the current build:** only the regulator itself (MCP1700 → Pololu D24V10F3) and the addition of the ceramic capacitor alongside the existing electrolytic. The inline switch, TP4056 charging path, both voltage dividers, SEN55, RGB LED, and debug UART wiring are all unaffected — this is a point-load swap, not a full rewire.

## 6. Firmware companions — not part of this wiring change, tracked separately

Per §2.14 points 2 and 10, already partially in place or tracked elsewhere:
- **Boot-time sequencing** (SEN55 held in Idle until `mqtt_client.is_connected()`, bounded to 30s) — already implemented (CARD-0198), keep as-is.
- **Low-battery cutoff extended to WiFi-burst operations** — air-quality-monitor's Step 8 duty-cycle firmware (field/home mode, the analogous piece to hiking-monitor's replay burst) isn't built yet at all. When it is, it needs the same gate CARD-0212 is adding to hiking-monitor: don't attempt a WiFi-heavy burst below the safe voltage threshold.

## 7. Open items before ordering/building

- ~~Confirm the Pololu D24V10F3 (or equivalent ≥1A buck breakout) is genuinely in stock/orderable — not yet purchased.~~ **Received 2026-08-27** — ×2, ordered direct from Pololu, `jctsh-parts-inventory.md` Bag 38.
- ~~Add a 4.7µF ceramic capacitor to the parts list — not currently in inventory.~~ **Received 2026-08-27** — BOJACK 10-value assortment kit (includes 4.7µF), `jctsh-parts-inventory.md` Bag 39.
- **New, 2026-08-27:** resolve the low-battery-cutoff-vs-regulator-dropout overlap flagged in §2 above — either bench-confirm the output actually holds clean 3.3V at 3.4V VIN under a real WiFi-burst load, or raise this device's own low-battery cutoff threshold above the generic §2.14 point 2 value (3.4V) to give real margin against this regulator's own documented dropout floor.
- This design has not been bench-tested. Build and verify per the same reliability bar used throughout CARD-0198 (multiple consecutive clean battery power cycles with SEN55 connected, not just one success) before considering this closed.
