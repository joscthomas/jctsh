# Air Quality Monitor — Breadboard Wiring Reference
**Component:** air-quality-monitor
**Purpose:** Complete wiring reference for the ESP32 breadboard prototype.

---

## Before Wiring

**ESP32 pin label orientation:** ESP32 DevKit pin labels face **down** when the board is inserted in a breadboard — the text is on the underside. Mark key GPIO rows with masking tape labels on the breadboard before wiring to avoid pin confusion (`JCTsh-Build-Standards.md` §2.6).

Rows to label: GPIO18 (pin 30), GPIO19 (pin 31), GPIO21 (pin 33), GPIO22 (pin 36), GPIO23 (pin 37), GPIO27 (pin 11), GPIO32 (pin 7), GPIO34 (pin 5).

GPIO34 (pin 5) note: input-only pin (ADC1) — no pull-up or pull-down; the battery voltage divider provides defined state.
GPIO32 (pin 7) note: configured as INPUT (no pull-up or pull-down) — the dock detect voltage divider provides defined state.

---

## GPIO Assignment Summary

**GPIO18 (pin 30)/GPIO19 (pin 31)/GPIO23 (pin 37) all connect to the same single RGB LED module (KY-016)** — its `R`/`G`/`B` pins respectively, not three separate LEDs. See "RGB LED Wiring" below for the full 4-pin mapping.

Physical pin numbers below are from `ESP32-project-pins.md` — verify against the actual board's silkscreen before soldering or probing, per that file's own caveat.

