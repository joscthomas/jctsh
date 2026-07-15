# Hiking Monitor — 3D Printed Enclosure Build Instructions
**Author:** Joseph C Thomas (JCT)
**Purpose:** Step-by-step Claude Code instruction set for designing and printing the hiking monitor enclosure.
**Project:** JCTsh — hiking-monitor
**Version:** 1.2
**Version description:** Corrected stale Bambu A1 Mini references throughout (Pre-Work, Step 1 checklist, Steps 30/32/33/37) to the Elegoo Centauri Carbon, matching the printer-lineup correction already recorded in `hiking-monitor-enclosure-plan.md` — the A1 Mini is no longer at Xerocraft. Exact slicer software name for the Centauri Carbon is still unconfirmed; flagged inline to check with Xerocraft staff.
**Status:** Ready for execution
**Related files:** hiking-monitor-enclosure-plan.md, enclosure-prototype.md, JCTsh-Build-Standards.md

---

## Context for Claude Code

This instruction set builds a 3D printed enclosure for the JCTsh hiking monitor. The hiking monitor is a wearable field sensor on an ESP32 DevKitC-32 perfboard (50mm × 70mm) with BME280, LTR-390 UV sensor, Waveshare 2.13" e-ink display, TP4056 charging module, and EEMB 1100mAh LiPo. A field prototype using perfboard sandwiches validated the design; this build translates it into a permanent printed enclosure.

