# Hiking Monitor — 3D Printed Enclosure Plan
**Author:** Joseph C Thomas (JCT)
**Purpose:** Planning document for the first 3D printed enclosure for the JCTsh hiking monitor (ESP32 + BME280 + LTR-390 + e-ink display + TP4056 + LiPo on perfboard stack).
**Project:** JCTsh — hiking-monitor
**Version:** 1.5
**Version description:** Added Section 0 (Current State Summary) capturing the Part 2 measurement session and Part 3 CAD session results — footprint enlarged for LTR-390 overhang, velcro redesigned to 2 independent straps (4 slots) on the top shell's long wall, switch relocated to the ESP32's USB-C wall with internal mounting, solar connector simplified to a plain wire pass-through, boss/nut-pocket approach finalized, no ESP32 USB-C reflash port. Corrected: top shell also gets the template's unconditional corner bosses (sized as plain clearance, not nut pockets) — not "no bosses" as first stated. Added file management strategy (raw vs. final STL naming, Tinkercad project naming, why the split matters given Tinkercad has no local source/edit log). Several original sections below are now superseded by Section 0 — kept for historical rationale.
**Status:** Draft — ready for CAD work
**Related files:** enclosure-prototype.md, JCTsh-Build-Standards.md

---

## 0. Current State Summary (2026-07-03 CAD session)

This section reflects what was actually decided during the Part 2 measurement and Part 3 CAD sessions — several details below **supersede** the original v1.3 sections that follow (footprint size, velcro strap design, switch/solar wall placement, etc.). Kept both so the history of *why* is preserved, but treat this section as the current source of truth.

**Overall concept:** two 3D-printed shells (bottom + top) stack and join with four M3 screws through corner bosses. Uses the pb-tec `easyprojectboxv24.scad` parametric template (`components/hiking-sensor/enclosure/easyprojectboxv24.scad`), rendered twice with `Show=1` (body only, lid discarded both times) since the template is a box+thin-lid generator, not a native two-shell design.

