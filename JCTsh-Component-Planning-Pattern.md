# JCT Smart Home (JCTsh) Component Planning Pattern

## Core Principle

Use Claude chat for **thinking, researching, and planning**. Use Claude Code for **implementation, documentation, and execution**. The two work in sequence, not in parallel — the chat session produces the blueprint that Claude Code builds from.

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

**Deliberate deferral.** Explicitly deciding what not to build yet is as important as deciding what to build. Future enhancements are documented so they aren't lost, but they don't complicate the current build.

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
[Specific hardware, part numbers, key constraints]

## Network / Integration Architecture
[Data flow, connectivity scenarios, integration points]

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

## Future Enhancement — [Deferred Feature Name]
[What was deferred and why, with enough detail to pick it up later]

## Notes for Claude Code
[Non-obvious constraints, gotchas, naming conventions, cross-references]
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
