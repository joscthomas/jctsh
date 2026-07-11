# JCT Smart Home (JCTsh) Component Planning Pattern
**Author:** Joseph C Thomas (JCT)
**Purpose:** Defines the five-phase process for planning and building JCTsh smart home components, from discovery through execution.
**Version:** 2.4
**Version description:** Realigned with `JCTsh-Operating-System.md`: Phases 1–5 now all happen in Claude Code, not Claude chat. Chat is limited to informal, pre-card preliminary thinking and research that produces no planning documents — once there's a decision to build something, the transition is to Claude Code, where a card is created (Backlog) and Phases 1–5 proceed from there in one continuous tool.

---

## Core Principle

Preliminary thinking happens in Claude chat, informally — feasibility questions, initial ideas, whether to build something at all. This stage produces no planning documents. Once that thinking is done and there's a decision to build, move to Claude Code: create a card (per `JCTsh-Operating-System.md`) and work Phases 1–5 there, start to finish. Chat doesn't re-enter the process once the card exists — research, planning, design, and execution all happen in the same continuous Claude Code session (or a resumed one), not split across tools.

---

## Context Files — Phased Loading

Files are loaded when they become necessary, not all at once before anything begins. Loading files before they are needed adds friction without adding value. The tables below define what is needed at each phase and why.

### Phase 1 — Load before beginning Phase 1

Phase 1 is about feasibility and approach. Only two files are needed: the planning pattern itself (this document) and the environmental architecture doc. The environmental architecture doc is required early because it defines the payload schema and data pipeline that all environmental sensor components must conform to — these constraints shape the feasibility discussion from the start.

| File | Location | Purpose |
|---|---|---|
| `JCTsh-Component-Planning-Pattern.md` | repo root | This document — the planning process itself |
| `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md` | core/data-pipeline/ | Standard environmental sensor payload schema, Google Sheets archive design, Node-RED wildcard handler pattern, Weather Underground integration, and the planned environmental sensor family. Shapes feasibility and approach from the start — all environmental sensor components must conform to decisions already made here. |

**For any property sensor build** (fixed, mobile, battery, solar, or USB-powered environmental sensor deployed on or around the property), also load:

| File | Location | Purpose |
|---|---|---|
| `JCTsh-Property-Sensor-Pattern.md` | repo root | Invariant standard, variable dimension decision table (location type, power source, connectivity, offline handling, sensor complement, custom automation), and new-sensor checklist. Work through the checklist in Phase 1 — it produces the concrete values needed to start Phase 2 hardware selection. |

If a prior component's Phase 1 planning document exists and is relevant (e.g., hiking monitor as reference for van sensor suite), load it as well. It carries architectural decisions and context that would otherwise have to be reconstructed.

Claude Code may begin Phase 1 discussion as soon as these files are read.

### Phase 2 — Load before beginning Phase 2 hardware discussion

Phase 2 is about hardware selection and integration design. These files are needed before any purchasing decisions are made or BOM items are confirmed.

| File | Location | Purpose |
|---|---|---|
| `README.md` | repo root | JCTsh infrastructure overview, naming conventions, and the authoritative list of existing components |
| `CLAUDE.md` | repo root | Architecture, message flow, MQTT conventions, log format, SmartThings integration path, credentials patterns, and infrastructure details |
| `ENVIRONMENT.md` | repo root | Full smart home device inventory — all hubs, sensors, switches, and integrations |
| `JCTsh-Build-Standards.md` | repo root | Required build, integration, and documentation standards for all JCTsh components |
| `jctsh-network.md` | repo root | DHCP reservations, hostname conventions, WiFi SSIDs, and all assigned device IPs and MACs. Required for network topology decisions and hostname/IP assignments. |
| `JCTsh-Parts-Inventory.md` | repo root | On-hand parts inventory. Must be loaded and scanned before any purchasing decisions are made or any BOM is finalized — on-hand parts must be identified before ordering anything. |
| `README.md` for each existing component | `components/<name>/` | Full ecosystem picture — understanding what exists before designing what's new. Claude reads the root README to identify all listed components, then requests each component README. |

