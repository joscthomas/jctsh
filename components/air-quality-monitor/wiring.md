# Air Quality Monitor — Breadboard Wiring Reference
**Component:** air-quality-monitor
**Purpose:** Complete wiring reference for the ESP32 breadboard prototype — target/desired wiring, not a build log. For build history, decisions, and lessons learned, see `tos/kanban-board.md` (CARD-0012, CARD-0198, CARD-0205, CARD-0213, CARD-0218) and `air-quality-monitor-claude-code-instructions.md`'s step-by-step notes.

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
| GPIO17 | 28 | Debug UART TX (transmit-only, `logger:` UART2) | External USB-TTL adapter |
| GPIO18 | 30 | RGB LED module — `R` pin (no external resistor — module has its own, see below) | Field indicator |
| GPIO19 | 31 | RGB LED module — `G` pin (same module, no external resistor) | Field indicator |
| GPIO21 | 33 | I2C SDA — blue | SEN55 (via Adafruit #5964 adapter) |
| GPIO22 | 36 | I2C SCL — yellow | SEN55 (via Adafruit #5964 adapter) |
| GPIO23 | 37 | RGB LED module — `B` pin (same module, no external resistor) | Field indicator |
| GPIO27 | 11 | Intent switch input (internal pull-up, inverted logic) | SS12D10 slide switch |
| GPIO32 | 7 | Dock detect (divider midpoint, INPUT) | TP4056 IN+ → 68kΩ → midpoint → 100kΩ → GND |
| GPIO34 | 5 | Battery ADC (input-only) | Voltage divider midpoint |

---

## SEN55 (via Adafruit #5964 Adapter) Wiring

**This sensor connects through two entirely separate interfaces, in series: ESP32 ↔ (bare wires) ↔ Adafruit #5964 adapter ↔ (JST-GH cable) ↔ SEN55.** Don't cross-reference wire colors between the two segments — they're different connection types with nothing in common (see below). (https://sensirion.com/media/documents/6791EFA0/62A1F68F/Sensirion_Datasheet_Environmental_Node_SEN5x.pdf)

### Segment 1 — ESP32 to adapter (bare wires, STEMMA QT color convention)

The adapter has a 4-pin **input** header, labeled directly on the Adafruit board: `VIN`, `GND`, `SCL`, `SDA`. This is a standard 0.1" header — you're making up individual jumper wires yourself here. Use the Adafruit STEMMA QT / SparkFun Qwiic color convention (black = GND, red = power, blue = SDA, yellow = SCL) rather than an arbitrary choice, matching `ESP32-project-pins.md`.

| Adafruit board pin (labeled on the board) | ESP32 Pin | Board Pin # | Wire Color | Notes |
|---|---|---|---|---|
| `VIN` | 3.3V (direct) | 1 | red | Board's own onboard boost converter steps this up to 5V internally, for the SEN55 side only |
| `GND` | GND | 38 / 32 / 18 / 14 (any GND pin) | black | Direct connection — no gate transistor, always-on whenever the device has power |
| `SDA` | GPIO21 | 33 | blue | I2C data |
| `SCL` | GPIO22 | 36 | yellow | I2C clock |

I2C address: 0x69 (fixed — no configurable address pin). No other I2C devices on this bus, no conflicts.

### Segment 2 — adapter to SEN55 (JST-GH cable, colors irrelevant)

**The adapter has a second, completely separate connector for this: a 6-pin JST-GH socket**, distinct from the 4-pin header above. This is what the SEN55 actually plugs into — it carries the boosted 5V, SDA, SCL, and the sensor's `SEL` interface-select line (Adafruit's board ties `SEL` to `GND` internally on this connector; there is no exposed `SEL` pin to wire by hand).

**The SEN55 sensor itself also has its own onboard 6-pin JST-GH socket** (built into the sensor's own PCB, inside its metal case) — this is separate from the Dupont-terminated pigtail cable the sensor was bundled with.

**Connection: plug the Bag 25 JST-GH cable directly between these two sockets** — one end into the Adafruit adapter's JST-GH socket, the other end into the SEN55's own onboard JST-GH socket.

**This cable is what makes the SEN55 external-mount design work** — the SEN55 module itself lives outside the enclosure, 3M-taped to its smooth exterior surface, while the adapter stays inside with the rest of the perfboard. This 100mm cable is the only connection between them, routed through a small pass-through hole in the enclosure wall. See the Phase 1 doc's Carry and Enclosure section and the Perfboard Footprint Measurement Procedure below.

- **Do not use the SEN55's bundled Dupont-terminated cable for this build at all** — set it aside. It's a separate breadboard-prototyping accessory, not part of this design.
- **Do not try to identify or match wire colors on the JST-GH cable.** Both sockets are the same fixed, keyed 6-pin JST-GH standard this sensor family is built around — the connector's physical shape guarantees pin 1 lines up with pin 1 (and so on) on both ends, regardless of what color any individual wire inside the cable happens to be. The SEN55's bundled Dupont cable and the Bag 25 JST-GH cable use *different, unrelated* wire-color conventions from different manufacturers — their colors have no relationship to each other.

Enable `scan: true` in the ESPHome `i2c:` block during initial testing to confirm the device is detected:
```
[I][i2c.arduino:069]: Found i2c device at address 0x69  ← SEN55
```

**SEN55's own 6-pin JST-GH connector pinout** (per Sensirion's official [SEN5x Datasheet PDF](https://sensirion.com/media/documents/6791EFA0/62A1F68F/Sensirion_Datasheet_Environmental_Node_SEN5x.pdf)):

| Pin | Signal | Notes |
|---|---|---|
| 1 | VDD | 5V ±10% supply |
| 2 | GND | |
| 3 | SDA | I2C data |
| 4 | SCL | I2C clock |
| 5 | SEL | Interface select — pull to GND (pin 2) to select I2C mode |
| 6 | NC | Do not connect |

**Useful diagnostic test point:** pin 1 (VDD) at the SEN55's own onboard socket is downstream of the entire power delivery chain (adapter's boost converter → JST-GH cable → sensor) — probing here directly confirms whether the sensor is actually receiving its 5V supply, independent of where in that chain a fault might be. A healthy ~5V here rules out the cable/connector/sensor as the problem.

---

## Debug UART — External USB-TTL Adapter (GPIO17, pin 28)

Serial console for viewing boot/runtime logs while the board is powered from its real LiPo/regulator path, independent of the ESP32's onboard USB-C port.

**Cannot use the board's own onboard USB-C port** — powering from USB and the battery regulator simultaneously is not supported (see the Power caution below), and the documented workaround (switch off before flashing) also kills battery power, so the onboard port can never show boot logs under real battery power. Also cannot tap the onboard CP2102's own TX0/RX0 (GPIO1/GPIO3) with a second adapter — those pins are already actively driven by the onboard chip, so a second driver on the same pins risks contention rather than a clean tap.

**Design:** `logger:` runs on a second UART (`hardware_uart: UART2`, `tx_pin: GPIO17`) instead of the default UART0/GPIO1. The logger is transmit-only (device → computer), so only 2 wires are needed:

```
ESP32 GPIO17 (pin 28) ────────────────────► Adapter RXD
ESP32 GND (any GND pin) ──────────────────► Adapter GND
Adapter VCC/3V3 ── NOT CONNECTED — board stays powered exclusively by battery/regulator, that's the whole point
```

**Adapter prep, before ever connecting it:** install the CP210x driver if Windows doesn't auto-detect it (same driver referenced in `front-porch-temp-sensor/flashing.md`/`garage-radar/flashing.md`), and **set the adapter's voltage-select jumper to 3.3V, not 5V** — the ESP32's GPIO is a 3.3V logic device.

---

## Inline Power Switch — True Transport/Storage Off

Wired **directly into the battery+ path**, ahead of both the TP4056 and the regulator's `VIN` tap, so switching it off isolates the entire board from the battery with zero current draw. It is not connected to any GPIO and does not appear in the GPIO table above.

**Part: BK-1208 latching push button** (2-pin, DC 30V 1A, 12×8×8mm). A simple 2-lead part, not SPDT — wire its two leads directly in the battery+ path:

```
LiPo BAT+ ──── SW ────┬──── TP4056 BAT+
                       └──── Pololu D24V10F3 VIN
```

**Verification (Step 7):** with the switch off, confirm zero voltage/current downstream at both the TP4056 `BAT+` pad and the regulator's `VIN` pin — not just "the board is unresponsive," which could also be explained by a firmware hang. Measure directly.

**Operating rule: switch ON for all device operation** — breadboard bench work after Step 7, field mode, home mode (docked and charging via TP4056), everything. **Switch OFF only for storage/transport**, with one narrow exception: briefly OFF while flashing over the ESP32's own USB-C port (see the Power caution below) — switch back ON immediately after. Switching off for TP4056 charging is *not* this exception and should not be done — the switch sits ahead of TP4056's `BAT+` too, so turning it off disconnects the battery from the charger and charging simply stops.

---

## Intent Switch Wiring (GPIO27, pin 11)

Signals whether the device is actively collecting field data — a plain GPIO-read digital input, **not in the power path**. Same pin role and wiring pattern as hiking-monitor's own Intent switch (`components/hiking-monitor/wiring.md`'s Slide Switch Wiring section).

**Part: Gebildet SS12D10 slide switch** (SPDT, wired as SPST).

| Switch terminal | Wire color | ESP32 pin | Notes |
|---|---|---|---|
| Terminal 1 | Brown | GPIO27 (pin 11) | Switch ON (closed) pulls GPIO27 LOW |
| Terminal 2 | Black | GND | |

Switch ON (closed): GPIO27 pulled LOW → collecting field data (Intent = actively hiking/logging).
Switch OFF (open): GPIO27 floats HIGH via internal pull-up → idle/ready-to-upload.

**Breadboard wiring:** brown jumper from one switch terminal to the GPIO27 breadboard row, black jumper from the other terminal to the GND rail.

**Firmware:** `wifi.enable()` gates on this switch being off (session genuinely over) — never on `dock_detect` alone, since `dock_detect` is shared with solar and says nothing about whether data collection has actually stopped. See `air-quality-monitor-claude-code-instructions.md` Step 8 for the full firmware design.

---

## TP4056 Module Wiring

Same physical TP4056+boost combined module as hiking-monitor (Bag 8) — see `components/hiking-monitor/wiring.md`'s "TP4056 Perfboard Connector" section for the reference module pinout (pins named `IN+`, `BAT+`, `VOUT−`, `VOUT+` there). On this design, **only the charging half of the module is used** — the boost stage (`VOUT+`) is bypassed in favor of the Pololu D24V10F3 regulator (see Power section below), so only three of the module's four pads are wired.

| Module Pin | Wire Color | Connects To |
|---|---|---|
| `IN+` | green | Dock Detect divider — R3 (68kΩ) top leg, → GPIO32 (pin 7). See Dock Detect Wiring below. **Shared input** — also where the SUNYIMA solar panel's positive lead connects (see Solar Input below); USB and solar are electrically parallel sources into this same node, not separate inputs. |
| `IN−` | — | Solar panel's negative lead connects here (see Solar Input below) — the module's only exposed ground pad for the solar/USB charge-input side. Not separately wired to anything else; USB-side ground is internal to the module's own micro-USB connector. |
| `BAT+` | white | Inline power switch downstream node — same node as the regulator's `VIN` and the Battery Voltage Divider's top leg. See Inline Power Switch above and Battery Voltage Divider Wiring below. |
| `VOUT−` (GND) | black | Common GND — ties the module's ground return into the shared ground with the ESP32, regulator, and both dividers. |
| `VOUT+` | — | **Unused, leave unconnected** — boost stage bypassed on this design. Do not wire to anything (unlike hiking-monitor, which uses this pin as its 5.7V boosted supply). |

**Note:** hiking-monitor's own reference connector exposes only `IN+`, `BAT+`, `VOUT−`, `VOUT+` for the identical physical module — the module's `BAT−` pad is tied internally to `VOUT−`, with no separate pad broken out for it. `IN−` is exposed and wired here (unlike on hiking-monitor's connector) specifically because the solar panel's negative lead needs it. Confirm both `IN−` and the `BAT−`/`VOUT−` internal tie with a continuity check against the physical module before relying on this.

### Solar Input (Backpacking Only)

The TP4056+boost module supports solar input natively — no separate charge controller needed. **This connects to the same `IN+`/`IN−` pads as the micro-USB charging input above**, not a distinct input on the module — solar and USB are electrically parallel sources into the same charge-input node. Consequence: since `IN+` is also the Dock Detect tap (GPIO32), connecting the solar panel — or charging via USB in the field, e.g. from a power bank while backpacking — raises `IN+` exactly like docking at home does, and the device reads as docked (GPIO32 HIGH) even out on trail.

Field-mode duty-cycle logging runs unconditionally regardless of dock-detect state; dock-detect HIGH only triggers a bounded-window background WiFi attempt against both `JCTnet1` and the Pixel hotspot (`secrets.yaml`), gated on the Intent switch being off (see Intent Switch Wiring above and `air-quality-monitor-claude-code-instructions.md` Step 8 for the full firmware behavior).

**Part:** SUNYIMA solar panel, 5.5V/80mA (Bag 6) — bare-lead panel, no connector attached. Solder a JST male plug to the panel's leads and a JST female receptacle wired to the module's `IN+`/`IN−` pads, verifying polarity with a multimeter before connecting (same procedure as LiPo polarity check). Likely connector source: the general-purpose JST SM 2-Pin Connectors assortment (Bag 14, `jctsh-parts-inventory.md`) — confirm before use.

Solar panel mount/clip design is deferred — only relevant for multi-day backpacking; the 1100mAh LiPo covers day hikes without it.

---

## Power — Pololu D24V10F3 Regulator (Direct LiPo-to-3.3V)

**Pololu D24V10F3 — 3.3V, 1A step-down (buck/switching) regulator**, small breakout board with 0.1" pin headers. Sized for the real coincident peak load (WiFi TX burst + SEN55 active + ESP32 baseline, ~450mA design peak, per `JCTsh-Build-Standards.md` §2.14 point 9's 2-3x headroom rule). TP4056's charging half is unchanged and still used; only its boost stage is bypassed.

**Pinout (silkscreen-labeled):**

| Pin | Signal |
|---|---|
| VIN | Battery+ (post-switch) |
| GND | Common ground |
| VOUT | Regulated 3.3V out |

```
LiPo BAT+ (via inline switch) ──┬──── TP4056 BAT+ (charging only — TP4056's boost pads unused)
                                 │
                                 ├──── Pololu D24V10F3 VIN
                                 │     D24V10F3 GND ──── common GND
                                 │     D24V10F3 VOUT ──┬── 470µF electrolytic ──┐
                                 │                      ├── 4.7µF ceramic ──────┤
                                 │                      │         (both to GND) │
                                 │                      └─────────────────────────► ESP32 3V3 pin directly
                                 │
                                 └──── Battery Voltage Divider — R1 (100kΩ) top leg
                                       (see Battery Voltage Divider Wiring below;
                                       same node as VIN, not a separate wire run)
```

**Bulk capacitance at the point of load** — both capacitors in parallel, directly across the ESP32's 3V3 pin and an adjacent GND pin, not just "somewhere on the rail":
- **470µF electrolytic** — from the 28-value 0.1µF-4700µF assortment kit (`jctsh-parts-inventory.md`, Plastic Box); any 10V+ rated value in that kit works on a 3.3V rail.
- **4.7µF ceramic** — BOJACK 10-value assortment kit (`jctsh-parts-inventory.md`, Bag 39); catches the sub-millisecond edge of a transient the electrolytic's own ESR can't fully absorb.

- **Regulator `VIN` taps the battery+ node in parallel with TP4056's `BAT+` input and the Battery Voltage Divider's top leg** — three things sharing one node straight off the raw battery (through the inline switch), not fed from TP4056's boost/`VOUT+` output.
- **Regulator `VOUT` → ESP32 dev board's `3V3` pin directly** (not `VIN`) — `VIN` expects ~5V and routes through the board's own onboard regulator; feeding `3V3` bypasses that second regulation stage.
- **Caution: never power the board from USB and the regulator at the same time** — both would drive the `3V3` rail from separate unisolated sources, risking backfeeding either regulator. Disconnect the battery-side regulator before flashing over USB, and vice versa. (Breadboard Steps 4-6 power via USB only — do not connect the LiPo/regulator until Step 7.) **This is scoped specifically to the ESP32's own USB-C port** — the TP4056's separate micro-USB charging port never touches `3V3` at all, it only feeds the LiPo via the charge circuit (see Dock Detect Wiring below); charging via TP4056 while the regulator powers the ESP32 off the battery is normal, expected home-mode operation, no need to switch off for that. **The inline power switch satisfies the ESP32-USB-C case** — switching it off removes the regulator's `VIN` entirely (functionally equivalent to unplugging it), so flashing over the ESP32's USB-C just requires the switch to be off, switched back on immediately after (see the Inline Power Switch operating rule above).
- The Adafruit #5964 adapter's own onboard 5V boost for the SEN55 is fed from this same `3V3` rail (`VIN` direct, `GND` also direct — no gate transistor) — unaffected by the regulator choice.

**Minimum input voltage:** being a pure buck (step-down-only) topology, this regulator cannot boost — if VIN drops below VOUT plus dropout, output sags with input. Documented input floor is 3.4V, with dropout increasing under load. This sits close to the standard §2.14 point 2 low-battery firmware cutoff (also 3.4V) — confirm via bench measurement that output holds clean 3.3V at 3.4V VIN under a real WiFi-burst load, or raise this device's own low-battery cutoff threshold to give real margin, before considering the power system final.

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

**`IN+` is a separate node from the inline power switch entirely, upstream of it — not to be confused with the Battery Voltage Divider below.** `IN+` is TP4056's charging *input* pin, fed directly by whatever's plugged into micro-USB or solar; it senses "is external power present" and is completely unaffected by the inline switch's position. The Battery Voltage Divider below is the opposite — it taps the switch's *output* node, so it only reads correctly when the switch is on.

---

## Battery Voltage Divider Wiring (GPIO34, pin 5)

**This divider taps the switch's output node — the opposite of the dock-detect divider above, which taps `IN+` upstream of the switch.** `LiPo BAT+ (post-switch)` below is the same node as TP4056's `BAT+` and the regulator's `VIN` (see Inline Power Switch and Power sections). This reading is only meaningful with the switch on — with it off, this whole node is unpowered/floating.

Divides LiPo voltage (3.5-4.2V) to fit ESP32 ADC range. Two equal 100kΩ resistors → 2:1 divider. Midpoint voltage = Vbatt / 2. ESPHome `filters: - multiply: 2.0` restores actual voltage.

```
LiPo BAT+ (post-switch) ──── R1 (100kΩ) ──┬── R2 (100kΩ) ──── GND
                                            │
                                     GPIO34 (pin 5, ADC input)
```

**Notes:**
- During breadboard testing without LiPo connected: wire the divider from the 3.3V rail instead as a placeholder, same as hiking-monitor's own bench-test approach. Replace with actual battery+ (post-switch) when the power system is integrated in Step 7.
- GPIO34 (pin 5) is an input-only pin — do not drive it as output. ADC use only.
- High-value resistors (100kΩ) minimize current draw from the divider itself — negligible against the regulator's own budget.
- **`LiPo BAT+ (post-switch)` is the same electrical node as the Pololu D24V10F3's `VIN` pin** — the switch's downstream junction feeds TP4056 `BAT+`, regulator `VIN`, and this divider's top resistor all from one node. Tap this divider from that junction, not a separate wire run back to the switch.

---

## RGB LED Wiring (GPIO18 pin 30 / GPIO19 pin 31 / GPIO23 pin 37)

**Greekcreit/Geekcreit 37-module kit (Plastic Box)** — a KY-016: common-cathode, clear 5mm LED, 4-pin header silkscreened `- R G B` in that order, **with three current-limiting resistors already built onto the module's own small PCB.**

| Module Pin | ESP32 Pin | Board Pin # | External resistor? |
|---|---|---|---|
| `-` (common cathode) | GND | 38 / 32 / 18 / 14 (any GND pin) | — |
| `R` | GPIO18 | 30 | **None** — module has its own onboard resistor per channel; do not add an external one in series, it would only dim the LED further |
| `G` | GPIO19 | 31 | None (see above) |
| `B` | GPIO23 | 37 | None (see above) |

This deviates from `JCTsh-Build-Standards.md` §8's default (330Ω external, for a bare LED with no onboard resistor) — that default assumes a bare LED, not a pre-resistored module like this one. Wire the module's 4 pins straight to GND/GPIO18 (pin 30)/GPIO19 (pin 31)/GPIO23 (pin 37), no discrete resistors in the RGB LED's signal path.

---

## Power (Breadboard Phase — Steps 4-6)

Power ESP32 via USB-C cable from PC during breadboard Steps 4-6. Do NOT connect the LiPo/regulator until Step 7 (power system integration with polarity verification) — see the Power caution above about not powering from USB and the battery regulator simultaneously.

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
┌────▼────┐  ┌───▼──────┐                  │                                  │
│ TP4056  │  │ Pololu   │──VOUT──┬─────────►│ 3V3 (pin 1)                      │
│(chg only)│  │D24V10F3  │        │ (bulk    │       │                          │
└────┬────┘  └──────────┘        │  caps)   │       └──► adapter VIN (direct — GND also direct, no gate transistor) │
     │ IN+ (green)                          │                                  │
     ├──R3(68kΩ)──┬──R4(100kΩ)──GND         │                                  │
     │            └──────────────► GPIO32 (pin 7) │                            │
     │ BAT+ (post-switch, white)             │                                  │
     ├──R1(100kΩ)──┬──R2(100kΩ)──GND        │                                  │
     │             └──────────────► GPIO34 (pin 5) │                           │
     └──────────────────────────────────────┤ GND ◄── adapter GND (direct, always-on) │
                                             │                                  │
                                             │ GPIO27 (pin 11) — Intent switch (brn) ◄─ SS12D10 (blk)─ GND │
                                             │ GPIO17 (pin 28) ──► debug UART adapter RXD │
                                             │                                  │
                                             │ GPIO21 (pin 33, SDA, blue) ◄─ SEN55 adapter │
                                             │ GPIO22 (pin 36, SCL, yellow) ◄─ SEN55 adapter │
                                             │ GPIO18/19/23 (pins 30/31/37) ──► RGB LED │
                                             └──────────────────────────────────┘
```

---

## Perfboard Footprint Measurement Procedure

Performed at Step 9 (perfboard transfer). Determines the minimum perfboard size. The SEN55 module itself is not part of this measurement — it mounts externally to the enclosure via 3M tape (see the Phase 1 doc's Carry and Enclosure section), not inside it, so its 59mm × 37mm × 23mm footprint doesn't constrain the internal board layout. Only the small **Adafruit #5964 adapter** stays inside, connected to the externally-mounted SEN55 via the JST-GH cable through a pass-through hole. Working assumption: the same 5×7cm Chanzon FR4 board hiking-monitor uses (`components/hiking-monitor/perfboard-layout.md`) should fit — this procedure confirms or corrects that assumption.

1. **Lay out the full component set** on a flat surface in their approximate final relative positions: ESP32 DevKitC-32 (with its two 19-pin female header strips, per `JCTsh-Build-Standards.md` §1.2), the Adafruit #5964 adapter (SEN55 itself is external — see above, not part of this layout), the two voltage dividers (4 resistors total), the RGB LED module, the Pololu D24V10F3 regulator plus its two bulk capacitors, and the inline power switch. No gate transistor in this design.
2. **Measure the Adafruit #5964 adapter board** — its footprint plus mounting clearance around the JST GH connector, and clearance for the cable running to the pass-through hole.
3. **Determine overall bounding footprint** needed for ESP32 + adapter + discrete components with reasonable trace/solder-pad spacing (don't pack components edge-to-edge — leave room for hand-soldered traces).
4. **Compare against the standard 5×7cm Chanzon FR4 board** (`JCTsh-Build-Standards.md` §1.2 default) — report whether that standard size fits.

**Report back:** the adapter's footprint and whether the standard 5×7cm board is sufficient. (SEN55's own physical dimensions are still worth confirming with calipers when convenient — ~59mm × 37mm × 23mm per spec — but only for planning the external mount point and cable routing, not for perfboard sizing.)
