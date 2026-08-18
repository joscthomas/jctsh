# JCTsh 3D-Printed Enclosure — Instruction Set Template
**Author:** Joseph C Thomas (JCT)
**Purpose:** Reusable Claude Code instruction-set template for designing and printing a custom 3D-printed enclosure for any JCTsh component. Generalized from the hiking-monitor enclosure build (CARD-0009) — the first JCTsh component to go through this process end-to-end.
**Version:** 1.0
**Project:** JCTsh — reusable across components
**Related files:** `JCTsh-Component-Planning-Pattern.md`, `JCTsh-Build-Standards.md` (§1.1 Enclosure Convention, §1.5 3D-Printed Enclosure Build Pattern), `hiking-monitor-enclosure-instructions.md` and `hiking-monitor-enclosure-plan.md` (the worked example this template was generalized from)

---

## How to Use This Template

Copy this file to `components/<name>/<name>-enclosure-instructions.md` and fill in every `[bracketed placeholder]` with the specific component's hardware, dimensions, and features. Write a companion `<name>-enclosure-plan.md` first (design decisions, rationale, diagram) — this instructions doc is the execution layer on top of that plan, exactly as `hiking-monitor-enclosure-plan.md` relates to `hiking-monitor-enclosure-instructions.md`.

**Before starting:** confirm a printed enclosure is actually the right call. Per `JCTsh-Build-Standards.md` §1.1, open standoff mount is the default first option — escalate to a project box only for outdoor/weather-exposed installs, a finished-appearance requirement, or a documented dust problem. A *custom printed* enclosure (this template) is a further escalation beyond an off-the-shelf project box — justified when the component needs integrated apertures for sensors/displays, mounting features (straps, bails, clips) no off-the-shelf box provides, or a cavity shape that has to match a specific internal hardware stack. Don't reach for this template if an off-the-shelf box would do.

---

## Context for Claude Code

This instruction set builds a 3D printed enclosure for **[COMPONENT NAME]**. [One or two sentences describing the hardware stack — board, sensors, display, power system, form factor.]

