# JCTsh Perfboard Build Template

**Author:** Joseph C Thomas (JCT)
**Purpose:** Reusable section skeleton for a component's `perfboard-layout.md` — copy this structure when transferring a new component from breadboard to perfboard, fill in each section for the specific circuit.
**Version:** 1.0
**Version description:** Initial version, generalized from two real builds: hiking-monitor's original perfboard-layout.md (I2C sensors, battery/TP4056 power chain, display) and salt-sensor's CARD-0049 build (much simpler circuit, but which surfaced the bus-planning discipline, the silkscreen-label-over-position-number lesson, and the adjacent-pin isolation check practice).
**Related files:** `JCTsh-Build-Standards.md` (the actual rules this template's steps enact), `JCTsh-Component-Planning-Pattern.md` (the analogous template for the planning phase)

---

## What this is, and isn't

This is a **skeleton to copy**, not a rulebook — the actual standards (perfboard socketing, pin verification, bus planning criteria) live in `JCTsh-Build-Standards.md` §1.2 and are only summarized here where a step needs the reasoning inline. Read Build Standards first; use this template to structure the resulting per-component doc.

**When to use it:** any time a component moves from validated breadboard prototype to a permanent perfboard build (`JCTsh-Build-Standards.md` §1.2 — breadboard is prototyping-only, perfboard is the final install). Copy the section headers below into `components/<name>/perfboard-layout.md` and fill each one in for the actual circuit.

---

## Overview

*One paragraph: what's being transferred, why (which card), and a one-line summary of the circuit's actual complexity — sensors, power source, anything unusual. State plainly whether this is a simple or complex build relative to other JCTsh perfboard builds, so a reader knows how much of this template's structure is actually load-bearing versus overkill for a trivial circuit.*

*Add a `STATUS:` line at the top once the build is complete, e.g. "STATUS: COMPLETE (date). Perfboard soldered, all Pre-Power Checks passed, power-on test passed, reboot/power-cycle verification passed."*

---

## Board Note — read before touching a multimeter or iron

**Always include this section, even if you expect it to be trivial.** State the exact physical board/module in use (brand, model — not just "ESP32 DevKitC-32," since clone boards vary). If a documented pin-reference table already exists for this component, explicitly confirm (or correct) it against the actual physical board's printed silkscreen before relying on it anywhere else in this doc — **identify every pin by its printed label, not by an assumed position number** (`JCTsh-Build-Standards.md` §1.2). This was skipped on salt-sensor's first pass through this exact template and caused a real wiring mistake (Trig landed on the wrong pin) that only got caught during Pre-Power Checks — don't skip it.

If a photo of the actual board's silkscreen was taken, reference it here and save it alongside this doc.

---

## Board Selection

*Perfboard size (5×7cm Chanzon FR4 is the JCTsh default per Build Standards §1.2 — note if a different size is needed and why), and which physical microcontroller module is being socketed.*

---

## Component Placement

*Where each part sits and why — group parts that share a bus near each other (see Bus Planning below), keep sensor headers oriented correctly for their final mounted position, note anything about connector/cable exit points for the eventual enclosure.*

---

## Wiring Connections

*Table(s) per net type — Power, Ground, and each signal group (I2C, individual GPIO drive lines, etc.). Use the physical board's actual pin labels (per Board Note), not position numbers. Split into as many subsections as the circuit needs; a simple circuit might only need Power/Ground/Signal, a complex one may need per-peripheral subsections like hiking-monitor's (I2C, voltage dividers, display harness, etc.).*

---

## Bus Planning

For every multi-connection net, explicitly state whether a bus (a shared rail multiple components tap into) is warranted, and why. This is a deliberate pass, not an assumption — do it before the Assembly Sequence, since bus rows typically get soldered early as infrastructure everything else hangs off of.

- **Ground:** almost always warranted on any circuit with more than one peripheral — GND typically has the highest fan-out of any net. If warranted, note the actual consumer count and whether to build in spare tap points for future additions.
- **Power (VIN/5V/3.3V, whichever applies):** warranted only if there are genuinely 3+ consumers tapping a shared rail. A single consumer beyond the source itself doesn't warrant a bus — a direct point-to-point wire is equivalent and simpler. State the actual consumer count either way.
- **Any other net with 3+ consumers:** check explicitly, even if the answer is "none." Recording "no other bus warranted, here's why" is itself the useful artifact — it means a future revision doesn't have to re-derive the same analysis, and it catches a bus need that might otherwise go unnoticed.

---

## Assembly Sequence

*Numbered soldering steps, in physical build order. General shape that's proven out twice now:*

1. Mark microcontroller header positions, verify spacing against the actual board.
2. Solder header strips (test-fit before committing to the second side's exact position).
3. Solder any warranted bus(es) from Bus Planning above — early, since other steps depend on them.
4–5. *(Bus planning checkpoints for nets found NOT to warrant a bus — keep as explicit no-op steps rather than silently omitting them, so the decision is visible in the sequence, not just buried in prose above.)*
6+. Solder each component/peripheral, tying into the relevant bus(es) as it goes.
Final. Seat all socketed components, confirm any board-specific access needs (e.g. a microcontroller's onboard USB port needing physical clearance if it's also the power/flash connector). **Power-on test** as the last step — connect power, confirm boot behavior, connectivity, and data/status reporting all match what the breadboard prototype already validated.

---

## Pre-Power Checks

**Do the short-circuit check first**, always — a supply-to-ground short can damage the board on first power-up.

Numbered multimeter table, grouped by net (Short Circuit → Power Path → each bus → each peripheral circuit), each row: `# | Probe A | Probe B | Mode | Expected | Result`. Leave a `Result` column blank until the checks are actually run; fill it in and flip the section `STATUS:` to `COMPLETE` once done — don't just narrate results in prose, keep the table itself as the record.

**Always include an Adjacent-Pin Isolation subsection** at the end, even on a simple board — check isolation (expect open/no-beep) between any pin labels that sit physically close together on the silkscreen, especially anything with a similar-looking name (e.g. a GPIO number next to an alternate-function label like `TX2`/`RX2`). This directly caught a real mistake on salt-sensor's build and costs only a few extra minutes.

A short-circuit resistance check reading something less than true infinity (OL) on a populated board is normal, not a failure — onboard regulators and USB-serial chips have their own quiescent bias paths. The threshold in Build Standards (>100kΩ) is a floor, not a target.

For an LED circuit specifically: diode-test mode readings will typically be *lower* than the LED's rated forward voltage when a series resistor is in the path, since the meter's small test current is reduced further by the resistor — a real, non-zero, non-infinite reading is a pass; the LED's true brightness/forward voltage only shows up once driven by the microcontroller's actual GPIO output at power-on.

---

## Power-On Test

*Connect power, confirm: boot self-test/indicator behavior, WiFi/MQTT connect, data publishing, status round-trip (if applicable) — everything the original breadboard prototype already validated, now on the permanent build.*

---

## Reboot / Power-Cycle Verification

Not just an OTA-triggered soft reboot — a **cold power interruption at the actual power source**, since a warm reboot doesn't exercise WiFi association from scratch, MQTT re-auth, or a true cold-boot path the way a real power loss does. What "cold" means depends on the power source:

- **USB/wall-powered:** physically unplug and replug the power adapter.
- **Battery-powered:** disconnect and reconnect the battery connector (not just toggling a switch that only gates a downstream rail, if the microcontroller itself stays powered through that switch).

**Two clean cycles minimum** before considering this verified — the first could be a fluke, a repeat confirms it. Record each cycle's result (boot behavior, reconnect, first reading after reconnect) rather than just "passed."

---

## Notes

*Anything that doesn't fit cleanly above: deliberate deviations from Build Standards and why, GPIO/pin caveats (strapping pins, DAC-broken pins, anything flash-reserved), cross-references to the component's other docs. Always worth a line on whether a 3.3V rail is or isn't needed externally — easy to assume one's needed out of habit even when nothing on the board actually uses it.*