**Bottom shell contains:**
- Main perfboard (ESP32, BME280, LTR-390, voltage divider)
- Louvered vent insert (separate printed part, press-fits into a wall cutout) for BME280 airflow
- LTR-390 sky aperture — hole in the top face, positioned 4mm from the long edge / 11.5mm from the short edge of the perfboard's corner
- Slide switch — internally mounted (tabs/body inside, only the 7×4mm actuator slot exposed), on the wall the ESP32's USB-C port faces (not the plan's original "left short-end wall" default)
- Solar panel wire pass-through — small hole for 2 bare wires only (connector is on flying leads, not panel-mount), left long wall near the ESP32
- Perfboard sits on brass M3 male-female standoffs (ZYAMY kit) — plain clearance holes in the floor, no thread/nut-trap needed in the printed plastic (the standoff itself provides the thread)
- Four corner screw bosses with M3 hex nut pockets (added in Tinkercad — the OpenSCAD template's own hole type is round, not hex) — no extra mid-wall bosses (`AddXScrew`/`AddYScrew` set `false`)
- No dedicated ESP32 USB-C emergency-reflash port — opening the screw-joined enclosure gives access if ever needed
- Current OpenSCAD values: `SizeX=63` (depth), `SizeY=79` (width), `SizeZ=33`, `WallThick=3`, `ScrewCylinderDia=10`, `Show=1` — footprint enlarged from the bare 50×70mm board to fit the LTR-390's corner overhang (see Section 6 update below)

**Top shell contains:**
- E-ink display, mounted directly over the ESP32's position (not routed to a side wall as originally planned — the ribbon cable exits from the middle of a long edge, not a short edge, so it routes straight down through the shell join instead)
- LiPo battery, TP4056 charge/boost module
- USB-C charging port — hot-glued adapter dongle (not a proper panel-mount connector), 12mm × 8mm wall slot
- Two independent velcro straps (4 slots total, not one strap through 2 slots as originally planned — reduces device wobble on the pack's chest strap), on the long wall matching the LTR-390's side, within this shell only (not spanning the shell seam)
- Carabiner bail (~9mm inner diameter, from a measured 5.92mm spine thickness + 3mm clearance)
- Corner bosses come from the same template (unconditional in the template's geometry — cannot be turned off, only the *extra* mid-wall ones via `AddXScrew`/`AddYScrew` can be disabled), but `HoleDiaThread` here is just a plain M3 clearance hole, not a thread/nut-pocket hole — no self-tapping or heat-set insert on this shell, the screw just passes through freely
- Current OpenSCAD values: same `SizeX`/`SizeY`/`WallThick`/`Rounding`/`HolePos`/`ScrewCylinderDia` as the bottom shell (must match exactly for the corner bosses/holes to line up vertically when stacked), only `SizeZ` differs = `19` (16mm internal + 3mm wall)

**How they join:** four M3 screws pass through the top shell's boss clearance holes, down into the bottom shell's corner bosses, threading into M3 hex nuts captured in pockets there (bottom shell only). Screw length from the on-hand ZYAMY kit (M3×6mm) is likely too short once real dimensions are accounted for — probably need longer M3 screws (8-12mm), to be confirmed once assembly is test-fit.

**File management strategy:**
```
components/hiking-sensor/enclosure/
├── easyprojectboxv24.scad       — original downloaded template, left unmodified (reference/backup)
├── bottom-shell.scad            — template + bottom shell's specific parameter values
├── top-shell.scad               — template + top shell's specific parameter values
├── bottom-shell-raw.stl         — OpenSCAD export: box + bosses only, BEFORE Tinkercad edits
├── top-shell-raw.stl            — same, top shell
├── bottom-shell-final.stl       — AFTER all Tinkercad cutouts/features — what actually gets sliced/printed
├── top-shell-final.stl          — same, top shell
├── vent-insert.stl              — separate small part, modeled entirely in Tinkercad (no OpenSCAD source)
└── bottom-shell-floorplan.svg   — visualization aid
```
Tinkercad itself has no local "source file" or edit log — its cloud projects are the only record of what cutouts were made, so the `-raw` vs `-final` STL naming split matters: `-raw` always reflects the current OpenSCAD state cleanly, and every cutout's exact dimensions/position gets written down here (Section 0) and in memory as the effective reproduction record, since Tinkercad edits can't be "replayed" automatically. Tinkercad cloud projects should be named to match (e.g. "hiking-monitor bottom shell," "hiking-monitor top shell," "hiking-monitor vent insert") for Joseph's own account organization.

**Other separate printed parts:** the louvered vent insert (bottom shell, BME280 airflow).

**Not yet resolved as of this session:** whether the current boss size/position (`ScrewCylinderDia=10`, `HolePos` default) actually clears the perfboard footprint and the LTR-390 overhang corner — to be confirmed visually in Tinkercad (Step 16+) by overlaying a 50×70mm test rectangle, not by further hand calculation.

---

## 1. Background and Context

The hiking monitor field prototype used two extra perfboards (5cm × 7cm each) attached above and below the main perfboard with brass standoffs, forming a three-board sandwich approximately 5cm tall. This prototype was carried on a camping trip to validate the form factor, display readability, sensor exposure, and battery life before committing to a 3D printed case.

This document captures all design decisions for the permanent printed enclosure, informed by what the prototype validated. This is Joseph's first 3D printed enclosure project; the design philosophy prioritizes simplicity and learnability over optimization. A second-generation enclosure is expected and acceptable.

---

## 2. What the Prototype Validated

- Display is readable in sunlight when face-up on the top board
- Switch and USB ports are accessible from the sides of the stack
- LTR-390 sensor reads UV correctly with open-sky exposure
- BME280 temperature reads correctly with airflow through the open sides of the stack
- Battery life is acceptable for day hikes
- The stacked layout (display/battery cavity above, main electronics below) is practical to carry

---

## 3. Enclosure Concept — Height-Optimized Stack

The printed enclosure translates the proven three-board sandwich into two printed shells joined by screws, with the internal cavity height tightened to the minimum needed to house actual components rather than the over-tall standoffs used in the prototype.

```
┌─────────────────────────────┐  ← Top shell (front face = display face)
│  e-ink display (landscape)  │    display aperture on front face
│  LiPo battery               │    in upper cavity
│  TP4056 + USB-C adapter     │    USB-C slot on right short-end wall
│  [ribbon cable exits left]  │    routes down to main board header
└─────────────────────────────┘
       ↕  joined by M3 screws through corner bosses
┌─────────────────────────────┐  ← Bottom shell
│  Main perfboard             │    ESP32, BME280, LTR-390, voltage dividers
│  (component side up)        │    solder joints face DOWN, open at base
│  Louvered vent insert       │    in long side wall, BME280/LTR-390 end
│  LTR-390 sky aperture       │    hole in top face above LTR-390 corner
│  Slide switch slot          │    in left short-end wall
│  Solar JST exit hole        │    in left short-end wall or long side wall
└─────────────────────────────┘

Back face (both shells combined):
  - Two velcro strap slots along 70mm width, near top  ← wraps chest strap webbing
  - Carabiner bail near top, between or beside slots
```

See Section 15 for the exploded diagram reference.

### Key geometry

| Dimension | Value | Source |
|---|---|---|
| Main perfboard footprint | 50mm × 70mm | Measured |
| Overall stack height (prototype) | ~50mm | Measured |
| Target printed height | 35–42mm | Tighten to actual component stack; measure before modeling |
| Wall thickness | 2.0–2.5mm | Standard for FDM enclosures |
| Corner boss diameter | 6mm OD, M3 through-hole | Standard |

**Critical measurement before CAD:** Measure the actual height from the bottom of the main perfboard to the top of the tallest component above it (likely the ESP32 or display header pins). Then measure the TP4056 + LiPo stack height. These two numbers determine the minimum cavity heights for each shell. Do not guess — measure with a ruler before opening the CAD tool.

---

## 4. Sensor Exposure Strategy

### 4.1 BME280 — Stevenson Screen Louvered Vent

The BME280 must be shaded from direct solar radiation while still receiving ambient airflow for accurate temperature and humidity readings. Direct sun on the sensor body causes artificially elevated temperature readings.

**Approach:** A separate small louvered vent insert that press-fits into a rectangular cutout in the long side wall of the bottom shell, positioned at the BME280/LTR-390 corner end.

**Why a separate insert:**
- Easier to model independently — the main shell just needs a rectangular cutout
- The insert can be iterated (reprint just the insert if louver spacing needs adjustment) without reprinting the whole enclosure
- Lower CAD complexity for a first project

**Louver design guidelines:**
- Horizontal angled slats, angled downward toward the outside — blocks rain and direct overhead sun, allows horizontal airflow
- Slat angle: 45° is conventional; blocks direct sun from above while allowing air movement
- Slat spacing: 2–3mm gap between slats is sufficient for airflow
- Insert overall size: size to match the rectangular cutout in the shell wall; keep small (20–25mm wide, 15mm tall is plenty for a single sensor)
- Fit: slight interference fit (0.1–0.2mm tighter than the cutout) so it presses in snugly; no screws needed at this size

### 4.2 LTR-390 — Top Face Sky Aperture

The LTR-390 UV sensor chip sits on the top surface of the Adafruit breakout board and must have an unobstructed view of the sky. The active surface faces upward.

**Approach:** A circular or rectangular hole in the top face of the bottom shell, positioned directly above the LTR-390 breakout board's corner location on the main perfboard.

**Design notes:**
- No cover, no glass, no plastic film — any transparent material will block some UV
- Hole size: 8–10mm diameter is sufficient; larger is fine, smaller risks partial obstruction if placement is slightly off
- Position: at the corner of the top face corresponding to the LTR-390 corner of the board; confirm exact position from board measurement before modeling
- Rain exposure: acceptable — the sensor is not damaged by water, and the device is not intended for use in rain

### 4.3 BME280 and LTR-390 are at the same corner

Both sensors are clustered at the same corner of the main perfboard (along the 70mm side, at the end near one 50mm short wall). This means:
- The louvered vent insert goes in the **long side wall** (70mm wall) nearest that corner
- The sky aperture goes in the **top face** at that same corner
- Both features are concentrated in one corner region — simplifies modeling

---

## 5. Display Orientation and Ribbon Cable Routing

### 5.1 Display orientation

The Waveshare 2.13" e-ink display is a landscape rectangle (wider than tall, approximately 2:1 ratio). It is mounted in **landscape orientation** on the front face of the top shell so that text reads correctly when the device is flipped upward to be read while hanging from the chest strap.

Display image rotation is set in ESPHome firmware to match however the display module is physically installed. The firmware setting is trivially adjusted during breadboard testing and does not constrain the physical mounting decision.

### 5.2 Ribbon cable exit direction

With the display in landscape orientation, the ribbon cable exits from one of the **short edges** of the display module — left or right. The cable is routed toward the **left short-end wall** of the enclosure, then down through the shell join gap to the main board header in the bottom shell.

The left wall has only a small slide switch slot low on its face, leaving adequate room for the ribbon cable to pass internally without conflict. Cable length will be adjusted to fit during assembly — there is sufficient slack in the existing harness.

---

## 6. Carry and Mounting

### 6.1 Primary mount — velcro strap to chest strap

Two slots in the **back face of the enclosure, near the top, spaced along the 70mm width**. The slots run along the long axis of the enclosure for maximum stability — spacing them across the full width prevents the enclosure from rocking or rotating on the chest strap. A velcro strap threads through both slots and wraps **perpendicular** to the Osprey hydration pack chest strap webbing, cinching the enclosure snugly against the strap. The enclosure hangs display-outward; to read it, flip the device upward from the strap slots as a pivot point.

**Slot design notes:**
- Two slots spaced well apart along the 70mm back face width
- Slot width: 22–26mm (measure your velcro strap before modeling)
- Slot height: 3–4mm (enough for strap thickness plus easy threading)
- Position: near the top of the back face so the device pivots upward naturally for reading
- Slots pass through the back wall of the top shell only — they do not need to span the shell join

### 6.2 Secondary mount — carabiner bail

A printed loop on the **back face, near the top**, sized for a small carabiner. Positioned between or beside the velcro strap slots. Allows the device to hang from a pack loop, belt loop, or shoulder strap in the same display-outward orientation as the velcro mount.

**Bail design notes:**
- Inner diameter: determined by carabiner spine thickness — measure before modeling (see Section 12)
- Wall thickness of loop: 3–4mm for adequate strength
- Extends from the back face by enough to clear the carabiner body — approximately 8–10mm proud of the wall
- Modeled as part of the top shell back wall in Tinkercad — add as a solid loop shape

---

## 7. Openings and Access Points

| Feature | Location | Notes |
|---|---|---|
| E-ink display window | Front face of top shell, centered, landscape | Open aperture; display hot-glued or foam-taped from inside |
| LTR-390 sky aperture | Top face of bottom shell, BME280/LTR-390 corner | 8–10mm hole; no cover |
| Louvered vent insert | Long side wall of bottom shell, BME280/LTR-390 end | Separate printed insert, press-fit into rectangular cutout |
| USB-C charging port | Right short-end wall of top shell | USB-C slot (~9mm × 3.5mm); USB-C to Micro USB adapter plugs into TP4056 |
| ESP32 USB-C port | Front face of bottom shell | Emergency reflash only; slot opening |
| Slide switch | Left short-end wall of bottom shell | Small rectangular slot; no harness extension expected |
| Solar JST connector | Left short-end wall or long side wall of bottom shell | Round hole sized to JST connector body; wire exits freely; used for backpacking only |
| Velcro strap slots ×2 | Back face of top shell, near top, along 70mm width | ~22–26mm wide, 3–4mm tall; spaced apart for stability |
| Carabiner bail | Back face of top shell, near top | Printed loop; inner diameter determined by carabiner measurement |
| Shell join screws | Four corners | M3 screws through top shell into captured M3 hex nuts in bottom shell bosses |

---

## 8. USB-C to Micro USB Adapter

The TP4056 charging module has a fixed female Micro USB port. A USB-C to Micro USB adapter (female USB-C → male Micro USB) plugs into the TP4056 port and presents a female USB-C face at the enclosure wall slot. This allows charging with a standard USB-C cable.

**Implementation notes:**
- The adapter body sits inside the top shell cavity, held in place by the TP4056 module position and the wall slot
- The wall slot is sized for USB-C (~9mm wide × 3.5mm tall) not Micro USB
- Install the adapter onto the TP4056 before final assembly — it stays permanently in place
- Verify the adapter body fits within the top shell cavity depth before modeling the slot position

---

## 9. Solar JST Connector

The solar panel input uses a JST connector and wire that exit through a simple round hole in the enclosure wall. No slot, no cover — the connector body passes through the hole and the wire hangs free. The solar panel is only connected during backpacking trips; the hole can remain open during day hikes with no consequence.

**Implementation notes:**
- Hole diameter: sized to the JST connector body — measure before modeling (see Section 12)
- Location: left short-end wall of the bottom shell, or the long side wall away from the vent insert — determine which is cleaner based on where the JST wire exits the main perfboard
- The connector body should pass through snugly but not require force — a slightly loose fit is fine since this is an occasional-use connection

---

## 10. Materials and Filament

| Decision | Choice | Rationale |
|---|---|---|
| Test fit print | PLA | Fast, cheap, easy — first print only checks fit, not durability |
| Final print | ASA preferred; PETG fallback | Tucson outdoor use: ASA has superior UV and heat resistance; PETG is adequate if ASA is unavailable at Xerocraft |
| Color | White or light gray | Minimizes solar gain on enclosure body in Tucson heat |

**Xerocraft printer assignment:**
- Bambu A1 Mini — PLA test prints
- Centauri Carbon — ASA final prints (enclosed chamber required for ASA)
- Check with Xerocraft staff for current filament availability before scheduling

---

## 11. CAD Toolchain — Beginner Approach

This is Joseph's first enclosure design. The strategy prioritizes learning over perfection.

### 11.1 Recommended two-tool workflow

**Step 1 — OpenSCAD (parametric box generation)**
- Find a parametric project box template on Printables.com (search: "parametric electronics project box OpenSCAD")
- Good starting point: "Easy Customizable Parametric Electronics Project Box" by pbtec (or equivalent with internal standoff bosses and two-piece shell)
- Edit the config variables: internal length, width, height for each shell; wall thickness; boss diameter and height
- Render and export STL for each shell

**Step 2 — Tinkercad (cutouts and custom features)**
- Import the OpenSCAD-generated STL into Tinkercad (free, browser-based, no install)
- Use Tinkercad's "hole" shapes to punch the display window, LTR-390 aperture, USB-C charging slot, ESP32 USB-C slot, switch slot, velcro strap slots, vent insert cutout, and solar JST hole
- Add the carabiner bail as a solid loop shape on the back face
- Export final STLs for slicing

**Step 3 — Louvered vent insert (designed separately in Tinkercad)**
- Model the insert as a standalone part in Tinkercad
- Match the cutout dimensions exactly; add 0.1–0.2mm interference for press fit
- Model horizontal angled slats as thin rectangular solids rotated 45°, repeated with 2–3mm gaps

### 11.2 Slicing

- Xerocraft's Bambu A1 Mini uses Bambu Studio (free download)
- Centauri Carbon (for ASA) may use a different slicer — confirm with Xerocraft staff
- Standard settings for enclosure walls: 3–4 perimeters, 20–30% infill, 0.2mm layer height
- ASA-specific: enclosure required (Centauri Carbon), bed temp ~100°C, slightly slower print speed

### 11.3 Learning resources

- Tinkercad: tinkercad.com — free, browser-based, tutorial built in; start here
- OpenSCAD: openscad.org — free download; parametric templates are the fastest path for enclosures
- Printables.com — source for parametric templates; filter by "parametric" and "project box"
- Xerocraft staff — ask for a brief orientation to the Bambu A1 Mini before first print

---

## 12. Print Strategy — Two Sessions at Xerocraft

### Session 1 — PLA Test Fit
- Print both shells and the vent insert in PLA
- Do not glue or assemble permanently
- Check: does the main perfboard drop in cleanly? Do USB ports align with slots? Does the USB-C adapter fit within the top shell cavity and align with the wall slot? Does the display sit flush in its landscape aperture? Does the vent insert press in without force? Does the LTR-390 aperture land above the sensor? Does the switch slot align with the switch? Do the velcro strap slots accept your strap and space correctly along the 70mm width? Does the carabiner bail accept your carabiner? Does the solar JST connector pass through its hole cleanly?
- Note all misalignments and adjust CAD before Session 2
- Expect to iterate — one or two PLA reprints of just the problem shell is normal

### Session 2 — ASA Final Print
- Print final shells in ASA on the Centauri Carbon
- Print vent insert in ASA as well
- Assemble with M3 screws; confirm all sensors read correctly after assembly
- Set ESPHome display rotation to match physical display orientation
- Note any BME280 temperature offset introduced by enclosure (self-heating effect from ESP32) — apply software calibration offset in ESPHome YAML as per Build Standards

---

## 13. Assembly Notes

- Main perfboard sits in the bottom shell with the component side facing up and solder joints facing down (open at the base or resting on small printed ledges)
- TP4056 and LiPo sit in the top shell cavity; TP4056 foam-taped or velcroed in place with USB-C adapter aligned to the right short-end wall slot
- Install USB-C to Micro USB adapter onto TP4056 before placing module in shell
- Display mounted landscape in the front face aperture of the top shell; hot-glued or foam-taped from inside
- Ribbon cable exits the left short edge of the display module, routes toward the left wall, then down through the shell join gap to the main board header; trim to fit
- Solar JST connector and wire exit through the hole in the bottom shell wall; leave enough wire slack for easy connector access during backpacking trips
- Slide switch: header sits adjacent to the left board edge; slot in the left short-end wall should align directly — verify during PLA test fit
- M3 screws: four corners, screwing down through the top shell into captured M3 hex nuts pressed into the bottom shell bosses
- After final assembly: confirm display image rotation in ESPHome firmware and adjust if needed

---

## 14. Open Questions (Resolve Before CAD)

| Question | When to resolve |
|---|---|
| Carry method comfort after camping trip | Velcro + carabiner decided; confirm on first hike |
| Exact height of tallest component above main board | Measure before opening CAD |
| Exact TP4056 + LiPo stack height | Measure before opening CAD |
| USB-C to Micro USB adapter body dimensions | Measure adapter before modeling top shell cavity and wall slot |
| LTR-390 corner position measured from board edge | Measure before placing aperture in CAD |
| BME280 position measured from board edge | Measure before placing vent insert cutout in CAD |
| Velcro strap width — measure actual strap | Measure before modeling back face slots |
| Carabiner spine thickness — determines bail inner diameter | Measure chosen carabiner before modeling bail |
| Solar JST connector body diameter | Measure before modeling exit hole |
| Solar JST wire exit location on main perfboard | Check board layout to determine which wall the hole goes in |
| Slide switch header position — confirm against left board edge | Verify before modeling switch slot |
| Ribbon cable exit side on Waveshare 2.13" module — confirm left short edge | Confirm on hardware before modeling top shell interior |
| Xerocraft filament availability (ASA for Centauri Carbon) | Check before scheduling Session 2 |

---

## 15. What This Enclosure Does NOT Address (Deferred to v2)

- Weatherproofing / gaskets — not needed for day hiking in Sonoran Desert; rainfall events are brief and the device would be sheltered
- Charging cradle integration — the device charges via USB-C directly; a cradle dock is a future enhancement
- Optimized carry attachment — v1 gets velcro slots and carabiner bail; a more tailored mount can be designed for v2 once carry preference is confirmed on the trail

---

## 16. Success Criteria

The enclosure is complete when:

- [ ] Main perfboard seats correctly in bottom shell with no stress on solder joints
- [ ] Display is readable in direct sunlight through the landscape front aperture
- [ ] Display image rotation is correct when device is flipped up to read
- [ ] LTR-390 UV readings are consistent with pre-enclosure baseline
- [ ] BME280 temperature and humidity readings are within expected range (software offset applied if needed)
- [ ] USB-C charging port is accessible and charges the LiPo correctly
- [ ] ESP32 USB-C port is accessible for emergency reflash without disassembly
- [ ] Slide switch is operable without disassembly
- [ ] Solar JST connector exits cleanly and reaches the solar panel connector during backpacking use
- [ ] Louvered vent insert is seated flush and does not rattle
- [ ] Velcro strap slots accept the strap and hold the enclosure securely on the chest strap
- [ ] Carabiner bail accepts the chosen carabiner without flexing excessively
- [ ] Enclosure survives a full day hike without coming apart
- [ ] BME280 temperature offset (if any) is documented and applied in ESPHome YAML

---

## 17. Enclosure Diagram

Isometric exploded view produced during planning (Claude Chat, June 2026). Shows the two-shell stack separated to reveal internal layout. In the final assembled enclosure the shells mate flush at the join line with M3 screws through the four corner bosses.

**Files:**
- `hiking_monitor_enclosure_3d.svg` — editable/scalable source
- `hiking_monitor_enclosure_3d.png` — raster for quick reference

**Note:** Diagram predates the v1.3 plan decisions (two velcro slots along 70mm width, USB-C adapter, solar JST exit hole). These features are not yet shown and will be reflected in the next diagram update.

**Key features shown:**
- Top shell front face: e-ink display aperture, landscape orientation
- Top shell back face: two velcro strap slots near top; carabiner bail between slots
- Top shell right short-end wall: USB-C charging slot (via USB-C to Micro USB adapter on TP4056)
- Ribbon cable: exits left short edge of display, routes down toward left wall and into bottom shell
- Bottom shell top face: LTR-390 sky aperture (dark circle) at BME280/LTR-390 corner
- Bottom shell long side wall: louvered vent insert (teal), same corner as LTR-390
- Bottom shell left short-end wall: slide switch slot
- Bottom shell front face: ESP32 USB-C slot (emergency reflash)
- Louvered vent insert shown exploded as a separate printed part
- 70mm runs along the front face width; 50mm runs front-to-back (depth)