**This build is different from firmware builds.** The implementation steps involve physical actions in external GUI tools (Tinkercad, OpenSCAD, the shop's slicer) and at a makerspace. Claude Code's role is to guide each step interactively — prompt the action, receive the result, advise on what to do next, and carry measurements forward into subsequent steps. Claude Code cannot operate these tools directly.

**Work through steps sequentially.** Many steps depend on measurements taken in earlier steps. Do not skip ahead.

**Planning document:** Read `<name>-enclosure-plan.md` before beginning. It contains all design decisions, rationale, and the enclosure diagram. This instruction set is the execution layer on top of that plan.

**File naming convention:** exports use a `-raw` / `-final` suffix: `-raw` = the initial OpenSCAD box export, before any Tinkercad cuts; `-final` = after the design is finalized in Tinkercad. All files live in `components/<name>/enclosure/`. Double-check this path matches the component's actual repo folder name, not its device/ESPHome name if the two differ — a stale path here is easy to introduce and easy to miss (this happened on the hiking-monitor build: `hiking-monitor` is the ESPHome device name, `hiking-monitor` is the repo folder, and early drafts of that instructions doc used the former in file paths).

---

## Pre-Work — Complete Independently Before Opening Claude Code

The following learning and setup tasks can be done independently, at your own pace, without Claude Code. Complete all of them before starting Step 0. None require the component's hardware to be in hand.

**Tools to install:**
- OpenSCAD — download from openscad.org
- Slicer for whichever printer the target makerspace currently has — **confirm the exact printer model and slicer software with makerspace staff before installing; printer lineups change.** Don't assume a previous build's printer is still there.

**Accounts to set up:**
- Tinkercad — free account at tinkercad.com (browser-based, no install)

**Tutorials to complete:**
- Tinkercad built-in tutorial — placing shapes, using hole shapes to punch cutouts, grouping objects
- OpenSCAD intro — how to open a `.scad` file, edit variables, and render/export STL
- Slicer intro — explore the interface, import any STL to see build plate and settings

**Template search — do this independently:**
- Search Printables.com: `parametric electronics project box OpenSCAD`
- Look for a two-piece shell design (separate top and bottom) with configurable internal dimensions, wall thickness, and corner screw bosses
- Download the `.scad` file and save it to `components/<name>/enclosure/`
- Open it in OpenSCAD, read the parameter section at the top, and render it (F6) to confirm it generates a box
- Note the variable names for: internal length, internal width, top shell height, bottom shell height, wall thickness, boss diameter

**Makerspace orientation:**
- Visit the makerspace and confirm which printer and slicer you'll be using for both the test print and the final print
- Confirm final-material filament availability (see Part 6) and whether the printer/enclosure can actually reach that material's required temps
- Confirm membership/day-pass status and whether a safety/printer orientation is required

**You are ready to open Claude Code when:**
- OpenSCAD, the target printer's slicer, and Tinkercad are all working on your machine
- You have completed the Tinkercad and OpenSCAD tutorials
- You have a parametric `.scad` template downloaded, opened in OpenSCAD, and rendering correctly
- You know the variable names in the template for the key parameters
- You have visited the makerspace and confirmed the printer and final-material filament availability
- The component's hardware is in hand for measurements

---

## Part 1 — Setup

### Step 0 — Read Build Standards

Read `JCTsh-Build-Standards.md` in full before proceeding, especially §1.1 (Enclosure Convention) and §1.5 (3D-Printed Enclosure Build Pattern). Note any existing enclosure patterns found.

**Report:** Confirm Build Standards read. Note any existing enclosure patterns found.

### Step 1 — Confirm pre-work complete

- [ ] OpenSCAD installed and launching correctly
- [ ] Target printer's slicer installed and launching correctly
- [ ] Tinkercad account working in browser
- [ ] Tinkercad tutorial completed
- [ ] OpenSCAD tutorial/intro completed
- [ ] Parametric `.scad` template downloaded to `components/<name>/enclosure/`
- [ ] Template renders correctly in OpenSCAD (F6 produces a two-piece box)
- [ ] Variable names noted for: internal length, width, top shell height, bottom shell height, wall thickness, boss diameter
- [ ] Makerspace orientation completed; printer and final-material filament availability confirmed
- [ ] Component hardware in hand for measurements

**Report:** Confirm all items checked. Provide the variable names from the template for the six key parameters listed above.

---

## Part 2 — Pre-CAD Measurements

All measurements in this part must be completed before modeling. Report each measurement to Claude Code; it will carry the values forward into the CAD steps. Have a ruler/calipers available. Disassemble any prototype stack enough to access the main board.

Adapt the specific steps below to the component's actual hardware. At minimum, cover:

### Step 2 — Measure bottom shell cavity height
Height from the board surface to the top of the tallest component above it.

**Report:** Height of tallest component (mm). Claude Code sets bottom shell internal cavity height to this + 2mm clearance.

### Step 3 — Measure any secondary cavity height
[E.g. a battery/charging-module compartment, if the design has one separate from the main board cavity.]

**Report:** Total assembly height (mm), and arrangement (side-by-side or stacked).

### Step 4 — Measure any connector/adapter that needs a wall slot
[E.g. USB-C to Micro-USB adapter, external antenna connector, etc. — repeat this step per connector.]

**Report:** Connector/adapter body dimensions and socket opening dimensions (mm).

### Step 5 — Confirm orientation/exit side of any directional component
[E.g. which edge a ribbon cable exits from, which face a display reads from.]

**Report:** Orientation/side.

### Step 6+ — Measure position of each sensor or feature needing an aperture, vent, or cutout
For each sensor/feature: distance from the nearest long edge and nearest short edge of the board to its center (mm), and which edges were used as reference.

**Report:** Distances and reference edges for each.

### Step N — Measure any mounting-feature hardware
[E.g. strap width for a strap slot, carabiner spine thickness for a bail, screw/standoff hole positions for a wall/panel mount.]

**Report:** Relevant dimensions (mm).

### Step N+1 — Compile and confirm measurement summary

Claude Code compiles all measurements into a summary table and the derived values (cavity heights, slot sizes, bail/hole diameters, aperture positions). Confirm all values are correct before proceeding. No CAD work begins until this table is confirmed.

---

## Part 3 — OpenSCAD Shell Generation

### Step — Set bottom shell dimensions

Using the variable names from Step 1 and the values from the measurement summary, set internal length/width/height and wall thickness (2.0mm is the standard starting wall thickness unless the design calls for otherwise). Render (F6). Confirm the shell is a rectangular box open at the top with corner bosses.

**Report:** Confirm render correct, provide exact internal height entered.

### Step — Set top shell dimensions

Same as above for the top/lid shell.

**Report:** Confirm render correct, provide exact internal height entered.

### Step — Export STL files from OpenSCAD

Export bottom and top shells as separate STL files: `bottom-shell-raw.stl`, `top-shell-raw.stl`. Save to `components/<name>/enclosure/`.

**Report:** Confirm both files exported and saved.

---

## Part 4 — Tinkercad Modeling

All cutouts, slots, apertures, and attachment features are added in Tinkercad. Work on the bottom shell first, then the top shell, then any press-fit insert parts separately.

For each sensor aperture, connector slot, mounting slot, or feature identified in Part 2's measurements: place the appropriate hole/cutout shape at the measured position (offset inward by the wall thickness to convert board-edge coordinates to shell-interior coordinates), group with the shell, and visually confirm placement before moving to the next feature.

### Step — Import bottom shell, add all bottom-shell features, export `bottom-shell-final.stl`

### Step — Import top shell, add all top-shell features (display aperture, connector slots, mounting features), export `top-shell-final.stl`

### Step — Model any press-fit insert parts (e.g. vent louvers) as standalone Tinkercad designs

**Interference fit for press-fit inserts:** size the insert 0.2mm tighter than its cutout on both width and height dimensions — this is the standard starting tolerance for a snug press fit without forcing.

**Report (each export step):** Confirm export successful, describe the result.

---

## Part 5 — Slicing and Session 1 Test Print (cheaper material)

### Step — Import STL files into the slicer

Import all exported `-final` STLs (and any insert parts). Select the confirmed printer and a cheap test material (PLA, unless the makerspace's printer lineup dictates otherwise).

### Step — Set print settings and orient parts

**Print orientation: shells print open-face down** — this is the standard orientation, placing the flat open face on the bed where it prints cleanly with no support needed. Apply standard test-print settings (layer height ~0.2mm, 3 walls, ~20% infill, no supports, brim recommended for bed adhesion).

**Report:** Confirm orientation looks correct, note estimated print time/filament.

### Step — Slice and export to print media

### Step — Makerspace Session 1: test print

Print all parts. Stay for the first few layers to confirm adhesion. Let parts cool before removing.

**Report:** Confirm all parts printed, note any defects (warping, layer separation, stringing).

### Step — Test fit: bottom shell

Check every aperture, slot, and cutout against the real hardware it's meant to accommodate. Does the board drop in cleanly? Does each aperture align with its sensor/connector? Does each insert press in snugly and sit flush?

**Report:** Pass/fail for each check. For any fail, describe the misalignment and approximate offset in mm.

### Step — Test fit: top shell

Same discipline for the top shell's features (display aperture, connector slot, mounting features, join-line flush fit with the bottom shell).

**Report:** Pass/fail for each check, with offsets for any fail.

### Step — Evaluate and iterate

Based on the test-fit reports, identify which features need adjustment and specify exact corrective changes in Tinkercad. Return to Tinkercad, apply corrections, re-export only the affected STL files, re-slice, and reprint only the shells that need correction.

**Capture exact new dimensions in the plan doc's design-record section (see below) as soon as they're decided in Tinkercad — not after the fact.** Live Tinkercad edits during a test-fit session are easy to make and easy to forget to record; if the plan doc has a section reserved for reproducing the design (dimensions, hole positions, feature specs), update it in the same session the edit is made. A plan doc that falls out of sync with the actual Tinkercad project is a real, observed risk on this kind of build, not a hypothetical one — the design can only be reproduced from the doc if the doc is current.

Repeat print → test-fit → iterate until all checks pass.

**Report:** Confirm all checks pass before proceeding to Part 6.

---

## Part 6 — Final Print and Assembly

### Step — Confirm final-material availability

Before scheduling the final print session, confirm with makerspace staff:
- The intended final material (ASA is the default choice for any outdoor/sun-exposed install; PETG is the standard fallback) is available for the target printer
- The printer is operational
- **If falling back to PETG, confirm the printer/bed can actually reach PETG's required bed temperature** — don't assume a PLA-only backup printer can substitute without checking it has a heated bed rated for the fallback material.

**Report:** Filament type and printer confirmed.

### Step — Re-slice for final material

Apply material-specific settings (higher wall count and infill than the test print, correct bed temp, reduced print speed, closed chamber if the material needs it, minimal cooling fan for warp-prone materials like ASA). Export to print media.

### Step — Makerspace Session 2: final print

Print all parts in the final material. Monitor the first layer. Let parts cool fully before removing — warp-prone materials (ASA) can deform if removed hot.

**Report:** Confirm all parts printed successfully, note any defects.

### Step — Install captured fasteners

If using hex-nut capture (the standard first-choice fastening method — preferred over heat-set threaded inserts for a first enclosure, since it needs no extra tooling beyond needle-nose pliers): press one nut into each corner boss pocket. If pockets are too tight (some materials shrink slightly on cooling), carefully enlarge with a hobby knife, removing material a little at a time.

**Report:** Confirm all fasteners seated.

### Step(s) — Assemble internal hardware

Mount each internal component (board, battery, charging module, display, etc.) into its shell per the plan doc's layout, routing cables/connectors through their designed exit points, leaving slack where components need to be reachable without full disassembly (e.g. a connector meant to be unplugged in the field).

**Report (per component):** Confirm seated/mounted/routed correctly.

### Step — Join shells

Align corner through-holes over corner bosses, drive fasteners, confirm flush join line with no gap.

**Report:** Confirm joined flush.

### Step(s) — Attach mounting features

Thread straps, attach to a mount point, or otherwise confirm the finished enclosure attaches the way the plan intends.

**Report:** Confirm mounting works as designed.

---

## Part 7 — Function Verification

### Step — Power on and verify any display/orientation-dependent output

If the enclosure changes a display's or sensor's physical orientation relative to its original bench setup, verify the readable/functional orientation is still correct once assembled — adjust firmware (e.g. a display `rotation:` parameter) and reflash if not.

**Report:** Confirm correct in the final mounted orientation.

### Step(s) — Verify each sensor's readings through its enclosure aperture

Compare against a reference where practical (e.g. a phone sensor app, a second known-good device). A small reduction from an enclosure wall/aperture is expected; a dramatic drop or dead reading is not.

**Report:** Enclosed reading vs. reference for each sensor, flag anything significantly off.

### Step — Full success criteria check

Verify every success criterion from the plan doc explicitly — board seats without solder-joint stress, display/sensors read correctly, all access ports (charging, reflash, switches) remain reachable without disassembly, press-fit inserts sit flush and don't rattle, mounting features hold securely, and any material-specific durability expectation (e.g. "survives a full day in the field") is met.

**Report:** All criteria checked, note any outstanding items.

---

## Part 8 — Documentation and Pattern Harvest

### Step — Update component README

Add an enclosure section documenting: enclosure design summary and footprint, the `-final`/insert STL file paths, the plan doc reference, any firmware adjustments made during verification (offsets, rotation values), and the date of final assembly.

**Report:** Confirm README updated.

### Step — Harvest patterns to Build Standards

Review this build for anything not already captured in `JCTsh-Build-Standards.md` §1.5 (3D-Printed Enclosure Build Pattern) or elsewhere — a new fastening approach, a new material choice and why, a new insert/tolerance pattern, a mounting-feature technique, or anything about this specific build that generalizes beyond it. **Do this step for real — it's easy to consider the build "done" once the hardware works and skip the harvest, but the harvest is what makes the next enclosure build faster than this one.** State each candidate explicitly (what it is, where it appeared, proposed addition) and get sign-off before writing changes to Build Standards.

**Report:** Confirm Build Standards updated, or confirm explicitly that nothing new applies.

---

*Build complete.*
