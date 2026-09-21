# Back Patio Temp Sensor — Parts List

Consolidated bill of materials for this build. Front-porch-temp-sensor's own BOM lived
in its Phase 4 instructions file (`front-porch-temp-sensor-claude-code-instructions.md`'s
Hardware Context table) — that file was deliberately skipped for this build (straight to
Build, per CARD-0219), so this file exists to hold the same consolidated view instead of
leaving it split with no single reference point. Per-step Materials sub-tables still exist
in `perfboard-layout.md` and `mounting.md` for at-a-glance use during those specific steps.

---

## Electronics

| Item | Detail | Source / inventory location |
|---|---|---|
| Microcontroller | ESP32 DevKitC-32, 38-pin, CP2102, USB-C — same board batch as `air-quality-monitor`'s (see `ESP32-project-pins.md`'s pin 18 GND-anomaly note) | `JCTsh-Parts-Inventory.md`, Bag 1 — allocated to this build (CARD-0219) |
| Temp/humidity/pressure sensor | BME280 breakout, genuine GY-BME280, I2C | `JCTsh-Parts-Inventory.md`, Bag 3 — allocated to this build. **Verify chip ID at flash regardless** — front-porch's original batch (different listing) turned out counterfeit BMP280. |
| Light sensor | BH1750 breakout (GY-302), I2C | `JCTsh-Parts-Inventory.md`, Bin C3 — allocated to this build |

## Build Hardware

| Item | Detail | Source |
|---|---|---|
| Perfboard | FR4 double-sided, 5×7cm | Confirmed on hand (Joseph, 2026-09-21) — not itemized in `JCTsh-Parts-Inventory.md` |
| Female pin headers | 2.54mm single-row — two 19-pin (ESP32), one 4-pin (BME280), one 3-pin (BH1750) | Confirmed on hand |
| Standoffs | M3 brass male-female, 10mm ×4 | Confirmed on hand |
| Screws | M3 ×4 (wall mount) | Confirmed on hand |
| Nuts | M3 ×4 (secures board to standoffs) | Confirmed on hand |
| Wire | Solid-core, for back-of-board bridges | Confirmed on hand |

## Mounting / Power

| Item | Detail | Source |
|---|---|---|
| USB-C cable | Length sufficient to reach the outlet from the mount point (P2) | Confirmed on hand |
| USB power adapter | 5V, ≥500mA | Confirmed on hand |

## Deliberately Not Used

| Item | Why not |
|---|---|
| Breadboard + prototyping jumper wires | Skipped (Joseph, 2026-09-21) — going straight to perfboard since this is a proven, already-built design, not a new prototype |

---

**Related:** `JCTsh-Parts-Inventory.md` (v2.32, allocation entries), `perfboard-layout.md` and `mounting.md` (per-step Materials sub-tables), `tos/kanban-board.md` CARD-0219 (Planning history).