**This build is different from firmware builds.** The implementation steps involve physical actions in external GUI tools (Tinkercad, OpenSCAD, the Centauri Carbon's slicer) and at Xerocraft makerspace. Claude Code's role is to guide each step interactively — prompt the action, receive the result, advise on what to do next, and carry measurements forward into subsequent steps. Claude Code cannot operate these tools directly.

**Work through steps sequentially.** Many steps depend on measurements taken in earlier steps. Do not skip ahead.

**Planning document:** Read `hiking-monitor-enclosure-plan.md` before beginning. It contains all design decisions, rationale, and the enclosure diagram. This instruction set is the execution layer on top of that plan.

**File naming convention:** exports use a `-raw` / `-final` suffix: `-raw` = the initial OpenSCAD box export, before any Tinkercad cuts (Step 15); `-final` = after the design is finalized in Tinkercad (Steps 22/28/29). All files live in `components/hiking-sensor/enclosure/` — note this is `hiking-sensor`, not `hiking-monitor` (the latter is only the ESPHome device name, not the repo folder). Corrected 2026-07-13 — steps below originally used older working names (`bottom-shell.stl`, `bottom-shell-cuts.stl`, etc.) and the wrong `hiking-monitor` path; both are now fixed throughout.

---

## Pre-Work — Complete Independently Before Opening Claude Code

The following learning and setup tasks can be done independently, at your own pace, without Claude Code. Complete all of them before starting Step 0. None require the hiking monitor hardware to be in hand.

**Tools to install on your Windows machine:**
- OpenSCAD — download from openscad.org
- Slicer for the Centauri Carbon (Elegoo's own slicer, not Bambu Studio — the A1 Mini this instruction set originally assumed is no longer at Xerocraft) — confirm the exact software with Xerocraft staff before installing; a shop computer may already have it set up

**Accounts to set up:**
- Tinkercad — free account at tinkercad.com (browser-based, no install)

**Tutorials to complete:**
- Tinkercad built-in tutorial — takes about 30 minutes; start a new design and follow the in-app tutorial prompts; focus on placing shapes, using hole shapes to punch cutouts, and grouping objects
- OpenSCAD intro — watch a beginner YouTube video (search: "OpenSCAD tutorial beginner enclosure") or read the OpenSCAD cheat sheet at openscad.org/cheatsheet; focus on how to open a `.scad` file, edit variables, and render/export STL
- Slicer intro — open the app and explore the interface; import any STL file to see how the build plate and slicer settings work

**Template search — do this independently:**
- Go to Printables.com and search: `parametric electronics project box OpenSCAD`
- Browse results looking for a two-piece shell design (separate top and bottom) with configurable internal dimensions, wall thickness, and corner screw bosses
- A well-regarded option is the "Easy Customizable Parametric Electronics Project Box" by pbtec — look for it or an equivalent
- Download the `.scad` file and save it to `components/hiking-sensor/enclosure/` in the repo
- Open it in OpenSCAD, read the parameter section at the top, and render it (press F6) to confirm it generates a box
- Note the variable names for: internal length, internal width, top shell height, bottom shell height, wall thickness, boss diameter

**Xerocraft orientation:**
- Visit Xerocraft (101 W 6th St #111, Tucson) and ask for a brief orientation to the **Elegoo Centauri Carbon** — the printer used for both the PLA test print (Session 1) and the ASA final print (Session 2); the Bambu A1 Mini this doc originally referenced has been retired
- Confirm ASA filament availability for the Centauri Carbon, and confirm which slicer software is used (ask whether a shop computer already has it set up, or whether to bring a laptop with it pre-installed)
- Confirm membership/day-pass status and whether a safety/printer orientation is required — worth checking given the printer lineup changed recently

**You are ready to open Claude Code when:**
- OpenSCAD, the Centauri Carbon's slicer, and Tinkercad are all working on your machine
- You have completed the Tinkercad and OpenSCAD tutorials
- You have a parametric `.scad` template downloaded, opened in OpenSCAD, and rendering correctly
- You know the variable names in the template for the key parameters
- You have visited Xerocraft and confirmed the Centauri Carbon and ASA availability
- The hiking monitor hardware is in hand for measurements (main perfboard, display, TP4056, LiPo, USB-C adapter, solar JST connector, carabiner, velcro strap)

---

## Part 1 — Setup

---

### Step 0 — Read Build Standards

Read `JCTsh-Build-Standards.md` in full before proceeding. Note any enclosure or fabrication conventions already established. This step is mandatory at the start of every JCTsh build session.

**Report:** Confirm Build Standards read. Note any existing enclosure patterns found.

---

### Step 1 — Confirm pre-work complete

Confirm the following before proceeding:

- [ ] OpenSCAD installed and launching correctly
- [ ] Centauri Carbon slicer installed and launching correctly
- [ ] Tinkercad account working in browser
- [ ] Tinkercad tutorial completed
- [ ] OpenSCAD tutorial/intro completed
- [ ] Parametric `.scad` template downloaded to `components/hiking-sensor/enclosure/`
- [ ] Template renders correctly in OpenSCAD (F6 produces a two-piece box)
- [ ] Variable names noted for: internal length, width, top shell height, bottom shell height, wall thickness, boss diameter
- [ ] Xerocraft orientation completed; Centauri Carbon and ASA availability confirmed
- [ ] Hiking monitor hardware in hand for measurements

**Report:** Confirm all items checked. Provide the variable names from the template for the six key parameters listed above.

---

## Part 2 — Pre-CAD Measurements

All measurements in this part must be completed before modeling. Report each measurement to Claude Code; it will carry the values forward into the CAD steps. Have a ruler available. Disassemble the field prototype stack enough to access the main perfboard.

---

### Step 2 — Measure bottom shell cavity height

With the main perfboard lying component-side up on a flat surface, measure the height from the board surface to the top of the tallest component above it. Candidates are the ESP32 DevKitC-32 in its female headers, the display header pins, and any capacitors or resistors that stand proud.

**Report:** Height of tallest component above main board surface (mm).

Claude Code will set the bottom shell internal cavity height to this value + 2mm clearance.

---

### Step 3 — Measure top shell cavity height

Place the TP4056 module and EEMB LiPo pouch as they would sit together in the top shell cavity — side by side or stacked, whichever fits. Measure the total height of the assembly from the surface to the highest point.

**Report:** Total TP4056 + LiPo assembly height (mm), and whether they sit side-by-side or one on top of the other.

Claude Code will set the top shell internal cavity height to this value + 2mm clearance.

---

### Step 4 — Measure USB-C to Micro USB adapter

With the USB-C to Micro USB adapter in hand, measure:
- Adapter body length (Micro USB plug face to USB-C socket face)
- Adapter body width at its widest point
- USB-C socket opening: width × height

**Report:** All three measurements (mm).

The adapter body length determines how far inboard the TP4056 must sit from the right short-end wall. The USB-C socket dimensions set the wall slot size (+ 0.5mm tolerance each dimension).

---

### Step 5 — Confirm ribbon cable exit side on display module

Hold the Waveshare 2.13" e-ink display module in landscape orientation (long axis horizontal, display face toward you). Identify which short edge the ribbon cable exits from.

**Report:** Left or right short edge.

The plan assumes left. If right, the top shell interior layout will be mirrored accordingly.

---

### Step 6 — Measure LTR-390 position on main perfboard

With the main perfboard component-side up, identify the Adafruit LTR-390 breakout board. Measure:
- Distance from the nearest long edge of the perfboard to the center of the LTR-390 breakout (mm)
- Distance from the nearest short edge of the perfboard to the center of the LTR-390 breakout (mm)

**Report:** Both distances (mm), and which long edge and which short edge you measured from.

These numbers place the LTR-390 sky aperture in the top face of the bottom shell.

---

### Step 7 — Measure BME280 position on main perfboard

With the main perfboard component-side up, identify the BME280 module. Measure:
- Distance from the nearest long edge of the perfboard to the center of the BME280 (mm)
- Distance from the nearest short edge of the perfboard to the center of the BME280 (mm)

**Report:** Both distances (mm), and which long edge and which short edge you measured from.

These numbers place the louvered vent insert cutout on the long side wall of the bottom shell.

---

### Step 8 — Confirm slide switch position

Locate the slide switch 2-pin header on the main perfboard. Measure:
- Distance from the left short edge of the board to the center of the switch header (mm)
- Height of the switch body above the board surface (mm)

**Report:** Both measurements (mm).

---

### Step 9 — Measure solar JST connector

With the solar JST connector in hand, measure the connector body diameter (or width × height if rectangular).

Also identify which wall the JST wire exits nearest on the main perfboard — the left short-end wall or the long side wall away from the BME280/LTR-390 corner.

**Report:** JST connector body dimensions (mm) and which wall it exits nearest.

---

### Step 10 — Measure velcro strap width

Measure the width of the velcro strap you plan to use for chest strap mounting.

**Report:** Strap width (mm).

Velcro slot width = strap width + 1mm. Slot height = 4mm.

---

### Step 11 — Measure carabiner spine thickness

With your chosen carabiner, measure the thickest part of the spine (the straight back bar opposite the gate).

**Report:** Spine thickness (mm).

Carabiner bail inner diameter = spine thickness + 3mm minimum clearance.

---

### Step 12 — Compile and confirm measurement summary

Claude Code will compile all measurements from Steps 2–11 into a summary table and the derived values (cavity heights, slot sizes, bail diameter, aperture position). Confirm all values are correct before proceeding. No CAD work begins until this table is confirmed.

---

## Part 3 — OpenSCAD Shell Generation

---

### Step 13 — Set bottom shell dimensions in OpenSCAD

Open the parametric `.scad` template. Using the variable names confirmed in Step 1 and the values from Step 12, set the bottom shell parameters:

- Internal length: 70mm
- Internal width: 50mm
- Internal height: [Step 2 value + 2mm]
- Wall thickness: 2.0mm

Render (F6). Confirm the shell looks correct — a rectangular box open at the top with corner bosses.

**Report:** Confirm render looks correct and provide the exact internal height value entered.

---

### Step 14 — Set top shell dimensions in OpenSCAD

Set the top shell parameters:

- Internal length: 70mm
- Internal width: 50mm
- Internal height: [Step 3 value + 2mm]
- Wall thickness: 2.0mm

Render (F6) and confirm.

**Report:** Confirm render correct and provide the exact internal height value entered.

---

### Step 15 — Export STL files from OpenSCAD

Export the bottom shell and top shell as separate STL files. Use File → Export → Export as STL:
- `bottom-shell-raw.stl`
- `top-shell-raw.stl`

Save both to `components/hiking-sensor/enclosure/` in the repo.

**Report:** Confirm both files exported and saved.

---

## Part 4 — Tinkercad Modeling

All cutouts, slots, apertures, and attachment features are added in Tinkercad. Work on the bottom shell first, then the top shell, then the vent insert as a separate part.

---

### Step 16 — Import bottom shell into Tinkercad

Go to tinkercad.com, create a new design, and import `bottom-shell-raw.stl`. Position it so the open face (top) faces up in the viewport.

**Report:** Confirm import looks correct — a rectangular box with corner bosses, open top.

---

### Step 17 — Add LTR-390 sky aperture

Place a cylindrical hole shape on the top face of the bottom shell, centered above the LTR-390 position from Step 6.

- Diameter: 10mm
- Depth: 5mm (punches through the 2mm wall with clearance)
- Position: [Step 6 measurements from board edges, offset inward by 2mm wall thickness to convert from board-edge to shell-interior coordinates]

Group the hole with the shell. Visually confirm the hole lands in the correct corner of the top face.

**Report:** Confirm aperture punched and positioned correctly.

---

### Step 18 — Add louvered vent insert cutout

Place a rectangular hole on the long side wall of the bottom shell nearest the BME280/LTR-390 corner, using the BME280 position from Step 7:

- Cutout width: 24mm
- Cutout height: 15mm
- Depth: 5mm (through the wall)
- Position: centered on the BME280 location along the wall length; vertically centered on the wall height

Group and punch. Confirm cutout is on the correct long side wall.

**Report:** Confirm cutout punched and positioned correctly.

---

### Step 19 — Add slide switch slot

Place a rectangular hole on the left short-end wall using the measurements from Step 8:

- Slot width: 12mm
- Slot height: [Step 8 switch height + 2mm clearance]
- Position: [Step 8 distance from left board edge, offset inward by 2mm wall]; vertically centered on the wall height

Group and punch.

**Report:** Confirm slot punched on the correct wall.

---

### Step 20 — Add ESP32 USB-C reflash slot

Place a rectangular hole on the front face of the bottom shell for the ESP32 USB-C port:

- Slot width: 10mm
- Slot height: 5mm
- Position: aligned with the ESP32 USB-C port; measure its distance from the board edge if needed

Group and punch.

**Report:** Confirm slot punched.

---

### Step 21 — Add solar JST exit hole

Using the measurements from Step 9 and the identified wall, place a circular hole on the appropriate wall:

- Diameter: [Step 9 JST body diameter + 0.5mm clearance]
- Position: near the bottom of the wall where the JST wire exits the board naturally

Group and punch.

**Report:** Confirm hole punched on the correct wall.

---

### Step 22 — Export bottom shell from Tinkercad

Export the completed bottom shell as `bottom-shell-final.stl` to `components/hiking-sensor/enclosure/`.

**Report:** Confirm export successful.

---

### Step 23 — Import top shell into Tinkercad

Create a new Tinkercad design and import `top-shell-raw.stl`. Position open face upward.

**Report:** Confirm import looks correct.

---

### Step 24 — Add landscape display aperture on front face

The Waveshare 2.13" display PCB is approximately 59.2mm × 29.2mm. The aperture is slightly smaller so the display rests on a ledge and can be glued from inside.

Place a rectangular hole on the front face of the top shell:

- Width: 56mm
- Height: 26mm
- Position: centered left-right and vertically on the front face

Group and punch.

**Report:** Confirm aperture punched and centered.

---

### Step 25 — Add USB-C charging slot on right short-end wall

Using the measurements from Step 4:

- Slot width: [Step 4 USB-C socket width + 0.5mm]
- Slot height: [Step 4 USB-C socket height + 0.5mm]
- Position: horizontally centered on the right short-end wall; vertically positioned to align with the TP4056 + adapter inside the cavity — use the adapter body length from Step 4 to estimate the vertical center of the USB-C face

Group and punch.

**Report:** Confirm slot punched on the correct wall.

---

### Step 26 — Add velcro strap slots on back face

The back face is opposite the display face. Place two rectangular holes near the top edge of the back face, spaced along the 70mm width:

- Slot width: [Step 10 strap width + 1mm]
- Slot height: 4mm
- Slot 1: centered at ~18mm from the left edge of the back face, 5mm down from the top edge
- Slot 2: centered at ~18mm from the right edge of the back face, 5mm down from the top edge

Group and punch both slots.

**Report:** Confirm both slots punched and symmetrically spaced.

---

### Step 27 — Add carabiner bail on back face

Construct a loop (bail) on the back face of the top shell between the two velcro strap slots:

- Build from two cylinders: a large cylinder (outer) with a smaller cylinder (hole) punched through it to create a loop
- Outer cylinder diameter: [Step 11 spine thickness + 3mm + 8mm] (inner clearance + 4mm wall thickness each side)
- Inner cylinder diameter (the hole): [Step 11 spine thickness + 3mm]
- Loop depth (how far it protrudes from the back wall): 10mm
- Position: centered between the two velcro slots, base flush with the back face

Group the outer cylinder and inner hole cylinder together as a solid loop. Then group with the top shell so the bail base merges into the back wall.

**Report:** Confirm bail added and looks like a loop a carabiner can pass through.

---

### Step 28 — Export top shell from Tinkercad

Export the completed top shell as `top-shell-final.stl` to `components/hiking-sensor/enclosure/`.

**Report:** Confirm export successful.

---

### Step 29 — Model louvered vent insert in Tinkercad

Create a new Tinkercad design for the vent insert as a standalone part:

- Overall dimensions: 24.2mm wide × 15.2mm tall × 2.5mm deep (0.2mm interference fit on width and height for press fit)
- Slats: three rectangular boxes, each 24.2mm wide × 2mm tall × 2.5mm deep, rotated 45° around their long axis (tilted downward toward the outside face), spaced evenly across the 15.2mm height
- The slat angle blocks direct overhead sun and rain while allowing horizontal airflow

Export as `vent-insert-final.stl` to `components/hiking-sensor/enclosure/`.

**Report:** Confirm insert modeled and exported. Describe what it looks like.

---

## Part 5 — Slicing and Session 1 PLA Test Print

---

### Step 30 — Import STL files into the Centauri Carbon slicer

Open the slicer (confirm exact software with Xerocraft staff — likely Elegoo's own slicer, not Bambu Studio, since the printer changed from the A1 Mini to the Centauri Carbon). Import all three STL files:
- `bottom-shell-final.stl`
- `top-shell-final.stl`
- `vent-insert-final.stl`

Select the Elegoo Centauri Carbon as the printer. Select PLA as the filament.

**Report:** Confirm all three models imported and visible on the build plate.

---

### Step 31 — Set PLA print settings and orient parts

Orient each shell **open-face down** on the build plate — this is the correct print orientation, placing the flat open face on the bed where it prints cleanly with no support needed.

Apply settings:
- Layer height: 0.2mm
- Walls/perimeters: 3
- Infill: 20%
- Supports: none
- Bed adhesion: brim recommended

**Report:** Confirm orientation looks correct in the slicer preview. Note estimated print time and filament usage.

---

### Step 32 — Slice and export to print media

Slice the print and export the file to the SD card or USB drive for the Centauri Carbon.

**Report:** Confirm export successful. Note the filename.

---

### Step 33 — Xerocraft Session 1: PLA test print

At Xerocraft, load PLA into the Centauri Carbon and print all three parts. Stay for the first few layers to confirm adhesion. When complete, let parts cool before removing.

**Report:** Confirm all three parts printed. Note any visible defects (warping, layer separation, stringing).

---

### Step 34 — Test fit: bottom shell

Check the following with the main perfboard and components:

1. Does the perfboard drop into the cavity cleanly without force?
2. Does the LTR-390 aperture hole land above the LTR-390 sensor?
3. Does the vent insert cutout align with the BME280 location?
4. Does the slide switch slot align with the switch header?
5. Does the ESP32 USB-C slot align with the ESP32 USB-C port?
6. Does the solar JST hole align with the connector and wire?
7. Does the vent insert press in snugly and sit flush?

**Report:** Pass/fail for each check. For any fail, describe the misalignment and approximate offset in mm.

---

### Step 35 — Test fit: top shell

Check the following with the display, TP4056, USB-C adapter, and LiPo:

1. Does the display module sit in the front face aperture with a ~1.5mm ledge on all sides?
2. Does the TP4056 + adapter sit inside the cavity with the USB-C face aligned to the right wall slot?
3. Do the velcro strap slots accept the strap cleanly?
4. Does the carabiner bail accept the carabiner without forcing?
5. Does the top shell sit flush on the bottom shell at the join line?

**Report:** Pass/fail for each check. For any fail, describe the misalignment and approximate offset in mm.

---

### Step 36 — Evaluate and iterate

Based on Step 34 and 35 reports, Claude Code will identify which features need adjustment and specify the exact corrective changes to make in Tinkercad. Return to Tinkercad, apply corrections, re-export affected STL files, re-slice, and reprint only the shells that need correction.

Repeat Steps 33–36 until all checks pass.

**Report:** Confirm all checks pass before proceeding to Part 6.

---

## Part 6 — Final ASA Print and Assembly

---

### Step 37 — Confirm ASA availability at Xerocraft

Before scheduling Session 2, confirm with Xerocraft:
- ASA filament is available for the Centauri Carbon enclosed printer
- The Centauri Carbon is operational

If ASA is unavailable, PETG on the Centauri Carbon is the acceptable fallback (the A1 Mini this fallback originally assumed is no longer at Xerocraft — confirm one of the PLA-only backup printers, e.g. Neptune 3 Pro/4 Plus or Sidewinder X1, isn't accidentally substituted for PETG without checking it actually has a heated bed capable of PETG temps).

**Report:** Filament type and printer confirmed for final print.

---

### Step 38 — Re-slice for ASA

Apply ASA-specific slicer settings (or PETG if fallback):

- Layer height: 0.2mm
- Walls/perimeters: 4
- Infill: 25%
- Bed temperature: ~100°C (ASA) or ~70°C (PETG)
- Print speed: reduce ~20% from defaults
- Enclosure chamber: closed (required for ASA)
- Cooling fan: off or minimal (ASA warps with rapid cooling)

Export to print media for the Centauri Carbon.

**Report:** Confirm settings applied and file exported.

---

### Step 39 — Xerocraft Session 2: ASA final print

Print all three parts in ASA on the Centauri Carbon. Monitor the first layer. Let parts cool fully before removing — ASA warps if removed hot.

**Report:** Confirm all three parts printed successfully in ASA. Note any defects.

---

### Step 40 — Press M3 hex nuts into bottom shell bosses

Press one M3 hex nut into each of the four corner boss pockets in the bottom shell using needle-nose pliers. Each nut should seat flush or just below the top of the boss. If pockets are too tight (ASA shrinks slightly on cooling), carefully enlarge with a hobby knife — remove material a little at a time.

**Report:** Confirm all four nuts seated.

---

### Step 41 — Install USB-C to Micro USB adapter on TP4056

Plug the adapter onto the TP4056 Micro USB port. Confirm it seats fully.

**Report:** Confirm adapter installed.

---

### Step 42 — Mount TP4056 + adapter in top shell

Position the TP4056 (with adapter) in the top shell cavity with the USB-C face aligned to the right short-end wall slot. Secure with foam tape or velcro on the underside. Test by inserting a USB-C cable through the slot.

**Report:** Confirm TP4056 secured and USB-C cable inserts successfully.

---

### Step 43 — Place LiPo in top shell cavity

Position the LiPo alongside the TP4056. Secure with foam tape if needed. Confirm the JST connector reaches the TP4056 BAT terminals.

**Report:** Confirm LiPo seated and connected.

---

### Step 44 — Mount display in top shell front face aperture

Position the display module (landscape) behind the front face aperture from inside the top shell. The PCB rests on the ~1.5mm ledge. Apply hot glue or double-sided foam tape to the back of the PCB and press into position. Confirm the display face is flush with or just proud of the front wall.

**Report:** Confirm display mounted and seated.

---

### Step 45 — Route ribbon cable

Route the ribbon cable from the left short edge of the display, along the left interior wall of the top shell, and down through the shell join gap. Trim to fit — leave enough slack for reassembly. Connect to the main board header.

**Report:** Confirm ribbon cable routed and connected without stress on the connector.

---

### Step 46 — Mount main perfboard in bottom shell

Place the main perfboard into the bottom shell cavity, component-side up, solder joints facing down. Confirm the board sits flat with no rocking.

**Report:** Confirm board seated correctly.

---

### Step 47 — Route solar JST connector

Feed the solar JST connector and wire through the exit hole in the bottom shell wall. Leave enough wire slack inside the shell for easy plug/unplug without opening the enclosure.

**Report:** Confirm connector exits cleanly.

---

### Step 48 — Press vent insert into bottom shell

Press the louvered vent insert into the rectangular cutout in the long side wall. It should press in snugly with finger pressure and sit flush with the outer wall. If too tight, lightly sand the insert edges. If too loose, secure with a small dab of hot glue on the back face.

**Report:** Confirm insert seated flush and does not rattle.

---

### Step 49 — Join shells with M3 screws

Place the top shell onto the bottom shell, aligning the four corner through-holes over the four corner bosses. Drive one M3 screw through each corner into the captured hex nut. Tighten snug — do not overtighten.

**Report:** Confirm all four screws installed and shells joined flush with no gap at the join line.

---

### Step 50 — Thread velcro strap

Thread the velcro strap through both back face slots. Wrap around the Osprey chest strap webbing perpendicularly and fasten. Confirm the enclosure sits flat against the chest strap with the display facing outward.

**Report:** Confirm strap threaded and enclosure mounts securely.

---

## Part 7 — Firmware Verification and Calibration

---

### Step 51 — Power on and verify display rotation

Power on the hiking monitor. If the text reads upside down or sideways, adjust the ESPHome `rotation:` parameter:

```yaml
display:
  - platform: waveshare_epaper
    rotation: 180    # adjust: 0, 90, 180, or 270
```

Flash the corrected firmware and confirm the display reads correctly when the device is flipped up from the chest strap.

**Report:** Rotation value confirmed and display readable in use position.

---

### Step 52 — Verify LTR-390 UV readings

With the enclosure assembled and LTR-390 aperture open to the sky, check UV index readings against a reference (phone UV app or UV meter). Readings should be within reasonable range of the reference — a small reduction is expected but not a dramatic drop.

**Report:** UV index reading with enclosure vs. reference. Flag if readings are significantly lower than expected.

---

### Step 53 — Verify BME280 readings and apply offset if needed

Allow the enclosure to stabilize for 15 minutes powered on. Compare BME280 temperature against a reference thermometer. The ESP32 self-heating effect may cause readings 2–5°F high.

If offset needed, apply in ESPHome YAML:

```yaml
- platform: bme280_i2c
  temperature:
    name: "Hiking Monitor Temperature"
    filters:
      - offset: -X.X    # negative value corrects high reading; determine by measurement
```

Flash and confirm corrected reading matches reference within 2°F.

**Report:** Raw BME280 reading, reference reading, offset value applied (if any), corrected reading.

---

### Step 54 — Full success criteria check

Verify all success criteria from the planning document:

- [ ] Main perfboard seats correctly in bottom shell with no stress on solder joints
- [ ] Display is readable in direct sunlight through the landscape front aperture
- [ ] Display image rotation is correct when device is flipped up to read
- [ ] LTR-390 UV readings are consistent with pre-enclosure baseline
- [ ] BME280 temperature and humidity readings are within expected range (offset applied if needed)
- [ ] USB-C charging port is accessible and charges the LiPo correctly
- [ ] ESP32 USB-C port is accessible for emergency reflash without disassembly
- [ ] Slide switch is operable without disassembly
- [ ] Solar JST connector exits cleanly and reaches the solar panel connector
- [ ] Louvered vent insert is seated flush and does not rattle
- [ ] Velcro strap slots accept the strap and hold the enclosure securely on the chest strap
- [ ] Carabiner bail accepts the chosen carabiner without flexing excessively
- [ ] Enclosure survives a full day hike without coming apart
- [ ] BME280 temperature offset (if any) is documented and applied in ESPHome YAML

**Report:** All criteria checked. Note any outstanding items.

---

### Step 55 — Update component README

Add an enclosure section to `components/hiking-sensor/README.md` documenting:

- Enclosure design: two-shell ASA printed stack, 70mm × 50mm footprint
- Files: `enclosure/bottom-shell-final.stl`, `enclosure/top-shell-final.stl`, `enclosure/vent-insert-final.stl`
- Diagram: `hiking_monitor_enclosure_3d.svg` and `.png`
- Planning document: `hiking-monitor-enclosure-plan.md`
- BME280 temperature offset applied (value from Step 53, or "none required")
- Display rotation setting applied (value from Step 51)
- Date of final assembly

**Report:** Confirm README updated.

---

### Step 56 — Harvest patterns to Build Standards

Review this build for new patterns to add to `JCTsh-Build-Standards.md`. Candidates include:

- FDM print orientation: shells print open-face down, no supports needed
- Hex nut capture vs. threaded inserts (hex nut capture preferred for first enclosure)
- ASA for Tucson outdoor use; PETG as fallback
- Tinkercad + OpenSCAD two-tool workflow for enclosure design
- Interference fit for press-fit inserts: 0.2mm tighter than cutout on width and height
- Velcro slot sizing: strap width + 1mm wide, 4mm tall
- USB-C slot sizing: socket width + 0.5mm, socket height + 0.5mm
- Louvered vent insert: separate printed part, 45° slat angle, 5mm slat spacing
- Carabiner bail inner diameter: spine thickness + 3mm minimum

Update `JCTsh-Build-Standards.md` with any patterns not already captured.

**Report:** Confirm Build Standards updated, or confirm no new patterns to add.

---

*Build complete.*