### Phase 2 — Additional files when an existing component is the closest reference model

| File | Location | Purpose |
|---|---|---|
| Claude Code instruction file | `components/<name>/` | The step-by-step build instructions produced in Phase 4 |
| ESPHome YAML or source code | `components/<name>/` | Actual implementation for reference |
| Node-RED flow export (if applicable) | `components/<name>/` | Flow logic for the component |

### How to load files

Claude Code reads files directly from the repo via its file-read tools — no pasting or uploading needed. "Loaded" means read when needed, not read all at once; the phased structure above still governs *when* each file gets read, to keep context focused on what the current phase actually requires.

---

## Phase 1 — Discovery and Feasibility

Start with what you want to accomplish, not how to accomplish it. Describe the goal in plain language and let the research conversation unfold naturally.

### What happens in this phase
- Confirm the technology exists and is appropriate for the goal
- Identify the key components and how they relate to each other
- Surface any compatibility issues, gotchas, or constraints early
- Establish what is proven/known versus what is uncertain
- Narrow down specific hardware and software choices with reasoning

### How it works
Ask questions as they occur to you. Don't worry about asking something that turns out to be irrelevant — that's how you discover what actually matters. The conversation self-organizes around the real constraints as they emerge.

### Example (RV component)
Started with "I'm considering building an eRVin interface" and worked through confirming the Firefly system, RV-C protocol, connector types, network topology, and eRVin capabilities before any purchase decisions were made.

---

## Phase 2 — Hardware Selection

Once the technology is understood, make specific hardware decisions with full context.

### Prerequisite
`JCTsh-Parts-Inventory.md` must be loaded before Phase 2 begins. If it was not loaded in Phase 1, load it now. The inventory scan is the first action in Phase 2 — no hardware direction is assumed and no purchasing decisions are made until on-hand parts are identified.

### What happens in this phase
- **Scan JCTsh-Parts-Inventory.md first** — identify every on-hand compute platform and sensor that could fulfill the component's requirements. State findings explicitly before any purchasing discussion begins. On-hand parts must be used before new parts are sourced.
- Identify every physical component needed
- Consult JCTsh-Build-Standards.md enclosure convention before specifying any enclosure
- Research specific products, part numbers, and sources
- Compare options on price, compatibility, availability, and suitability
- Flag any components that are hard to source or have known issues (counterfeits, supply problems)
- Produce a confirmed bill of materials

### How it works
Research specific products together in the conversation. Use web search to verify current pricing and availability. Don't finalize the BOM until compatibility between all components is confirmed.

### Example (RV component)
Worked through Pi 3B+ vs other Pi versions, PiCAN2 SMPS variant selection, case options (Zebra vs Geekworm vs HighPi vs project box), connector sourcing (DigiKey vs Firefly vs Amazon), and UK vs US sourcing for the PiCAN2.

---

## Phase 3 — Architecture and Integration Design

Define how the new component fits into the existing JCTsh ecosystem before writing a single line of configuration.

### What happens in this phase
- Map the data flow from source to destination
- Define network topology and connectivity scenarios
- Identify integration points with existing components
- Separate what is in scope now from what is a future enhancement
- Make conscious decisions about what NOT to build yet

### How it works
Draw out the architecture in the conversation — even in plain text. Discuss each integration point explicitly. Deliberately defer anything that would complicate the initial build. The goal is a clean, minimal first version that works, not a complete system on day one.

### Phase 3 Required Checklist

Phase 3 is not complete until every item in this checklist has been explicitly decided and documented. These items are not optional and are not subject to deferral.

