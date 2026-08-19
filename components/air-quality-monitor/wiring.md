# Air Quality Monitor — Breadboard Wiring Reference
**Component:** air-quality-monitor
**Purpose:** Complete wiring reference for the ESP32 breadboard prototype.

---

## Before Wiring

**ESP32 pin label orientation:** ESP32 DevKit pin labels face **down** when the board is inserted in a breadboard — the text is on the underside. Mark key GPIO rows with masking tape labels on the breadboard before wiring to avoid pin confusion (`JCTsh-Build-Standards.md` §2.6).

Rows to label: GPIO18, GPIO19, GPIO21, GPIO22, GPIO23, GPIO27, GPIO32, GPIO34.

GPIO34 note: input-only pin (ADC1) — no pull-up or pull-down; the battery voltage divider provides defined state.
GPIO32 note: configured as INPUT (no pull-up or pull-down) — the dock detect voltage divider provides defined state.

---

## GPIO Assignment Summary

**GPIO18/19/23 all connect to the same single RGB LED module (KY-016)** — its `R`/`G`/`B` pins respectively, not three separate LEDs. See "RGB LED Wiring" below for the full 4-pin mapping.

| GPIO | Function | Component |
|---|---|---|
| GPIO18 | RGB LED module — `R` pin (no external resistor — module has its own, see below) | Field indicator |
| GPIO19 | RGB LED module — `G` pin (same module, no external resistor) | Field indicator |
| GPIO21 | I2C SDA | SEN55 (via Adafruit #5964 adapter) |
| GPIO22 | I2C SCL | SEN55 (via Adafruit #5964 adapter) |
| GPIO23 | RGB LED module — `B` pin (same module, no external resistor) | Field indicator |
| GPIO27 | SEN55 power-gate control (active-high) | BC547B base, via resistor |
| GPIO32 | Dock detect (divider midpoint, INPUT) | TP4056 IN+ → 68kΩ → midpoint → 100kΩ → GND |
| GPIO34 | Battery ADC (input-only) | Voltage divider midpoint |

---

## SEN55 (via Adafruit #5964 Adapter) Wiring

**This sensor connects through two entirely separate interfaces, in series: ESP32 ↔ (bare wires) ↔ Adafruit #5964 adapter ↔ (JST-GH cable) ↔ SEN55.** Don't cross-reference wire colors between the two segments — they're different connection types with nothing in common (see below).

### Segment 1 — ESP32 to adapter (bare wires, you choose the colors)

The adapter has a 4-pin **input** header, labeled directly on the Adafruit board: `VIN`, `GND`, `SCL`, `SDA`. This is a standard 0.1" header — you're making up individual jumper wires yourself here, so the "wire color" is just your own convention, not something to verify against anything.

| Adafruit board pin (labeled on the board) | ESP32 Pin | Notes |
|---|---|---|
| `VIN` | 3.3V (via BC547B gate, see SEN55 Power Gate section — not straight to the 3.3V rail) | Board's own onboard boost converter steps this up to 5V internally, for the SEN55 side only |
| `GND` | GND | |
| `SDA` | GPIO21 | I2C data |
| `SCL` | GPIO22 | I2C clock |

I2C address: 0x69 (fixed — no configurable address pin). No other I2C devices on this bus, no conflicts.

### Segment 2 — adapter to SEN55 (JST-GH cable, colors irrelevant)

**The adapter has a second, completely separate connector for this: a 6-pin JST-GH socket**, distinct from the 4-pin header above. This is what the SEN55 actually plugs into — it carries the boosted 5V, SDA, SCL, and the sensor's `SEL` interface-select line (Adafruit's board ties `SEL` to `GND` internally on this connector; there is no exposed `SEL` pin to wire by hand).

**The SEN55 sensor itself also has its own onboard 6-pin JST-GH socket** (built into the sensor's own PCB, inside its metal case) — this is separate from the Dupont-terminated pigtail cable the sensor was bundled with.

**Connection: plug the Bag 25 JST-GH cable directly between these two sockets** — one end into the Adafruit adapter's JST-GH socket, the other end into the SEN55's own onboard JST-GH socket.

- **Do not use the SEN55's bundled Dupont-terminated cable for this build at all** — set it aside. It's a separate breadboard-prototyping accessory, not part of this design.
- **Do not try to identify or match wire colors on the JST-GH cable.** Both sockets are the same fixed, keyed 6-pin JST-GH standard this sensor family is built around — the connector's physical shape guarantees pin 1 lines up with pin 1 (and so on) on both ends, regardless of what color any individual wire inside the cable happens to be. This was verified at length on 2026-08-19 (see `kanban-board.md` CARD-0012) after a real, confusing false start: the SEN55's bundled Dupont cable and the Bag 25 JST-GH cable use *different, unrelated wire-color conventions* (they're different products from different manufacturers) — comparing their colors against each other looked like a mismatch but was actually a meaningless comparison, since neither cable's colors need to relate to the other's at all.

Enable `scan: true` in the ESPHome `i2c:` block during initial testing to confirm the device is detected:
```
[I][i2c.arduino:069]: Found i2c device at address 0x69  ← SEN55
```

---

## SEN55 Power Gate — BC547B NPN Low-Side Switch (GPIO27)

Duty-cycles the SEN55 (via the adapter) on/off to manage its ~70mA active draw during field-mode logging (~10s active per 2-minute cycle, per the Phase 1 power budget). NPN low-side switch — correct topology since SEN55/the adapter sit on their own 5V-boosted rail, not the ESP32's shared 3.3V logic rail (unlike the unvalidated §2.14 point 8 P-FET pattern, which targets peripherals on that shared rail — not applicable here, see Hardware Context in the instructions doc for the full reasoning).

**BC547B TO-92 lead identification** (flat face toward you, legs down — standard EBC pinout):

| Pin | Position | Signal |
|---|---|---|
| 1 | Left | Emitter |
| 2 | Middle | Base |
| 3 | Right | Collector |

```
Adapter VIN/SEN55 supply ──────────────────────────┐
                                                     │ (adapter GND return, not the supply itself —
                                                     │  see note below)
Adapter GND ──────────────────────────────────────► Collector
                                                     │
                                              Emitter ── GND (common)
                                                     │
GPIO27 ──── R (1kΩ) ──── Base
                            │
                        R_pd (10kΩ) ──── GND (base pull-down)
```

- **Low-side switch: the transistor sits between the adapter's GND return and common GND**, not between the 3.3V supply and the adapter's VIN. The adapter's VIN stays tied directly to 3.3V; switching the GND return is what actually de-energizes it.
- **Base resistor: 1kΩ** (Bag on hand, `jctsh-parts-inventory.md`) — targets several mA of base current at 3.3V GPIO drive, comfortably into saturation for BC547B's typical hFE at the ~70mA collector current this needs to switch.
- **Base pull-down: 10kΩ**, base to GND. Not in the original hiking-monitor gate pattern, but added here as a direct lesson from CARD-0070's BS250 floating-gate finding on the LDO/gate rig (a floating gate can leave a switch in an unintended state before firmware configures the GPIO, e.g. during the ESP32's reset/boot window). This is the NPN/active-high equivalent precaution — pull-down ensures the gate defaults to SEN55-off whenever GPIO27 isn't actively driven HIGH, not just after firmware takes over.
- **Active-high:** GPIO27 HIGH → transistor ON → SEN55 GND return connected → powered. GPIO27 LOW (or floating, thanks to the pull-down) → transistor OFF → SEN55 unpowered.
- Firmware: drive GPIO27 HIGH before an I2C read, allow the SEN55's own settle/warm-up time (see `air-quality-monitor-claude-code-instructions.md` Step 8 for the exact duty-cycle timing), then read; drive LOW again before the next sleep/idle period.

---

## Inline Power Switch — True Transport/Storage Off

**Decided 2026-08-19, directly from CARD-0181's hiking-monitor finding** — a switch tapped off a GPIO only sets a mode flag, it does not cut power. This switch is wired **directly into the battery+ path**, ahead of both the TP4056 and the LDO tap point, so switching it off isolates the entire board from the battery with zero current draw. It is not connected to any GPIO and does not appear in the GPIO table above.

**Part:** Gebildet SS12D10 slide switch (SPDT, Bag 23, on hand) — used as SPST: battery+ wire to the common (COM) terminal, one throw terminal to the downstream node (TP4056 `BAT+` / LDO `VIN` junction, see Power section below), the other throw terminal left unconnected.

```
LiPo BAT+ ──── SW (COM) ── SW (throw 1) ────┬──── TP4056 BAT+
                                              └──── MCP1700 VIN
                            SW (throw 2) ── (not connected)
```

**Verification (Step 7):** with the switch off, confirm zero voltage/current downstream at both the TP4056 `BAT+` pad and the LDO `VIN` pin — not just "the board is unresponsive," which could also be explained by a firmware hang. Measure directly.

---

## Power — MCP1700 LDO (Direct LiPo-to-3.3V)

**Decided 2026-08-19** per `JCTsh-Build-Standards.md` §2.14 point 7 — replaces the originally-planned TP4056+boost combined-module path for the ESP32's own supply. TP4056's charging half is unchanged and still used; only its boost stage is bypassed. Same LDO part and wiring pattern already validated on the CARD-0026/CARD-0070 rig.

**MCP1700 TO-92 lead identification** (flat face toward you, legs down — confirmed against Microchip datasheet DS20001826F on the CARD-0070 rig; reordered from the common 78xx VIN-GND-VOUT convention, a known gotcha for this part):

| Pin | Position | Signal |
|---|---|---|
| 1 | Left | GND |
| 2 | Middle | VIN |
| 3 | Right | VOUT |

```
LiPo BAT+ (via inline switch) ──┬──── TP4056 BAT+ (charging only — TP4056's boost pads unused)
                                 │
                                 └──── MCP1700 VIN
                                       MCP1700 GND ──── common GND
                                       MCP1700 VOUT ──── ESP32 3V3 pin directly
```

- **LDO `VIN` taps the battery+ node in parallel with TP4056's `BAT+` input** — a parallel connection straight off the raw battery (through the inline switch), not fed from TP4056's boost/`OUT+` output.
- **LDO `VOUT` → ESP32 dev board's `3V3` pin directly** (not `VIN`) — `VIN` expects ~5V and routes through the board's own onboard regulator; feeding `3V3` bypasses that second regulation stage, which is the entire point of this change.
- **Caution: never power the board from USB and the LDO at the same time** — both would drive the `3V3` rail from separate unisolated sources, risking backfeeding either regulator. Disconnect the LDO before flashing over USB, and vice versa. (Breadboard Steps 4-6 below power via USB only — do not connect the LiPo/LDO until Step 7.)
- The Adafruit #5964 adapter's own onboard 5V boost for the SEN55 is fed from this same `3V3` rail (via the BC547B gate above) — it never depended on TP4056's boost output, so this change doesn't affect it.

---

## Dock Detect Wiring (GPIO32)

Same divider values and pin as hiking-monitor's `IN+` divider — TP4056 IN+ (USB VBUS) divided down to a safe GPIO level.

```
TP4056 IN+ ──── R3 (68kΩ) ──┬──── R4 (100kΩ) ──── GND
                             │
                      GPIO32 (INPUT, no pull)
```

- USB absent: LOW → field mode
- USB present: HIGH → docked/charging (home mode)

Matches hiking-monitor's measured behavior (0.47V/5.1V raw → ~0.28V/~3.04V after the divider) — same TP4056 module, same divider values, expect the same result. Confirm with a multimeter during Step 3/4 rather than assuming.

---

## Battery Voltage Divider Wiring (GPIO34)

**Corrected 2026-08-19** — the instructions doc's Hardware Context table originally said 68kΩ/68kΩ; hiking-monitor's actual `wiring.md` uses **100kΩ/100kΩ**. Matching the real value here, per Step 0's "match hiking-monitor's pattern, don't re-derive it" instruction. (68kΩ/100kΩ is the *dock-detect* divider above, a different one — not to be confused.)

Divides LiPo voltage (3.5-4.2V) to fit ESP32 ADC range. Two equal 100kΩ resistors → 2:1 divider. Midpoint voltage = Vbatt / 2. ESPHome `filters: - multiply: 2.0` restores actual voltage.

```
LiPo BAT+ (post-switch) ──── R1 (100kΩ) ──┬── R2 (100kΩ) ──── GND
                                            │
                                     GPIO34 (ADC input)
```

**Notes:**
- During breadboard testing without LiPo connected: wire the divider from the 3.3V rail instead as a placeholder, same as hiking-monitor's own bench-test approach. Replace with actual battery+ (post-switch) when the power system is integrated in Step 7.
- GPIO34 is an input-only pin — do not drive it as output. ADC use only.
- High-value resistors (100kΩ) minimize current draw from the divider itself — negligible against the LDO's own budget.

---

## RGB LED Wiring (GPIO18/19/23)

**Confirmed 2026-08-19 against the actual physical module** (Greekcreit/Geekcreit 37-module kit, Plastic Box) — a KY-016: common-cathode, clear 5mm LED, 4-pin header silkscreened `- R G B` in that order, **with three current-limiting resistors already built onto the module's own small PCB.**

| Module Pin | ESP32 Pin | External resistor? |
|---|---|---|
| `-` (common cathode) | GND | — |
| `R` | GPIO18 | **None** — module has its own onboard resistor per channel; do not add an external one in series, it would only dim the LED further |
| `G` | GPIO19 | None (see above) |
| `B` | GPIO23 | None (see above) |

This deviates from `JCTsh-Build-Standards.md` §8's default (330Ω external, for a bare LED with no onboard resistor) — that default assumes a bare LED, not a pre-resistored module like this one. Wire the module's 4 pins straight to GND/GPIO18/GPIO19/GPIO23, no discrete resistors in the RGB LED's signal path.

---

## Power (Breadboard Phase — Steps 4-6)

Power ESP32 via USB-C cable from PC during breadboard Steps 4-6. Do NOT connect the LiPo/LDO until Step 7 (power system integration with polarity verification) — see the LDO caution above about not powering from USB and the LDO simultaneously.

Power wiring for Steps 4-6:
- USB-C → ESP32 USB-C port (powers ESP32 from PC)
- Breadboard power rails: 3.3V from ESP32 3.3V pin → red rail; GND from ESP32 GND → blue rail

---

## Schematic Overview

```
┌────────────────────┐                    ┌──────────────────────────────────┐
│  LiPo (via switch)  │                    │    ESP32 DevKitC-32 (38-pin)     │
└──────────┬──────────┘                    │                                  │
           │                               │                                  │
     ┌─────┴─────┐                         │                                  │
     │           │                         │                                  │
┌────▼────┐  ┌───▼────┐                    │                                  │
│ TP4056  │  │ MCP1700│──VOUT──────────────►│ 3V3 (pin 1)                      │
│(chg only)│  │  LDO   │                    │       │                          │
└────┬────┘  └────────┘                    │       └──► adapter VIN (via BC547B gate)
     │ IN+ (green)                          │                                  │
     ├──R3(68kΩ)──┬──R4(100kΩ)──GND         │                                  │
     │            └──────────────► GPIO32   │                                  │
     │ BAT+ (post-switch, white)             │                                  │
     ├──R1(100kΩ)──┬──R2(100kΩ)──GND        │                                  │
     │             └──────────────► GPIO34  │                                  │
     └──────────────────────────────────────┤ GND                              │
                                             │                                  │
                                             │ GPIO27 ──R(1k)── Base(BC547B)    │
                                             │           │      Collector◄─adapter GND
                                             │        R_pd(10k)  Emitter──GND   │
                                             │           │                      │
                                             │          GND                     │
                                             │                                  │
                                             │ GPIO21 (SDA) ◄─ SEN55 adapter    │
                                             │ GPIO22 (SCL) ◄─ SEN55 adapter    │
                                             │ GPIO18/19/23 ──► RGB LED         │
                                             └──────────────────────────────────┘
```

---

## Perfboard Footprint Measurement Procedure

Determines the minimum perfboard size before Step 9 (perfboard transfer). SEN55 + adapter is the dominant constraint (SEN55 itself is ~59mm × 37mm × 23mm per Phase 1's spec-sheet figures — measure the real unit, don't just trust the spec).

1. **Lay out the full component set** on a flat surface in their approximate final relative positions: ESP32 DevKitC-32 (with its two 19-pin female header strips, per `JCTsh-Build-Standards.md` §1.2), the SEN55 module + Adafruit #5964 adapter (as one unit, connected via their JST GH cable — note they don't have to be directly adjacent, the cable gives some placement flexibility, but lay them at a realistic minimum separation), the BC547B + its two resistors, the two voltage dividers (4 resistors total), the RGB LED module, the MCP1700 LDO, and the inline power switch.
2. **Measure the SEN55 module itself directly** (calipers if available) — confirm or correct the ~59mm × 37mm × 23mm spec-sheet figure against the real unit in hand.
3. **Measure the Adafruit #5964 adapter board** separately — its footprint plus mounting clearance around the JST GH connector.
4. **Determine overall bounding footprint** needed for ESP32 + adapter + discrete components with reasonable trace/solder-pad spacing (don't pack components edge-to-edge — leave room for hand-soldered traces).
5. **Compare against the standard 5×7cm Chanzon FR4 board** (`JCTsh-Build-Standards.md` §1.2 default) — report whether that standard size fits, or whether a larger board is needed given SEN55's footprint.

**Report back:** SEN55's actual measured dimensions, the adapter's footprint, and whether the standard 5×7cm board is sufficient or a larger size is needed.
