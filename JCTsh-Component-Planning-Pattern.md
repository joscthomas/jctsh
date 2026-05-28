# JCT Smart Home (JCTsh) Component Planning Pattern
**Author:** Joseph C Thomas (JCT)
**Purpose:** Defines the five-phase process for planning and building JCTsh smart home components, from discovery through execution.
**Version:** 1.8
**Version description:** Added `JCTsh-Environmental-Data-Architecture.md` and `jctsh-network.md` to the required context file list in Step 1. Added explicit file confirmation rule: Claude must name all missing files and confirm receipt of all required files before asking any planning questions. Both changes identified during the hiking monitor planning session (May 2026).

---

## Core Principle

Use Claude chat for **thinking, researching, and planning**. Use Claude Code for **implementation, documentation, and execution**. The two work in sequence, not in parallel — the chat session produces the blueprint that Claude Code builds from.

---

## Context Files Required

Before any component planning session can begin, load the following files into the Claude chat session. Claude will not proceed with Phase 1 until all required files are present.

**File confirmation rule:** When a session begins, Claude must immediately identify which required files are present and which are missing, name the missing files explicitly, and wait for them to be loaded before asking any planning questions. Claude must not proceed with Phase 1 — not even a single clarifying question — until all required files are confirmed received.

### Step 1 — Load first

| File | Location | Purpose |
|---|---|---|
| `README.md` | repo root | JCTsh infrastructure overview, naming conventions, and the authoritative list of existing components |
| `CLAUDE.md` | repo root | Architecture, message flow, MQTT conventions, log format, SmartThings integration path, credentials patterns, and infrastructure details |
| `ENVIRONMENT.md` | repo root | Full smart home device inventory — all hubs, sensors, switches, and integrations |
| `JCTsh-Parts-Inventory.md` | repo root | On-hand parts inventory — hardware available for use before any purchasing decisions are made |
| `JCTsh-Build-Standards.md` | repo root | Required build, integration, and documentation standards for all JCTsh components |
| `JCTsh-Component-Planning-Pattern.md` | repo root | This document — the planning process itself |
| `JCTsh-Environmental-Data-Architecture.md` | repo root | Standard environmental sensor payload schema, Google Sheets archive design, Node-RED wildcard handler pattern, Weather Underground integration, and the planned environmental sensor family. Required for all components — contains pre-existing architectural decisions that shape integration design. |
| `jctsh-network.md` | repo root | DHCP reservations, hostname conventions, WiFi SSIDs, and all assigned device IPs and MACs. Required for Phase 3 network topology decisions and Phase 4 instruction writing. |

### Step 2 — Claude reads the root README and requests these

After reading the root README, Claude identifies every listed component and requests:

| File | Location | Purpose |
|---|---|---|
| `README.md` for each component | `components/<name>/` | Full ecosystem picture — understanding what exists before designing what's new |

### Step 3 — Required in addition when an existing component is the closest reference model

| File | Location | Purpose |
|---|---|---|
| Claude Code instruction file | `components/<name>/` | The step-by-step build instructions produced in Phase 4 |
| ESPHome YAML or source code | `components/<name>/` | Actual implementation for reference |
| Node-RED flow export (if applicable) | `components/<name>/` | Flow logic for the component |

### How to load files

Paste file contents directly into the chat, or use the file upload feature. State which file each paste represents. Claude will confirm when it has sufficient context to begin Phase 1.

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

### What happens in this phase
- Identify every physical component needed
- Check JCTsh-Parts-Inventory.md first — use on-hand parts before purchasing
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

Hand off to Claude Code with the full instruction set and execute step by step.

### What happens in this phase
- Claude Code works through the instructions sequentially
- Joseph performs physical and configuration work guided by Claude Code's documents
- Results feed back into the documentation in real time
- Unexpected issues come back to the Claude chat session if they need deeper research

### The feedback loop
If something doesn't work as expected during execution, bring it back to the Claude chat session for research and diagnosis, then take the solution back to Claude Code for documentation and continuation. The chat session remains available as a research resource throughout the build.

---

## What Makes This Pattern Work

**Separation of concerns.** Chat is for thinking. Code is for building. Mixing them produces confusion.