| Item | Required decision |
|---|---|
| MQTT topic naming | Confirm primary topic and all sub-topics following `jctsh/<type>/<component>/<message-type>` convention — including `/log` and `/heartbeat` |
| MQTT account | Confirm a dedicated Mosquitto account will be created for this component (see JCTsh-Build-Standards.md Section 2.7) |
| Heartbeat | Confirm 5-minute heartbeat publishing to both `/log` and `/heartbeat` topics in standard JSON format |
| Message logging | Confirm logs publish to `/log` topic in standard JSON format — Node-RED wildcard subscription handles routing automatically |
| Watchdog | Confirm heartbeat topic matches `jctsh/<type>/<name>/heartbeat` — Node-RED watchdog wildcard subscription catches it automatically. If the watchdog flow does not yet exist, it must be built as part of this project (see JCTsh-Build-Standards.md Section 4.4) |
| SmartThings device type | Decide: motion sensor, virtual switch, contact sensor, presence sensor, or other — consult JCTsh-Build-Standards.md Section 5.1 |
| SmartThings integration path | Confirm Node-RED → HA REST API → virtual switch/entity → SmartThings — no other path exists |
| Timeout / timer logic | Decide where each timeout lives: ESPHome (smoothing), Node-RED (flow logic), or HA (automation logic) — document all timeouts with their distinct purposes |
| LED indicators | Decide whether LEDs are included, which GPIOs, and what state each reflects — consult JCTsh-Build-Standards.md Section 8 |
| Bench/install boundary | Identify explicitly which steps are bench work and which require the component to be in its final installed location. Document the dividing line. |

### Example (RV component)
Mapped the full path from Firefly RV-C bus through PiCAN2 to eRVin to MQTT to Home Assistant to SmartThings to Google Home, then deliberately deferred everything from Home Assistant onward until the RV component itself is proven.

---

## Phase 4 — Produce the Claude Code Instructions

Convert everything learned in Phases 1–3 into a structured instruction set for Claude Code.

### What happens in this phase
- Write step-by-step instructions that interleave Claude Code actions with real-world actions
- Every step has a clear owner: Claude Code creates, Joseph does, Joseph confirms
- Hardware context and network architecture are documented at the top so Claude Code has full project context without needing to re-research
- Future enhancements are explicitly called out and deferred — not forgotten, just sequenced
- Notes for Claude Code capture non-obvious things that would otherwise go wrong (bitrates, jumper settings, counterfeit warnings, etc.)
- Bench steps are sequenced before install steps — the bench/install boundary is marked with an explicit dividing section header

### The step structure
Each step follows this pattern:

1. **Claude Code does** — creates documentation, configuration files, or scripts
2. **Joseph does** — follows that documentation to perform real-world work
3. **Joseph confirms** — reports results before proceeding
4. **Claude Code does** *(if needed)* — updates documentation to reflect actual findings

### Critical rules
- Claude Code does not proceed until Joseph confirms each step
- Real-world deviations get captured in the documentation immediately
- The instructions are living documents, not static guides
- **All steps that can be completed on the workbench must be sequenced before any step that requires the component to be in its final installed location.** The bench/install boundary must appear as an explicit dividing section header in the instruction set. Do not proceed to install steps until all bench steps are confirmed complete.

---

## Phase 5 — Execution in Claude Code

Continue in the same Claude Code session (or a resumed one) with the full instruction set from Phase 4 and execute step by step.

### What happens in this phase
- **Step 0 — Read Build Standards first.** Before writing any code, config, or documentation, Claude Code reads `JCTsh-Build-Standards.md` in full and identifies every section relevant to the anticipated technologies for this build (ESPHome YAML, Node-RED flows, MQTT conventions, LED wiring, enclosures, SmartThings integration, etc.). Claude Code states explicitly which standards apply and confirms it will follow them before any build work begins.
- Claude Code works through the instructions sequentially
- Joseph performs physical and configuration work guided by Claude Code's documents
- Results feed back into the documentation in real time
- Unexpected issues get researched and diagnosed in the same Claude Code session
- **Final step — Harvest new patterns.** After the build is confirmed complete, Claude Code reviews the completed implementation for coding patterns, configuration decisions, or integration approaches that are not yet captured in `JCTsh-Build-Standards.md`. Claude Code proposes specific additions or updates to the standards document. Joseph reviews and approves before any changes are written.