| GPIO | Board Pin # | Function | Component |
|---|---|---|---|
| GPIO18 | 30 | RGB LED module — `R` pin (no external resistor — module has its own, see below) | Field indicator |
| GPIO19 | 31 | RGB LED module — `G` pin (same module, no external resistor) | Field indicator |
| GPIO21 | 33 | I2C SDA — blue | SEN55 (via Adafruit #5964 adapter) |
| GPIO22 | 36 | I2C SCL — yellow | SEN55 (via Adafruit #5964 adapter) |
| GPIO23 | 37 | RGB LED module — `B` pin (same module, no external resistor) | Field indicator |
| GPIO27 | 11 | SEN55 power-gate control (active-high) | BC547B transistor base, via resistor |
| GPIO32 | 7 | Dock detect (divider midpoint, INPUT) | TP4056 IN+ → 68kΩ → midpoint → 100kΩ → GND |
| GPIO34 | 5 | Battery ADC (input-only) | Voltage divider midpoint |

---

## SEN55 (via Adafruit #5964 Adapter) Wiring

**This sensor connects through two entirely separate interfaces, in series: ESP32 ↔ (bare wires) ↔ Adafruit #5964 adapter ↔ (JST-GH cable) ↔ SEN55.** Don't cross-reference wire colors between the two segments — they're different connection types with nothing in common (see below).

### Segment 1 — ESP32 to adapter (bare wires, STEMMA QT color convention)

The adapter has a 4-pin **input** header, labeled directly on the Adafruit board: `VIN`, `GND`, `SCL`, `SDA`. This is a standard 0.1" header — you're making up individual jumper wires yourself here. Use the Adafruit STEMMA QT / SparkFun Qwiic color convention (black = GND, red = power, blue = SDA, yellow = SCL) rather than an arbitrary choice, matching `ESP32-project-pins.md`.

| Adafruit board pin (labeled on the board) | ESP32 Pin | Board Pin # | Wire Color | Notes |
|---|---|---|---|---|
| `VIN` | 3.3V (direct — the BC547B transistor switches the adapter's GND return instead, see SEN55 Power Gate section below) | 1 | red | Board's own onboard boost converter steps this up to 5V internally, for the SEN55 side only |
| `GND` | GND | 38 / 32 / 18 / 14 (any GND pin) | black | |
| `SDA` | GPIO21 | 33 | blue | I2C data |
| `SCL` | GPIO22 | 36 | yellow | I2C clock |

I2C address: 0x69 (fixed — no configurable address pin). No other I2C devices on this bus, no conflicts.

### Segment 2 — adapter to SEN55 (JST-GH cable, colors irrelevant)

**The adapter has a second, completely separate connector for this: a 6-pin JST-GH socket**, distinct from the 4-pin header above. This is what the SEN55 actually plugs into — it carries the boosted 5V, SDA, SCL, and the sensor's `SEL` interface-select line (Adafruit's board ties `SEL` to `GND` internally on this connector; there is no exposed `SEL` pin to wire by hand).

**The SEN55 sensor itself also has its own onboard 6-pin JST-GH socket** (built into the sensor's own PCB, inside its metal case) — this is separate from the Dupont-terminated pigtail cable the sensor was bundled with.

**Connection: plug the Bag 25 JST-GH cable directly between these two sockets** — one end into the Adafruit adapter's JST-GH socket, the other end into the SEN55's own onboard JST-GH socket.

**This cable is what makes the SEN55 external-mount decision (2026-08-20) work** — the SEN55 module itself lives outside the enclosure, 3M-taped to its smooth exterior surface, while the adapter stays inside with the rest of the perfboard. This 100mm cable is the only connection between them, routed through a small pass-through hole in the enclosure wall. See the Phase 1 doc's Carry and Enclosure section and the Perfboard Footprint Measurement Procedure below.

- **Do not use the SEN55's bundled Dupont-terminated cable for this build at all** — set it aside. It's a separate breadboard-prototyping accessory, not part of this design.
- **Do not try to identify or match wire colors on the JST-GH cable.** Both sockets are the same fixed, keyed 6-pin JST-GH standard this sensor family is built around — the connector's physical shape guarantees pin 1 lines up with pin 1 (and so on) on both ends, regardless of what color any individual wire inside the cable happens to be. This was verified at length on 2026-08-19 (see `kanban-board.md` CARD-0012) after a real, confusing false start: the SEN55's bundled Dupont cable and the Bag 25 JST-GH cable use *different, unrelated wire-color conventions* (they're different products from different manufacturers) — comparing their colors against each other looked like a mismatch but was actually a meaningless comparison, since neither cable's colors need to relate to the other's at all.

Enable `scan: true` in the ESPHome `i2c:` block during initial testing to confirm the device is detected:
```
[I][i2c.arduino:069]: Found i2c device at address 0x69  ← SEN55
```

---

## SEN55 Power Gate — BC547B NPN Transistor Low-Side Switch (GPIO27, pin 11)

Duty-cycles the SEN55 (via the adapter) on/off to manage its ~70mA active draw during field-mode logging (~10s active per 2-minute cycle, per the Phase 1 power budget). NPN low-side switch — correct topology since SEN55/the adapter sit on their own 5V-boosted rail, not the ESP32's shared 3.3V logic rail (unlike the unvalidated §2.14 point 8 P-FET pattern, which targets peripherals on that shared rail — not applicable here, see Hardware Context in the instructions doc for the full reasoning).

**BC547B transistor TO-92 lead identification** (flat face toward you, legs down — standard EBC pinout):

| Pin | Position | Signal |
|---|---|---|
| 1 | Left | Emitter |
| 2 | Middle | Base |
| 3 | Right | Collector |

```
Adapter GND return ─────────────────────────► Collector
                                                   │
                                            Emitter ── GND (common)
                                                   │
GPIO27 (pin 11) ──── R (1kΩ) ──── Base
                            │
                        R_pd (10kΩ) ──── GND (base pull-down)
```

- **Low-side switch: the transistor sits between the adapter's GND return and common GND**, not between the 3.3V supply and the adapter's VIN. The adapter's VIN stays tied directly to 3.3V; switching the GND return is what actually de-energizes it.
- **Base resistor: 1kΩ** (Bag on hand, `jctsh-parts-inventory.md`) — targets several mA of base current at 3.3V GPIO drive, comfortably into saturation for the BC547B transistor's typical hFE at the ~70mA collector current this needs to switch.
- **Base pull-down: 10kΩ**, base to GND. Not in the original hiking-monitor gate pattern, but added here as a direct lesson from CARD-0070's BS250 floating-gate finding on the LDO/gate rig (a floating gate can leave a switch in an unintended state before firmware configures the GPIO, e.g. during the ESP32's reset/boot window). This is the NPN/active-high equivalent precaution — pull-down ensures the gate defaults to SEN55-off whenever GPIO27 (pin 11) isn't actively driven HIGH, not just after firmware takes over.
- **Active-high:** GPIO27 (pin 11) HIGH → transistor ON → SEN55 GND return connected → powered. GPIO27 (pin 11) LOW (or floating, thanks to the pull-down) → transistor OFF → SEN55 unpowered.
- Firmware: drive GPIO27 (pin 11) HIGH before an I2C read, allow the SEN55's own settle/warm-up time (see `air-quality-monitor-claude-code-instructions.md` Step 8 for the exact duty-cycle timing), then read; drive LOW again before the next sleep/idle period.

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

**Operating rule: switch ON for all device operation** — breadboard bench work after Step 7, field mode, home mode (docked and charging via TP4056), everything. **Switch OFF only for storage/transport**, with one narrow exception: briefly OFF while flashing over the ESP32's own USB-C port (see the LDO caution below) — switch back ON immediately after. Switching off for TP4056 charging is *not* this exception and should not be done — the switch sits ahead of TP4056's `BAT+` too, so turning it off disconnects the battery from the charger and charging simply stops.

---

## TP4056 Module Wiring

Same physical TP4056+boost combined module as hiking-monitor (Bag 8) — see `components/hiking-monitor/wiring.md`'s "TP4056 Perfboard Connector" section for the reference module pinout (pins named `IN+`, `BAT+`, `VOUT−`, `VOUT+` there). On this design, **only the charging half of the module is used** — the boost stage (`VOUT+`) is bypassed in favor of the MCP1700 LDO (see Power — MCP1700 LDO below), so only three of the module's four pads are wired.

| Module Pin | Wire Color | Connects To |
|---|---|---|
| `IN+` | green | Dock Detect divider — R3 (68kΩ) top leg, → GPIO32 (pin 7). See Dock Detect Wiring below. **Shared input** — also where the SUNYIMA solar panel's positive lead connects (see Solar Input below); USB and solar are electrically parallel sources into this same node, not separate inputs. |
| `IN−` | — | Solar panel's negative lead connects here (see Solar Input below) — the module's only exposed ground pad for the solar/USB charge-input side. Not separately wired to anything else; USB-side ground is internal to the module's own micro-USB connector. |
| `BAT+` | white | Inline power switch throw 1 — same node as `MCP1700 VIN` (pin 2) and the Battery Voltage Divider's top leg. See Inline Power Switch above and Battery Voltage Divider Wiring below. |
| `VOUT−` (GND) | black | Common GND — ties the module's ground return into the shared ground with the ESP32, LDO, and both dividers. |
| `VOUT+` | — | **Unused, leave unconnected** — boost stage bypassed on this design. Do not wire to anything (unlike hiking-monitor, which uses this pin as its 5.7V boosted supply). |

**Inferred, not separately confirmed:** hiking-monitor's own reference connector exposes only `IN+`, `BAT+`, `VOUT−`, `VOUT+` (4 signals) for the identical physical module — implying the module's own `BAT−` pad is tied internally to `VOUT−`, with no separate pad broken out for it. `IN−` itself **is** exposed and wired here (unlike on hiking-monitor's connector, which doesn't route it out) specifically because the solar panel's negative lead needs it — hiking-monitor's own solar wiring (`power-system.md`) confirms `IN−` is a real, usable pad on this module, just not one hiking-monitor's 4-pin perfboard harness happened to break out. Confirm both `IN−` and the `BAT−`/`VOUT−` tie internally with a continuity check against the physical module before relying on this at Step 3/7, same as other unverified physical claims in this doc.

### Solar Input (Backpacking Only)

Per the Phase 1 doc's Resolved Decisions (Power), the TP4056+boost module supports solar input natively — no separate charge controller needed. **This connects to the same `IN+`/`IN−` pads as the micro-USB charging input above**, not a distinct input on the module — solar and USB are electrically parallel sources into the same charge-input node. Consequence: since `IN+` is also the Dock Detect tap (GPIO32), connecting the solar panel — or charging via USB in the field, e.g. from a power bank while backpacking — raises `IN+` exactly like docking at home does, and the device reads as docked (GPIO32 HIGH) even out on trail. Same underlying wiring as hiking-monitor, matching its `perfboard-layout.md` note ("IN+ / IN− — solar/USB charging input; IN+ also tapped for dock detect").

**This is now a designed-for path, not just an accepted quirk (2026-08-20 Timeout policy revision, `JCTsh-air-quality-monitor-phase1.md`)** — field-mode duty-cycle logging runs unconditionally regardless of dock-detect state, and dock-detect HIGH only triggers a bounded-window background WiFi attempt against both `JCTnet1` and the Pixel hotspot (added to `secrets.yaml` specifically for this). If neither is reachable, the attempt backs off and retries periodically without ever interrupting logging. See `air-quality-monitor-claude-code-instructions.md` Step 8 for the firmware behavior.

**Part:** SUNYIMA solar panel, 5.5V/80mA (Bag 6) — bare-lead panel, no connector attached. Per hiking-monitor's `power-system.md`, solder a JST male plug to the panel's leads and a JST female receptacle wired to the module's `IN+`/`IN−` pads, verifying polarity with a multimeter before connecting (same procedure as LiPo polarity check). **Connector source not yet itemized in this project's own BOM** — the Phase 1 doc's Resolved Decisions row lists the JST solar port without a bag number. The general-purpose JST SM 2-Pin Connectors assortment (Bag 14, `jctsh-parts-inventory.md`) is the likely candidate, matching hiking-monitor's approach, but confirm before use rather than assuming.

Deferred per Phase 1's "Deferred Features" table: solar panel mount/clip design. Only relevant for multi-day backpacking — the 1100mAh LiPo covers day hikes without it.

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

- **LDO `VIN` taps the battery+ node in parallel with TP4056's `BAT+` input** — a parallel connection straight off the raw battery (through the inline switch), not fed from TP4056's boost/`VOUT+` output.
- **LDO `VOUT` → ESP32 dev board's `3V3` pin directly** (not `VIN`) — `VIN` expects ~5V and routes through the board's own onboard regulator; feeding `3V3` bypasses that second regulation stage, which is the entire point of this change.
- **Caution: never power the board from USB and the LDO at the same time** — both would drive the `3V3` rail from separate unisolated sources, risking backfeeding either regulator. Disconnect the LDO before flashing over USB, and vice versa. (Breadboard Steps 4-6 below power via USB only — do not connect the LiPo/LDO until Step 7.) **This is scoped specifically to the ESP32's own USB-C port** (the one used for flashing/serial) — the TP4056's separate micro-USB charging port never touches `3V3` at all, it only feeds the LiPo's `BAT+`/`BAT-` via the charge circuit (see Dock Detect Wiring below). Charging via TP4056 while the LDO powers the ESP32 off the battery is normal, expected home-mode operation, not a conflict — no need to switch off for that. **The inline power switch satisfies the ESP32-USB-C case** — switching it off removes the LDO's `VIN` entirely (functionally equivalent to unplugging it), so flashing over the ESP32's USB-C just requires the switch to be off rather than physically disconnecting anything (switch back on immediately after — see the Inline Power Switch operating rule above). Note: with the switch off, `VIN` is floating rather than grounded, so a microamp-scale reverse leakage back onto that node via the LDO's parasitic body diode (`VOUT`→`VIN`) is theoretically possible while `VOUT` is USB-fed — not a real hazard for the MCP1700, not worth acting on.
- The Adafruit #5964 adapter's own onboard 5V boost for the SEN55 is fed from this same `3V3` rail (`VIN` direct, GND return switched by the BC547B transistor — see SEN55 Power Gate section above) — it never depended on TP4056's boost output, so this change doesn't affect it.

---

## Dock Detect Wiring (GPIO32, pin 7)

Same divider values and pin as hiking-monitor's `IN+` divider — TP4056 IN+ (USB VBUS) divided down to a safe GPIO level.

```
TP4056 IN+ ──── R3 (68kΩ) ──┬──── R4 (100kΩ) ──── GND
                             │
                      GPIO32 (pin 7, INPUT, no pull)
```

- USB absent: LOW → field mode
- USB present: HIGH → docked/charging (home mode)

Matches hiking-monitor's measured behavior (0.47V/5.1V raw → ~0.28V/~3.04V after the divider) — same TP4056 module, same divider values, expect the same result. Confirm with a multimeter during Step 3/4 rather than assuming.

**`IN+` is a separate node from the inline power switch entirely, upstream of it — not to be confused with the Battery Voltage Divider below.** `IN+` is TP4056's charging *input* pin, fed directly by whatever's plugged into micro-USB or solar; it senses "is external power present" and is completely unaffected by the inline switch's position (switch off doesn't touch this reading at all). The Battery Voltage Divider below is the opposite — it taps the switch's *output* node, so it only reads correctly when the switch is on.

---

## Battery Voltage Divider Wiring (GPIO34, pin 5)

**Corrected 2026-08-19** — the instructions doc's Hardware Context table originally said 68kΩ/68kΩ; hiking-monitor's actual `wiring.md` uses **100kΩ/100kΩ**. Matching the real value here, per Step 0's "match hiking-monitor's pattern, don't re-derive it" instruction. (68kΩ/100kΩ is the *dock-detect* divider above, a different one — not to be confused.)

**This divider taps the switch's output node — the opposite of the dock-detect divider above, which taps `IN+` upstream of the switch.** `LiPo BAT+ (post-switch)` below is the same node as TP4056's `BAT+` and the LDO's `VIN` (see Inline Power Switch and Power — MCP1700 LDO sections). Consequence: this reading is only meaningful with the switch on — with it off, this whole node is unpowered/floating, unlike the dock-detect divider, which keeps working regardless of switch position since `IN+` doesn't depend on it.

Divides LiPo voltage (3.5-4.2V) to fit ESP32 ADC range. Two equal 100kΩ resistors → 2:1 divider. Midpoint voltage = Vbatt / 2. ESPHome `filters: - multiply: 2.0` restores actual voltage.

```
LiPo BAT+ (post-switch) ──── R1 (100kΩ) ──┬── R2 (100kΩ) ──── GND
                                            │
                                     GPIO34 (pin 5, ADC input)
```

**Notes:**
- During breadboard testing without LiPo connected: wire the divider from the 3.3V rail instead as a placeholder, same as hiking-monitor's own bench-test approach. Replace with actual battery+ (post-switch) when the power system is integrated in Step 7.
- GPIO34 (pin 5) is an input-only pin — do not drive it as output. ADC use only.
- High-value resistors (100kΩ) minimize current draw from the divider itself — negligible against the LDO's own budget.
- **`LiPo BAT+ (post-switch)` is the same electrical node as the MCP1700 LDO's pin 2 (Middle, `VIN`)** — the switch's downstream junction feeds TP4056 `BAT+`, LDO `VIN`, and this divider's top resistor all from one node (see Inline Power Switch and Power — MCP1700 LDO sections above). Tap this divider from that junction, not a separate wire run back to the switch.

---

## RGB LED Wiring (GPIO18 pin 30 / GPIO19 pin 31 / GPIO23 pin 37)

**Confirmed 2026-08-19 against the actual physical module** (Greekcreit/Geekcreit 37-module kit, Plastic Box) — a KY-016: common-cathode, clear 5mm LED, 4-pin header silkscreened `- R G B` in that order, **with three current-limiting resistors already built onto the module's own small PCB.**

| Module Pin | ESP32 Pin | Board Pin # | External resistor? |
|---|---|---|---|
| `-` (common cathode) | GND | 38 / 32 / 18 / 14 (any GND pin) | — |
| `R` | GPIO18 | 30 | **None** — module has its own onboard resistor per channel; do not add an external one in series, it would only dim the LED further |
| `G` | GPIO19 | 31 | None (see above) |
| `B` | GPIO23 | 37 | None (see above) |

This deviates from `JCTsh-Build-Standards.md` §8's default (330Ω external, for a bare LED with no onboard resistor) — that default assumes a bare LED, not a pre-resistored module like this one. Wire the module's 4 pins straight to GND/GPIO18 (pin 30)/GPIO19 (pin 31)/GPIO23 (pin 37), no discrete resistors in the RGB LED's signal path.

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
└────┬────┘  └────────┘                    │       └──► adapter VIN (direct — GND return switched by BC547B transistor, below)
     │ IN+ (green)                          │                                  │
     ├──R3(68kΩ)──┬──R4(100kΩ)──GND         │                                  │
     │            └──────────────► GPIO32 (pin 7) │                            │
     │ BAT+ (post-switch, white)             │                                  │
     ├──R1(100kΩ)──┬──R2(100kΩ)──GND        │                                  │
     │             └──────────────► GPIO34 (pin 5) │                           │
     └──────────────────────────────────────┤ GND                              │
                                             │                                  │
                                             │ GPIO27 (pin 11) ──R(1k)── Base(BC547B transistor) │
                                             │           │      Collector◄─adapter GND
                                             │        R_pd(10k)  Emitter──GND   │
                                             │           │                      │
                                             │          GND                     │
                                             │                                  │
                                             │ GPIO21 (pin 33, SDA, blue) ◄─ SEN55 adapter │
                                             │ GPIO22 (pin 36, SCL, yellow) ◄─ SEN55 adapter │
                                             │ GPIO18/19/23 (pins 30/31/37) ──► RGB LED │
                                             └──────────────────────────────────┘
```

---

## Perfboard Footprint Measurement Procedure

**Performed at Step 9 (perfboard transfer), not Step 3** (moved 2026-08-20 — measuring before there's a real perfboard layout to size against was premature). Determines the minimum perfboard size. **Scope narrowed 2026-08-20:** the SEN55 module itself is no longer part of this measurement — it mounts externally to the enclosure via 3M tape (see the Phase 1 doc's Carry and Enclosure section), not inside it, so its 59mm × 37mm × 23mm footprint doesn't constrain the internal board layout at all. Only the small **Adafruit #5964 adapter** stays inside, connected to the externally-mounted SEN55 via the JST-GH cable through a pass-through hole. **Working assumption:** the same 5×7cm Chanzon FR4 board hiking-monitor uses (`components/hiking-monitor/perfboard-layout.md`) will probably work here too, likely with more headroom than originally expected now that SEN55 itself is out of the equation — this procedure confirms or corrects that assumption, not a from-scratch sizing exercise.

1. **Lay out the full component set** on a flat surface in their approximate final relative positions: ESP32 DevKitC-32 (with its two 19-pin female header strips, per `JCTsh-Build-Standards.md` §1.2), the Adafruit #5964 adapter (SEN55 itself is external — see above, not part of this layout), the BC547B transistor + its two resistors, the two voltage dividers (4 resistors total), the RGB LED module, the MCP1700 LDO, and the inline power switch.
2. **Measure the Adafruit #5964 adapter board** — its footprint plus mounting clearance around the JST GH connector, and clearance for the cable running to the pass-through hole.
3. **Determine overall bounding footprint** needed for ESP32 + adapter + discrete components with reasonable trace/solder-pad spacing (don't pack components edge-to-edge — leave room for hand-soldered traces).
4. **Compare against the standard 5×7cm Chanzon FR4 board** (`JCTsh-Build-Standards.md` §1.2 default) — report whether that standard size fits (expected, now that SEN55 is out of the internal footprint).

**Report back:** the adapter's footprint and whether the standard 5×7cm board is sufficient. (SEN55's own physical dimensions are still worth confirming with calipers when convenient — ~59mm × 37mm × 23mm per spec — but only for planning the external mount point and cable routing, not for perfboard sizing.)
