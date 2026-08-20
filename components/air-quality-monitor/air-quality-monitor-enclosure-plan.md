# Air Quality Monitor — 3D Printed Enclosure Plan
**Author:** Joseph C Thomas (JCT)
**Purpose:** Planning document for the 3D printed clip-case enclosure for the JCTsh air-quality-monitor (ESP32 + Adafruit #5964 adapter + RGB LED + inline power switch + LDO/TP4056/LiPo on perfboard, SEN55 mounted externally). Follows the same planning process used for `hiking-monitor-enclosure-plan.md` — read that document for the reference pattern this one is modeled on.
**Project:** JCTsh — air-quality-monitor (CARD-0012)
**Version:** 1.0
**Version description:** Initial draft — captures decisions already made in `JCTsh-air-quality-monitor-phase1.md` and `air-quality-monitor-claude-code-instructions.md` (clip case + carabiner, SEN55 external mount) and lays out the open questions that still need physical measurement before CAD work can begin. **Updated 2026-08-20:** final print material decided as white ASA (matching hiking-monitor's own upgrade), correcting Phase 1's original PETG call — no longer an open question.
**Status:** Draft — pre-CAD. **Do not begin CAD work until the bench phase (Steps 0-9 in `air-quality-monitor-claude-code-instructions.md`) is confirmed complete**, per `JCTsh-Component-Planning-Pattern.md`'s bench-before-install rule. This document exists to capture the plan and open questions now, not to start building yet.
**Related files:** `hiking-monitor-enclosure-plan.md` (reference pattern), `hiking-monitor-enclosure-instructions.md` (reference execution pattern), `JCTsh-air-quality-monitor-phase1.md`, `air-quality-monitor-claude-code-instructions.md`, `wiring.md`, `JCTsh-Build-Standards.md`

---

## 1. Background and Context

Unlike hiking-monitor, air-quality-monitor has no field-tested prototype yet to validate against — this plan is being drafted in parallel with the electrical bench build (breadboard wiring confirmed, Step 4 firmware validation in progress), not after a proven three-board-sandwich prototype like hiking-monitor's camping-trip test. Treat every physical dimension below as provisional until Step 9's perfboard footprint measurement and a real component test-fit are done.

This is Joseph's second 3D-printed enclosure project (after hiking-monitor) — the same "simplicity and learnability over optimization" philosophy applies, and a second-generation enclosure is expected and acceptable here too.

---

## 2. What's Already Decided (from Phase 1 / instructions doc)

These are settled, not open questions — carried over here so this document is self-contained:

- **Clip case with carabiner**, independent of hiking-monitor's own enclosure — clips to the Osprey hydration pack's shoulder or sternum strap
- **3D-printed, white ASA for final print** (decided 2026-08-20, corrected from Phase 1's original PETG call) — matches hiking-monitor's own upgrade; better UV/heat resistance than PETG for Tucson outdoor use. PLA still used for the test-fit print, same as hiking-monitor.
- **No display** — data value is post-hike analysis, not moment-to-moment reading (Phase 1 decision). Only field-facing output is the RGB LED.
- **SEN55 mounts externally** (decided 2026-08-20) — 3M double-sided foam tape (on hand, Plastic Box) to the enclosure's smooth outer surface, cabled to the internal Adafruit #5964 adapter via the existing 100mm JST-GH cable (Bag 25) through a small pass-through hole. No intake/exhaust venting needed — the SEN55's own sealed metal housing/fan shield handles its own airflow. This is the single biggest structural difference from hiking-monitor's enclosure, which had to solve BME280/LTR-390 venting and sky-exposure problems that don't exist here.
- **Micro USB charging port + external JST solar port** — same general pattern as hiking-monitor (adapter dongle or panel-mount, TBD below)
- **Inline power switch** (Gebildet SS12D10, Bin A3) needs a wall slot, same general treatment as hiking-monitor's slide switch slot

---

## 3. Enclosure Concept — Single Shell, No Stack

Hiking-monitor's enclosure is a height-optimized two-shell stack because it separates a display/battery cavity from the main electronics cavity. Air-quality-monitor has no display and a much shorter component list — **provisionally a single-cavity two-shell box** (same bottom+top pb-tec `easyprojectboxv24.scad` two-shell approach as hiking-monitor, reusable toolchain) rather than a height-stacked design, unless the perfboard-plus-battery stack height argues otherwise once Step 9's measurements are in.

```
┌─────────────────────────────┐  ← Top shell (used inverted, same as hiking-monitor's pattern)
│  Main perfboard              │    ESP32, Adafruit #5964 adapter, BC547B gate,
│  (component side up)         │    RGB LED, both dividers, MCP1700 LDO
│  LiPo battery, TP4056         │
│  Inline power switch          │
└─────────────────────────────┘
       ↕  joined by M3 screws through corner bosses (same as hiking-monitor)

Exterior:
  - SEN55 module, 3M-taped to a smooth exterior face, cabled through a
    pass-through hole to the internal Adafruit adapter
  - RGB LED — visible through a small window/diffuser aperture, or possibly
    mounted flush at the wall itself (see Section 5)
  - Inline power switch actuator slot
  - USB-C charging slot (same adapter-dongle pattern as hiking-monitor, TBD)
  - Solar JST exit hole (same round-hole, no-cover pattern as hiking-monitor)
  - Carabiner bail
```

**Key open question this raises:** whether a single shell is actually sufficient, or whether the LiPo/TP4056/LDO stack plus perfboard still wants two cavities like hiking-monitor's. Resolve after Step 9.

---

## 4. SEN55 External Mount — Placement and Cable Routing

The one genuinely new mechanical problem this enclosure has that hiking-monitor's doesn't:

- **Cable length constrains mount position.** The JST-GH cable is 100mm. The SEN55 must be taped somewhere on the exterior within ~100mm of cable slack from wherever the pass-through hole lands — measure the actual internal routing path (adapter → pass-through hole → external cable run to the sensor) before picking a mount face, not just straight-line distance.
- **SEN55's own airflow needs are independent of this enclosure** (per the 2026-08-20 decision) — but the *mounting surface itself* still needs to be reasonably open to ambient air, not tucked against the pack or another surface that would block the sensor's own intake/exhaust. Pick an exterior face that stays clear when clipped to the pack strap.
- **Orientation:** per the (low-confidence, never independently re-verified) Sensirion guidance already on file — inlets above the outlet, opening face ideally downward. Worth actually confirming against Sensirion's primary documentation before finalizing the tape orientation, since this enclosure decision doesn't remove that open question, it just moves it from "vent design" to "tape orientation."
- **Serviceability:** 3M tape is not intended to be a permanent, one-time bond — confirm it's rated for outdoor temperature swings and repeated attach/detach if the SEN55 might ever need to come off for cleaning or the JST cable might need reseating.

---

## 5. RGB LED Field Indicator

Simplest exterior feature on this enclosure — no display, no ribbon cable routing problem like hiking-monitor's. Two options, not yet decided:

1. **Small window/aperture** over the KY-016 module, same general treatment as hiking-monitor's LTR-390 sky aperture (open hole, no cover — colored plastic diffusion isn't necessary for an RGB LED the way it might help even out brightness, but test before assuming)
2. **LED mounted flush at the wall itself**, module face pressed against a wall cutout sized to its body, rather than a separate light pipe/window — simpler if the module's footprint allows it

Resolve during CAD, informed by the module's actual measured size (KY-016, Plastic Box).

---

## 6. Carry and Mounting

Per Phase 1's decision: clip case with carabiner, independent of hiking-monitor's velcro-strap chest mount. No back-face velcro slots needed here — only a carabiner bail, same general design as hiking-monitor's (Section 6.2 there): printed loop, inner diameter from carabiner spine thickness, wall thickness 3-4mm, extends far enough proud of the wall to clear the carabiner body.

**Open question:** which carabiner. Hiking-monitor measured a specific carabiner's spine thickness (5.92mm) for its bail; air-quality-monitor needs its own measurement, potentially the same carabiner/clip hardware if Joseph intends a matching set, potentially different since this device clips to a strap rather than hanging from a pack loop.

---

## 7. Openings and Access Points

| Feature | Location (provisional) | Notes |
|---|---|---|
| SEN55 cable pass-through | TBD exterior face — see Section 4 | Small round hole, cable only, no connector body to pass through (unlike hiking-monitor's solar JST hole) |
| RGB LED window/mount | Front-facing wall | See Section 5 — window vs. flush-mount not yet decided |
| USB-C charging port | TBD wall | Same adapter-dongle pattern as hiking-monitor's, or a proper panel-mount USB-C — hiking-monitor used a hot-glued dongle as a known compromise; worth considering a cleaner panel-mount part for this second enclosure if one's on hand or cheap to source |
| ESP32 USB-C port | TBD wall | Emergency reflash access, same reasoning as hiking-monitor's (opening the screw-joined enclosure is the actual fallback either way) |
| Inline power switch | TBD wall | Slot sized to the Gebildet SS12D10 actuator, same treatment as hiking-monitor's slide switch slot |
| Solar JST connector | TBD wall | Round hole sized to the JST connector body, no cover — measure before modeling (same open item hiking-monitor had, still not resolved there either per its own Section 14) |
| Carabiner bail | Back or top face | See Section 6 |
| Shell join screws | Four corners | Same M3-through-top-shell-into-bottom-shell-bosses pattern as hiking-monitor, reusing the same heat-set-insert approach (Ruthex RX-M3x5x4, 4.2mm pilot hole) rather than re-deriving the nut-pocket-vs-insert decision hiking-monitor already made |

---

## 8. Materials and Filament

| Decision | Choice | Rationale |
|---|---|---|
| Test fit print | PLA | Same reasoning as hiking-monitor — fast, cheap, checks fit only |
| Final print | **White ASA (decided 2026-08-20, corrected from Phase 1's original PETG call)** | Matches hiking-monitor's own upgrade — better UV/heat resistance for Tucson outdoor use than PETG. No longer an open question; Xerocraft's Centauri Carbon (enclosed chamber, required for ASA) is the confirmed printer for this print, same as hiking-monitor's Session 2. |
| Color | White | Same reasoning as hiking-monitor — minimizes solar gain |

**Xerocraft printer info:** reuse hiking-monitor's own findings (`hiking-monitor-enclosure-plan.md` Section 10) rather than re-researching — confirm current availability before scheduling, since that research is now over a month old and the printer lineup has already changed once (A1 Mini retired mid-project).

---

## 9. CAD Toolchain

Same two-tool workflow as hiking-monitor — reuse the pattern, not just the tools:

1. **OpenSCAD** — reuse `components/hiking-monitor/enclosure/easyprojectboxv24.scad` as the starting template (same parametric box generator), with air-quality-monitor's own `SizeX`/`SizeY`/`SizeZ` etc. once Step 9's perfboard measurement and the component layout are known.
2. **Tinkercad** — cutouts and custom features (SEN55 cable pass-through, RGB LED window, USB-C slot, switch slot, solar JST hole, carabiner bail), same workflow hiking-monitor used.

No separate louvered vent insert needed for this build — the one piece of hiking-monitor's toolchain that doesn't carry over, since there's no BME280/LTR-390 venting problem here.

---

## 10. Open Questions (Resolve Before CAD)

| Question | When to resolve |
|---|---|
| Perfboard footprint — confirm the 5×7cm assumption | Step 9 (in progress — see `wiring.md`'s Perfboard Footprint Measurement Procedure) |
| Single-shell vs. two-shell stack height | After Step 9, once perfboard + battery/LDO/TP4056 stack height is known |
| SEN55 exterior mount face and cable routing path | Measure actual routing distance (not straight-line) from adapter position to candidate exterior faces |
| SEN55 mount orientation (inlet/outlet relative to ground) | Re-verify Sensirion's primary mechanical guidelines directly — current understanding is flagged low-confidence, sourced from search-snippet synthesis, never confirmed against the actual document |
| 3M tape suitability for outdoor temperature swings / repeated attach-detach | Confirm tape spec before committing to this as the permanent mount method |
| RGB LED window vs. flush-mount | Decide once KY-016 module's physical size is measured |
| USB-C charging port — adapter dongle (hiking-monitor's approach) vs. proper panel-mount connector | Decide before modeling the wall slot |
| Carabiner choice and spine thickness | Measure before modeling the bail |
| Solar JST connector body diameter and wire exit location | Same open item hiking-monitor never resolved either — measure before modeling |
| Screw/fastening hardware length | Confirm once real enclosure wall thickness and boss height exist — same caution as hiking-monitor and remote-temp-sensor-01, don't assume on-hand kit screws are long enough |

---

## 11. Success Criteria

The enclosure is complete when:

- [ ] Main perfboard seats correctly in the shell with no stress on solder joints
- [ ] SEN55 mounts securely to the exterior surface and stays attached through normal hiking use
- [ ] SEN55's cable reaches the internal adapter with slack to spare, routed cleanly through the pass-through hole
- [ ] RGB LED is visible/legible in daylight from the window or flush mount
- [ ] USB-C charging port is accessible and charges the LiPo correctly
- [ ] ESP32 USB-C port is accessible for emergency reflash without disassembly
- [ ] Inline power switch is operable without disassembly
- [ ] Solar JST connector exits cleanly and reaches the solar panel connector during backpacking use
- [ ] Carabiner bail accepts the chosen carabiner without flexing excessively
- [ ] Enclosure survives a full day hike clipped to the pack without coming loose or apart
- [ ] SEN55 readings after enclosure mounting are consistent with pre-enclosure bench baseline (confirms the external mount doesn't introduce airflow interference from its own tape/backing)

---

## 12. What This Enclosure Does NOT Address (Deferred to v2)

- Weatherproofing / gaskets — same reasoning as hiking-monitor, not needed for day hiking in the Sonoran Desert
- A dedicated cradle/dock for home-mode charging — charges via USB-C directly, cradle is a future enhancement if ever wanted
- Optimized SEN55 mount hardware (a proper clip or bracket instead of 3M tape) — v1 uses tape as the simple first pass; revisit for v2 once field use confirms whether tape is durable enough