### The feedback loop
If something doesn't work as expected during execution, research and diagnose it in the same Claude Code session — it has the tools (web search, file access, live system access) to do both research and continuation without switching tools. Chat is not re-entered once the card exists in Backlog.

---

## What Makes This Pattern Work

**Separation of concerns.** Chat is for informal, pre-card thinking — whether to build something at all. Claude Code is for everything once that decision is made: researching, planning, designing, and building, in the same continuous process. The boundary is the card's creation, not a tool switch partway through Phases 1–5.

**Research before purchase.** Every hardware decision is made with full compatibility context. No buying something only to discover it doesn't work with something else.

**Parts inventory first.** On-hand parts are checked before any purchasing decisions. No buying something you already have.

**Inventory scan at the start of Phase 2.** The inventory scan is the first action in Phase 2 — before hardware discussion begins. On-hand compute platforms and sensors are identified and stated explicitly so no purchasing decision is made without awareness of what is already available. Phase 1 is about feasibility and approach; the inventory check is a purchasing constraint that belongs in Phase 2.

**Build standards before hardware selection — and before first line of code.** `JCTsh-Build-Standards.md` is loaded at the start of Phase 2 so enclosure convention, GPIO rules, MQTT conventions, and documentation requirements are applied from the start of hardware selection — not retrofitted at the end. In Phase 5, Claude Code re-reads Build Standards as Step 0 and states which sections apply before writing any code or config. At the end of Phase 5, Claude Code reviews the completed build for patterns not yet captured in Build Standards and proposes additions for Joseph's approval.

**Phased file loading.** Context files are loaded when they become necessary, not all at once before anything begins. Phase 1 needs only the planning pattern and the environmental architecture doc. Hardware, integration, network, and inventory files are loaded at Phase 2 when they actually drive decisions. Loading files before they are needed adds friction without adding value.

**Architecture context before integration design.** CLAUDE.md is a required Phase 2 context file. It contains the actual message flow, log format, SmartThings integration path, and credentials patterns. Without it, integration decisions in Phase 3 are made on incorrect assumptions.

**Environmental architecture context before payload design.** core/data-pipeline/JCTsh-Environmental-Data-Architecture.md is a required Phase 1 context file. It contains pre-existing architectural decisions for the entire environmental sensor family — payload schema, MQTT topic conventions, Google Sheets archive design, and the planned device family. Without it, a new environmental sensor component will contradict or duplicate decisions already made.

**Property sensor pattern before hardware selection.** JCTsh-Property-Sensor-Pattern.md is a required Phase 1 context file for any property sensor build. It defines the invariant standard (what every sensor does identically), the variable dimensions (location type, power source, connectivity, offline handling), and a 12-item checklist that produces concrete firmware values before Phase 2 hardware selection begins. Work through the checklist in Phase 1 — decisions made there drive hardware choices in Phase 2.

**Network context before topology decisions.** jctsh-network.md is a required Phase 2 context file. It contains DHCP reservations, hostname conventions, and all assigned device IPs and MACs. Without it, network topology decisions in Phase 3 and hostname/IP assignments in Phase 4 are made without visibility into what is already allocated.

**Deliberate deferral.** Explicitly deciding what not to build yet is as important as deciding what to build. Future enhancements are documented so they aren't lost, but they don't complicate the current build.

**Observability is not optional.** Every component publishes to the `/log` topic in standard JSON format and publishes a 5-minute heartbeat. The Node-RED watchdog monitors heartbeats and alerts via the HA companion app on Joseph's Pixel 10 Pro. SmartThings exposure is decided during Phase 3, not deferred.

