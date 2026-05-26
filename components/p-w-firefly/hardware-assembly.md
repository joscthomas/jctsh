# Hardware Assembly — Pleasure-Way Firefly Interface

Assemble the Raspberry Pi 3B+, PiCAN2 SMPS HAT, and Geekworm acrylic sandwich case.

---

## Pre-Assembly Checklist

- [ ] Power is off — nothing is plugged in
- [ ] Anti-static precautions taken (work on a non-static surface; handle boards by edges)
- [ ] Confirm JP3 jumper is NOT installed on PiCAN2 before assembly — see JP3 warning below

---

## JP3 Termination Jumper — Critical Warning

**Do NOT install the JP3 jumper on the PiCAN2 board.**

This device connects to the Firefly RV-C bus as a Drop (tap), not a Trunk endpoint. The Firefly network already has two termination resistors at its trunk endpoints. Adding a third via JP3 will disrupt the entire RV-C bus and may prevent the Vegatouch system from functioning.

Inspect the PiCAN2 board before assembly and confirm JP3 is absent. If a jumper is present, remove it now.

---

## Inspect PiCAN2 Board

Before assembly, visually confirm:
- JP3 jumper is absent (see above)
- Screw terminal block is seated and all four terminals are labeled: +Vin, GND, CAN-H, CAN-L
- Two small ICs are present near the screw terminal end of the board (CAN controller and CAN transceiver)

**Note on IC identification:** Newer PiCAN2 SMPS revisions use the MCP2562 as the CAN transceiver — a pin-compatible replacement for the MCP2551 that Microchip introduced when MCP2551 went end-of-life. SMD ICs on the HAT may also have abbreviated or unreadable markings. If the board is from Copperhill Technologies and the screw terminals are labeled correctly, IC identification by part number is not required — the board is correct.

---

## Assembly Procedure

### 1. Align PiCAN2 HAT onto Pi 3B+

- Hold the PiCAN2 HAT above the Pi 3B+ and align the 40-pin GPIO header
- Correct orientation: the USB ports on the Pi and the screw terminal block on the PiCAN2 should be on the same side of the assembly
- Lower the HAT straight down onto the GPIO header — do not tilt
- Press firmly until all 40 pins are fully seated — the HAT should sit flat with no pin gaps visible

### 2. Secure with standoffs

- If the Geekworm case kit includes M2.5 brass standoffs, install them between the Pi and HAT at the four corner mounting holes
- Hand-tighten only — do not overtorque M2.5 hardware

### 3. Install into Geekworm acrylic sandwich case

- Follow the Geekworm case assembly instructions for the specific model
- The assembled Pi+HAT stack installs as a unit into the case
- Route the PiCAN2 screw terminal block and DB9 connector to an accessible side of the case — these must remain reachable for wiring and future service
- Secure case panels with included hardware

### 4. Label the case

Attach a label to the outside of the case:

```
eRVin — Pleasure-Way Firefly Interface
Assembled: May 2026
```

---

## After Assembly

Do not apply power yet. MicroSD card preparation (Steps 4–5) must be completed before first boot.

---

## Deviations

*(Update this section after assembly with any fit issues, missing hardware, or deviations from the procedure above.)*