**Research before purchase.** Every hardware decision is made with full compatibility context. No buying something only to discover it doesn't work with something else.

**Parts inventory first.** On-hand parts are checked before any purchasing decisions. No buying something you already have.

**Build standards first.** JCTsh-Build-Standards.md is loaded at the start of every session. Enclosure convention, GPIO rules, MQTT conventions, and documentation requirements are applied from the start — not retrofitted at the end.

**Architecture context first.** CLAUDE.md is a required context file. It contains the actual message flow, log format, SmartThings integration path, and credentials patterns. Without it, integration decisions are made on incorrect assumptions.

**Environmental architecture context first.** JCTsh-Environmental-Data-Architecture.md is a required context file. It contains pre-existing architectural decisions for the entire environmental sensor family — payload schema, MQTT topic conventions, Google Sheets archive design, and the planned device family. Without it, a new environmental sensor component will contradict or duplicate decisions already made.

**Network context first.** jctsh-network.md is a required context file. It contains DHCP reservations, hostname conventions, and all assigned device IPs and MACs. Without it, network topology decisions in Phase 3 and hostname/IP assignments in Phase 4 are made without visibility into what is already allocated.

**Deliberate deferral.** Explicitly deciding what not to build yet is as important as deciding what to build. Future enhancements are documented so they aren't lost, but they don't complicate the current build.

**Observability is not optional.** Every component publishes to the `/log` topic in standard JSON format and publishes a 5-minute heartbeat. The Node-RED watchdog monitors heartbeats and alerts via the HA companion app on Joseph's Pixel 10 Pro. SmartThings exposure is decided during Phase 3, not deferred.

**Bench-first prototyping.** All steps that can be performed on the workbench — hardware assembly, image flashing, software configuration, WiFi testing, integration verification, and end-to-end testing — are completed and confirmed on the bench before the component is installed in its final location. Physical installation is the final phase of the build, not an early step. This applies to all component types: ESP32/ESPHome components (bench before perfboard transfer and permanent mounting), Pi-based components (bench before coach or wall installation), and any other hardware. The instruction set must make the bench/install boundary explicit with a dedicated dividing section header. Do not proceed to installation steps until all bench steps are confirmed complete.

**Real-world steps are first-class.** The instruction set treats physical assembly, wiring, and testing as formal steps equal in importance to software configuration. Nothing is hand-waved with "then install the hardware."

**Documentation captures reality.** Instructions get updated with actual findings, not just intentions. The repo reflects what was actually built, not what was planned.

**Context travels with the project.** The Claude Code instruction set contains enough context that a fresh Claude Code session can execute it without needing to re-read the entire planning conversation.

---

## Template for Starting a New Component

When beginning a new JCTsh component project, open a Claude chat session and start with:

> *"I want to add a [component name] to JCTsh. Here's what I'm trying to accomplish: [goal in plain language]. Here's what I already have that's relevant: [existing infrastructure]. I don't know yet whether [specific uncertainty]. Let's start by figuring out whether this is feasible and what the right approach is."*

Then work through Phases 1–4 before touching Claude Code.

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

---

## Future Enhancement — [Deferred Feature Name]
[What was deferred and why, with enough detail to pick it up later]

## Notes for Claude Code
[Non-obvious constraints, gotchas, naming conventions, cross-references]

--- Required notes for every ESP32 component ---
- Read JCTsh-Build-Standards.md and CLAUDE.md before beginning
- Read JCTsh-Environmental-Data-Architecture.md if this is an
  environmental sensor — payload schema and MQTT topic convention
  are defined there and must be followed exactly
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
| 1 — Discovery | Claude chat | Establish feasibility and understand the technology |
| 2 — Hardware | Claude chat | Select and confirm all physical components |
| 3 — Architecture | Claude chat | Design integration with existing JCTsh ecosystem |
| 4 — Instructions | Claude chat | Produce the Claude Code instruction set |
| 5 — Execution | Claude Code | Build, document, and test with real-world feedback |

---

*This pattern was developed during the JCTsh RV component planning project (2025) and is intended to be reused for every subsequent JCTsh component build.*