**Bench-first prototyping.** All steps that can be performed on the workbench — hardware assembly, image flashing, software configuration, WiFi testing, integration verification, and end-to-end testing — are completed and confirmed on the bench before the component is installed in its final location. Physical installation is the final phase of the build, not an early step. This applies to all component types: ESP32/ESPHome components (bench before perfboard transfer and permanent mounting), Pi-based components (bench before coach or wall installation), and any other hardware. The instruction set must make the bench/install boundary explicit with a dedicated dividing section header. Do not proceed to installation steps until all bench steps are confirmed complete.

**Real-world steps are first-class.** The instruction set treats physical assembly, wiring, and testing as formal steps equal in importance to software configuration. Nothing is hand-waved with "then install the hardware."

**Documentation captures reality.** Instructions get updated with actual findings, not just intentions. The repo reflects what was actually built, not what was planned.

**Context travels with the project.** The Claude Code instruction set contains enough context that a fresh Claude Code session can execute it without needing to re-read the entire planning conversation.

---

## Template for Starting a New Component

Preliminary thinking can start in a Claude chat session, informally:

> *"I want to add a [component name] to JCTsh. Here's what I'm trying to accomplish: [goal in plain language]. Here's what I already have that's relevant: [existing infrastructure]. I don't know yet whether [specific uncertainty]. Let's start by figuring out whether this is feasible and what the right approach is."*

Once that preliminary thinking produces a real decision to build something, move to Claude Code: create a card capturing the thinking so far, place it in Backlog, and work through Phases 1–5 there — start to finish, in the same tool.

---

## Template for Claude Code Instructions

Use this structure when producing the instruction set at the end of Phase 4:

```
# JCTsh [Component Name] — Claude Code Instructions

## Overview
[What this component does and how it fits into JCTsh]

## Working Pattern
Claude Code creates documentation and configuration files. Joseph follows
those documents to perform physical assembly, wiring, and software
configuration work outside of Claude Code. Joseph reports results back,
and Claude Code updates documentation to reflect actual findings,
deviations, and lessons learned. Do not proceed to the next step until
Joseph confirms the current step is complete.

## Hardware Context
[Specific hardware, part numbers, key constraints, GPIO assignments,
LED assignments, enclosure decision]

## Network / Integration Architecture
[Data flow, MQTT topics including /log and /heartbeat, connectivity
scenarios, integration points — SmartThings device type and integration
path via Node-RED → HA REST API, timeout locations and their distinct
purposes]

## Step 0 — Read Build Standards

**Claude Code does:**
Read `JCTsh-Build-Standards.md` in full. Identify every section relevant to the technologies anticipated for this build: ESPHome YAML conventions, Node-RED flow patterns, MQTT topic and log format standards, LED wiring rules, enclosure convention, SmartThings integration path, MQTT account creation, and any other applicable sections. State explicitly which standards apply to this build and confirm they will be followed before any code, config, or documentation is written.

**Joseph confirms:**
Acknowledged — proceed.

---

## BENCH PHASE

All steps in this section are performed on the workbench. No step in
this section requires the component to be in its final installed
location. Do not proceed to the Install Phase until every bench step
below is confirmed complete.

## Step N — [Step Name]

**Claude Code does:**
[Specific documents or files to create]

**Joseph does:**
[Specific physical or configuration actions to perform]

**Joseph confirms:**
[What Joseph reports back before proceeding]

**Claude Code does:** (if needed)
[Documentation updates based on Joseph's findings]

---

## Bench Phase Complete — Install Phase Begins

All bench steps above are confirmed complete. The component has been:
[Bullet summary of what was verified on the bench]

Do not proceed to Step N+1 until all bench steps are confirmed complete.

---

## INSTALL PHASE

All steps in this section require the component to be in its final
installed location.

## Step N+1 — [Step Name]

[Same step structure as bench phase]

## Step [Final] — Harvest New Patterns into Build Standards

**Claude Code does:**
Review the completed build in full — ESPHome YAML, Node-RED flows, HA config, wiring decisions, integration approaches, and any deviations from original plans. Identify coding patterns, configuration decisions, or integration approaches that are not yet captured in `JCTsh-Build-Standards.md` or that supersede existing entries. For each candidate, state: (a) what the pattern is, (b) where it appeared in this build, and (c) the proposed addition or update to Build Standards. Do not write changes to `JCTsh-Build-Standards.md` until Joseph reviews and approves.

**Joseph does:**
Review proposed additions. Approve, modify, or reject each one.

**Joseph confirms:**
Approved additions identified. Proceed to update `JCTsh-Build-Standards.md`.

**Claude Code does:**
Write approved additions and updates to `JCTsh-Build-Standards.md`. Bump the version number and update the version description to reflect what was added.

---

## Future Enhancement — [Deferred Feature Name]
[What was deferred and why, with enough detail to pick it up later]

## Notes for Claude Code
[Non-obvious constraints, gotchas, naming conventions, cross-references]

--- Required notes for every ESP32 component ---
- Step 0 is mandatory: read JCTsh-Build-Standards.md in full, state which sections apply, and confirm before writing any code or config — CLAUDE.md must also be read before beginning
- Read core/data-pipeline/JCTsh-Environmental-Data-Architecture.md if this is an
  environmental sensor — payload schema and MQTT topic convention
  are defined there and must be followed exactly
- Read JCTsh-Property-Sensor-Pattern.md if this is a property sensor
  (fixed, mobile, battery, solar, or USB environmental sensor) —
  confirm the new-sensor checklist was completed in Phase 1 and all
  variable dimensions are resolved before writing any firmware
- Log format: JSON to jctsh/<type>/<component>/log —
  { "component": "<name>", "category": "<cat>", "message": "<text>" }
  Node-RED wildcard subscription handles routing automatically
- Heartbeat: publish to both /log and /heartbeat topics every 5 minutes
  Node-RED watchdog wildcard subscription catches /heartbeat automatically
- If Node-RED watchdog flow does not yet exist, build it as part of
  this project — see JCTsh-Build-Standards.md Section 4.4
- SmartThings path: Node-RED → HA REST API (port 8123) → virtual
  switch/entity → SmartThings — no other path exists
- Examine salt sensor implementation as SmartThings reference pattern
- MQTT account: create dedicated Mosquitto account before first flash —
  see JCTsh-Build-Standards.md Section 2.7 for commands and ownership gotcha
- Add new account to credentials table in root CLAUDE.md
- Record new device IP, hostname, and MAC in jctsh-network.md
- Consult JCTsh-Parts-Inventory.md before adding any item to the BOM
- Update JCTsh-Parts-Inventory.md inventory update log at final step
- Bench-first: all bench steps must be confirmed complete before any
  install step begins — enforce the bench/install boundary strictly
```

---

## Pattern Summary

| Phase | Where | Purpose |
|---|---|---|
| 0 — Preliminary thinking | Claude chat (informal, no card yet) | Decide whether to build something at all |
| 1 — Discovery | Claude Code | Establish feasibility and understand the technology |
| 2 — Hardware | Claude Code | Select and confirm all physical components |
| 3 — Architecture | Claude Code | Design integration with existing JCTsh ecosystem |
| 4 — Instructions | Claude Code | Produce the Claude Code instruction set |
| 5 — Execution | Claude Code | Build, document, and test with real-world feedback |

Phase 0 has no card and produces no planning documents — see `JCTsh-Operating-System.md`'s "Where Work Happens" section. A card is created in Backlog once Phase 0 ends with a decision to build, and Phases 1–5 proceed from there entirely in Claude Code.

---

*This pattern was developed during the JCTsh RV component planning project (2025) and is intended to be reused for every subsequent JCTsh component build.*