# JCTsh Pleasure-Way Firefly Interface — Claude Code Instructions
**Author:** Joseph C Thomas (JCT)
**Purpose:** Step-by-step build instructions for the p-w-firefly component — eRVin-based coach control interface for the 2018 Pleasure-Way Lexor FL.
**Project:** JCT Smart Home (JCTsh)
**Version:** 1.1
**Version description:** Added explicit bench/install phase boundary per JCTsh-Component-Planning-Pattern v1.7. All bench-verifiable steps (hardware assembly, image flash, driver config, first boot, eRVin configuration, WiFi hotspot, Tailscale) are now grouped in the Bench Phase. Physical RV installation and in-coach testing are in the Install Phase. MicroSD swap moved to Install Phase. Bench power note promoted from Notes section into Step 6 directly.
**Related files:** README.md, CLAUDE.md, ENVIRONMENT.md, JCTsh-Build-Standards.md, JCTsh-Component-Planning-Pattern.md, jctsh-parts-inventory.md

---

## Overview

The Pleasure-Way Firefly Interface connects a Raspberry Pi 3B+ with a PiCAN2 SMPS CAN-Bus HAT to the Firefly Integrations Vegatouch RV-C network in the 2018 Pleasure-Way Lexor FL (Ram ProMaster 3500, VIN 3C6URVJG9JE113400). The eRVin software (myervin.com) provides a web dashboard accessible from both household Pixels for monitoring and controlling coach systems — tanks, battery, lights, generator, awning, water pump, shore power, and inverter.

This is a Pi-based component, not ESP32/ESPHome. The eRVin image owns the RV Pi entirely. JCTsh standards for ESP32 components (ESPHome, MQTT accounts, heartbeat, watchdog, Node-RED flows) do not apply to the initial build. Smart home integration — MQTT bridging to the home Pi, HA entities, SmartThings, Google Home — is explicitly deferred to a future phase.

---

## Working Pattern

Claude Code creates documentation and configuration files. Joseph follows those documents to perform physical assembly, wiring, flashing, and configuration outside of Claude Code. Joseph reports results back, and Claude Code updates documentation to reflect actual findings, deviations, and lessons learned. Do not proceed to the next step until Joseph confirms the current step is complete.

---

## Hardware Context

| Component | Detail |
|---|---|
| Single-board computer | Raspberry Pi 3B+ |
| CAN-Bus HAT | Copperhill Technologies PiCAN2 SMPS (MCP2515/MCP2551) |
| Case | Geekworm Universal HAT acrylic sandwich case |
| MicroSD card (bench/setup) | On-hand card — used for Bench Phase only |
| MicroSD card (permanent) | SanDisk MAX Endurance 32GB microSDHC (ASIN B084CJLNM4) |
| RV-C connector | 3M Mini-Clamp 37104-A165-00E, 4-position, 2mm pitch IDC |
| Drop cable | 4-conductor stranded 20–24AWG or CAT5 (on hand) |
| 12V power tap | From coach 12V bus, downstream of LCD panel power switch |
| Fuse | Inline fuse on 12V tap wire |
| Software | eRVin OS image (myervin.com) |

**PiCAN2 screw terminal pinout (left to right):**

| Terminal | Connection |
|---|---|
| +Vin | 12V coach power (via inline fuse) |
| GND | Coach ground |
| CAN-H | 3M connector Blue wire (pin 3) |
| CAN-L | 3M connector Red wire (pin 1) |

**3M Mini-Clamp connector wire order (clip blue-side up, pin 1 at left):**

| Pin | Color | Connect to |
|---|---|---|
| 1 | Red | CAN-L → PiCAN2 screw terminal |
| 2 | White | Firefly 12V bus — do NOT connect to PiCAN2 |
| 3 | Blue | CAN-H → PiCAN2 screw terminal |
| 4 | Black | Ground — share with PiCAN2 GND terminal |

**Critical:** Do NOT install the JP3 termination jumper on the PiCAN2. Connecting as a Drop, not a Trunk endpoint. The Firefly network already has two termination resistors — adding a third will disrupt the RV-C bus.

**Power loss note:** Coach power is cut abruptly by the LCD panel power switch when the RV is stored. The red battery disconnect key is used only to prevent solar charging in near-freezing weather — it is NOT the coach power switch. No graceful shutdown hardware is used. The SanDisk MAX Endurance card is specified for the permanent install to handle abrupt power loss. During the eRVin software setup step, check whether the eRVin image supports a read-only overlay filesystem and enable it if available.

---

## Network / Integration Architecture

```
SCENARIO 1 — Home driveway
RV Pi → home WiFi (priority 1, pre-loaded in eRVin image)
RV Pi gets reserved static IP on home network
Pixels → home WiFi → eRVin dashboard at reserved IP
Tailscale available but not required

SCENARIO 2 — Traveling, Pixel 10 Pro hotspot active
RV Pi → Pixel 10 Pro hotspot (priority 2, known network)
Tailscale tunnel established over cellular data
Pixels → eRVin dashboard via Tailscale IP
Home Pi can reach RV MQTT broker via Tailscale (future use)

SCENARIO 3 — Traveling, no known network (fallback)
RV Pi → own hotspot "JCT-RV" (priority 3)
Pixels → JCT-RV → eRVin dashboard at Pi hotspot IP (192.168.4.1)
No home connectivity
Full coach control available offline

STORAGE
RV Pi unpowered — coach power off via LCD panel switch
Home HA shows RV entities as unavailable (future integration phase)
No action required
```

**WiFi priority order:**
1. Home WiFi SSID (pre-loaded in eRVin image before first flash)
2. Joseph's Pixel 10 Pro hotspot (added after first boot via SSH)
3. JCT-RV hotspot (Pi's own fallback — activates when no known network found)

**Tailscale:** RV Pi joins the existing JCTsh Tailscale account. Home Pi already at Tailscale IP `100.70.162.24`. RV Pi Tailscale IP assigned after setup — document when confirmed.

**eRVin MQTT broker:** Runs on RV Pi as part of eRVin image. Publishes Firefly RV-C data on eRVin's native topic structure. Home Node-RED will subscribe directly to these topics in the future integration phase (Option A — no JCTsh topic translation in initial build).

**RV-C bus bitrate:** 250kbps. Not 500kbps. Critical — wrong bitrate produces no CAN traffic.

---

## Future Enhancement — Smart Home Integration

The following items are deferred until all build steps are complete and the RV component is working and proven. Refer to the planning conversation for full details.

**MQTT topic strategy (Option A):** Home Node-RED subscribes directly to eRVin's native MQTT topics over Tailscale. No JCTsh topic convention applied in the initial build. Option B (republish under `jctsh/rv/ervin/<message-type>`) is documented as an alternative if needed later.

**When ready to implement:**
- Create dedicated `rv-ervin` MQTT account on home Mosquitto broker (Build Standards Section 2.7)
- Add Node-RED flow on home Pi subscribing to RV MQTT broker topics via Tailscale IP
- Define HA entities: tank levels, battery state of charge, shore power, generator, inverter, water pump, lights, awning
- Define HA automations: battery low alert, tank level alerts, pump run warning
- Build HA dashboard card for RV systems
- Define SmartThings device types and integration path (Node-RED → HA REST API → SmartThings)
- Add JCTsh heartbeat/watchdog/log topics per Build Standards Section 4

---

## BENCH PHASE

All steps in this section are performed on the workbench. No step in this section requires the component to be in the Pleasure-Way Lexor FL. Do not proceed to the Install Phase until every bench step below is confirmed complete.

---

## Step 1 — Create Component Structure

**Claude Code does:**
Review the existing JCTsh repo structure. Create the `components/p-w-firefly/` directory with placeholder files consistent with existing component conventions. Do not impose structure — follow what exists. Create a stub `README.md` noting this component is in progress.

Update the root `README.md` Components list to add `p-w-firefly — Pleasure-Way Firefly Interface (in progress)`.

**Joseph confirms:**
Component directory structure created and looks correct. Root README updated.

---

## Step 2 — Bill of Materials

**Claude Code does:**
Create `components/p-w-firefly/bill-of-materials.md` with all components, descriptions, sources, and costs:

| Item | Description | Source | Cost |
|---|---|---|---|
| Raspberry Pi 3B+ | Element14 | On hand (from inventory) | — |
| PiCAN2 SMPS HAT | Copperhill Technologies | Received | ~$65 |
| Geekworm HAT case | Amazon B074T7D1V5 | On hand (from inventory) | — |
| MicroSD — bench | On-hand card | On hand | — |
| MicroSD — permanent | SanDisk MAX Endurance 32GB (ASIN B084CJLNM4) | Amazon | ~$13 |
| 3M connectors | 37104-A165-00E, qty 4–6 | Received | ~$5 |
| Drop cable | 4-conductor 20–24AWG or CAT5 | On hand | — |
| 12V tap wire + inline fuse | Coach power connection | On hand | — |

**Joseph confirms:**
BOM accurate. SanDisk MAX Endurance card received before Step 13 (permanent MicroSD swap).

---

## Step 3 — Hardware Assembly

**Claude Code does:**
Create `components/p-w-firefly/hardware-assembly.md` covering:

- Pre-assembly checklist: power off, anti-static precautions, confirm JP3 jumper is NOT installed on PiCAN2 before assembly
- Inspect PiCAN2 board — confirm MCP2515 and MCP2551 ICs are present and labeled
- Align PiCAN2 HAT onto Pi 3B+ 40-pin GPIO header — note correct orientation (USB ports and screw terminal on same side)
- Seat firmly — all 40 pins engaged
- Secure with M2.5 standoffs if included with Geekworm case kit
- Install assembled Pi+HAT stack into Geekworm acrylic sandwich case
- Route screw terminal and DB9 connector to accessible side of case
- Label case with "eRVin — Pleasure-Way Firefly Interface" and assembly date

**Joseph does:**
Follow hardware-assembly.md to assemble Pi, PiCAN2 HAT, and Geekworm case. Do not apply power yet.

**Joseph confirms:**
Assembly complete. JP3 jumper confirmed absent. Note any fit issues or deviations.

**Claude Code does:**
Update hardware-assembly.md with any confirmed deviations.

---

## Step 4 — MicroSD Preparation and eRVin Image Flash

**Claude Code does:**
Create `components/p-w-firefly/image-setup.md` covering:

- Download the current eRVin OS image from myervin.com — confirm correct image for Pi 3B+
- Download and install Balena Etcher on Windows
- Before flashing: locate the eRVin image pre-configuration method for embedding home WiFi credentials — document the exact procedure from myervin.com instructions (this varies by eRVin version)
- Pre-load home WiFi SSID and password into the image so Pi connects on first boot without keyboard/monitor
- Flash image to on-hand MicroSD card using Balena Etcher
- Safely eject MicroSD card
- Do not insert into Pi yet — Step 5 edits the boot partition first

**Joseph does:**
Download eRVin image, pre-load home WiFi credentials, flash to on-hand MicroSD card. Report eRVin image version number.

**Joseph confirms:**
MicroSD card flashed. eRVin version documented. WiFi credentials pre-loaded.

**Claude Code does:**
Update image-setup.md with confirmed eRVin version and any procedure deviations.

---

## Step 5 — PiCAN2 Driver Configuration

**Claude Code does:**
Create `components/p-w-firefly/pican2-config.md` covering:

- Re-insert MicroSD into Windows PC after flashing
- The boot partition appears as a small FAT32 volume readable on Windows
- Open `config.txt` on the boot partition and add the following lines at the end:

```
dtparam=spi=on
dtoverlay=mcp2515-can0,oscillator=16000000,interrupt=25
dtoverlay=spi-bcm2835-overlay
```

- Save and safely eject
- Also document the can0 interface bring-up command:

```bash
sudo ip link set can0 up type can bitrate 250000
```

- Document how to make this persistent at boot (via `/etc/network/interfaces` or a systemd service) — check whether eRVin image already handles this automatically and document the finding
- Note prominently: bitrate is 250000 (RV-C spec) — NOT 500000

**Joseph does:**
Re-insert MicroSD into Windows PC. Edit config.txt on boot partition. Add the three required lines. Safely eject. Re-insert MicroSD into assembled Pi.

**Joseph confirms:**
config.txt updated correctly. MicroSD inserted into Pi.

---

## Step 6 — First Boot on Home Network

**Claude Code does:**
Create `components/p-w-firefly/first-boot.md` covering:

**Bench power — important:**
The PiCAN2 SMPS takes 12V input at its screw terminal. For all bench steps (Steps 6–9) that do not require CAN bus connectivity, power the Pi via its micro-USB port directly — this bypasses the SMPS entirely and is the correct approach for bench work. Do not connect the screw terminal to anything during bench steps. The screw terminal is wired to coach 12V only during Step 11 (physical installation in the coach).

**First boot procedure:**
- Power the Pi via micro-USB from a workbench USB power supply or USB port (5V/2A minimum)
- Wait approximately 10 minutes for first-boot filesystem expansion and automatic reboot
- Find the eRVin IP address on the home network — check router DHCP table or use Fing app on Pixel
- Reserve a static IP for the RV Pi in the home router DHCP settings based on Pi WiFi MAC address
- Access the eRVin dashboard at the reserved IP in Chrome on a Pixel
- Verify the dashboard loads — note that RV-C data will not appear yet (no CAN bus connected at this stage — expected)
- Check whether the eRVin image supports read-only overlay filesystem — document the finding and enable if available
- Document the confirmed static IP address

**Joseph does:**
Power the Pi via micro-USB on the workbench. Wait for first boot. Find IP address. Reserve static IP in home router. Access eRVin dashboard in Chrome. Check overlay filesystem option. Report static IP and dashboard status.

**Joseph confirms:**
First boot successful. Dashboard accessible. Static IP reserved. Report the IP address. Report overlay filesystem status (supported/enabled or not available).

**Claude Code does:**
Update first-boot.md and pican2-config.md with confirmed static IP. Update bill-of-materials.md with confirmed eRVin version. Document overlay filesystem decision.

---

## Step 7 — eRVin Lexor FL Configuration File

**Claude Code does:**
Create `components/p-w-firefly/ervin-configuration.md` covering:

- Log into eRVin dashboard at reserved IP
- Navigate to the configuration/setup section of the eRVin interface
- Locate the Pleasure-Way Lexor FL configuration file on myervin.com
- Download the configuration file
- Install the configuration file via the eRVin dashboard interface
- What the configuration file does: maps Firefly RV-C device IDs to named entities specific to the Lexor FL layout (tank sensors, light circuits, awning, generator, etc.)
- Verify the configuration loaded correctly — named entities should appear in the dashboard

**Joseph does:**
Follow ervin-configuration.md to locate, download, and install the Lexor FL configuration file via the eRVin dashboard.

**Joseph confirms:**
Configuration file installed. Named entities visible in dashboard. Report eRVin configuration file version/date if shown.

**Claude Code does:**
Update ervin-configuration.md with confirmed configuration file version and any deviations.

---

## Step 8 — WiFi Auto-Hotspot Configuration

**Claude Code does:**
Create `components/p-w-firefly/wifi-setup.md` covering:

**SSH access from Windows:**
- Use Windows Terminal or PuTTY to SSH into RV Pi: `ssh pi@<reserved-IP>`
- Default eRVin SSH credentials — check myervin.com documentation for current defaults

**Install RaspberryConnect Auto WiFi Hotspot Switch (Direct Connection variant):**
- Full command sequence from raspberryconnect.com for the Direct Connection variant
- This variant joins known networks when available and creates its own hotspot when not — no internet sharing required
- Document exact commands — do not paraphrase

**Configure known networks:**
- Home WiFi is already pre-loaded from Step 4
- Add Joseph's Pixel 10 Pro hotspot as a second known network (SSID and password)
- Priority order: home WiFi first, Pixel hotspot second

**Configure fallback hotspot:**
- SSID: `JCT-RV`
- Password: Joseph to choose and document in `components/p-w-firefly/secrets.md` (gitignored — confirm .gitignore before entering password)
- Static IP when in hotspot mode: `192.168.4.1`
- Enable service to run at boot

**Joseph does:**
SSH into RV Pi. Follow wifi-setup.md to install and configure auto-hotspot script. Configure both known networks. Configure JCT-RV fallback hotspot. Enable at boot.

**Joseph confirms:**
Auto-hotspot installed and configured. Both known networks added. JCT-RV hotspot configured.

**Testing — Joseph does:**
- Reboot Pi — verify it connects to home WiFi (check router for active DHCP lease at reserved IP)
- Temporarily move Pi out of home WiFi range or disable home WiFi SSID on router
- Verify JCT-RV hotspot SSID appears within 60 seconds
- Connect Joseph's Pixel to JCT-RV — verify eRVin dashboard accessible at 192.168.4.1 in Chrome
- Connect Robin's Pixel 7 to JCT-RV — verify dashboard accessible
- Re-enable home WiFi — verify Pi switches back to home network within 60 seconds
- Add JCT-RV to both Pixels as a saved network with auto-connect enabled

**Joseph confirms:**
Auto-hotspot switchover verified in both directions. Both Pixels connected to JCT-RV and dashboard confirmed accessible. Both Pixels have JCT-RV saved as auto-connect network.

**Claude Code does:**
Update wifi-setup.md with any deviations. Note actual switchover times observed.

---

## Step 9 — Tailscale Setup

**Claude Code does:**
Create `components/p-w-firefly/tailscale-setup.md` covering:

- SSH into RV Pi
- Install Tailscale on RV Pi:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

- Authenticate RV Pi to the existing JCTsh Tailscale account — follow the URL shown in terminal
- Verify Tailscale is running: `tailscale status`
- Note the RV Pi's assigned Tailscale IP address
- Verify home Pi (`100.70.162.24`) and RV Pi both appear in Tailscale admin console
- Test connectivity from RV Pi: `ping 100.70.162.24`
- Test reverse: from home Pi, ping RV Pi Tailscale IP
- Verify eRVin dashboard accessible from Pixel browser at RV Pi Tailscale IP (simulates remote access from outside home network)
- Document RV Pi Tailscale IP

**Joseph does:**
SSH into RV Pi. Install Tailscale. Authenticate to existing JCTsh account. Run connectivity tests in both directions. Access dashboard via Tailscale IP from Pixel. Report RV Pi Tailscale IP.

**Joseph confirms:**
Tailscale installed. RV Pi authenticated to JCTsh account. Both Pis visible in Tailscale console. Ping successful in both directions. Dashboard accessible via Tailscale IP. Report confirmed Tailscale IP.

**Claude Code does:**
Update tailscale-setup.md with confirmed RV Pi Tailscale IP. Update root CLAUDE.md Tailscale section to add RV Pi entry with its Tailscale IP.

---

## Bench Phase Complete — Install Phase Begins

All bench steps above are confirmed complete. The assembled unit has been:
- Hardware assembled: Pi 3B+ + PiCAN2 HAT + Geekworm case, JP3 jumper absent confirmed
- eRVin image flashed to on-hand MicroSD with home WiFi pre-loaded
- PiCAN2 driver configuration applied to boot partition
- First boot on home network confirmed, static IP reserved
- eRVin Lexor FL configuration file installed, named entities visible
- WiFi auto-hotspot configured: home WiFi → Pixel hotspot → JCT-RV fallback
- Hotspot switchover tested in both directions, both Pixels confirmed working
- Tailscale installed and verified, RV Pi authenticated to JCTsh account

**Do not proceed to Step 10 until all bench steps above are confirmed complete.**

---

## INSTALL PHASE

All steps in this section require the assembled unit to be in the Pleasure-Way Lexor FL.

---

## Step 10 — Physical RV Installation

**Claude Code does:**
Create `components/p-w-firefly/physical-installation.md` covering:

**Safety precautions:**
- Switch off coach power at the LCD panel power switch before any wiring
- Confirm Pi unit is powered off before connecting to coach 12V
- Connect 3M connector to Firefly Net Port with coach power off — then power on

**Locating the Firefly Gx panel:**
- Lift the rear seat cushion of the 2018 Pleasure-Way Lexor FL
- The Firefly Gx distribution panel is mounted in the electrical compartment alongside the batteries, DC load center, converter/charger, and Xantrex inverter
- The panel face has a green NET LED and one or more 3M Mini-Clamp sockets labeled "Net" or "Network"
- Identify an available (unused) Net Port socket

**Crimping the 3M Mini-Clamp drop cable:**
- Cut drop cable to length — measure from Firefly Net Port to intended Pi mounting location, add 6 inches for slack
- Strip outer jacket if using CAT5 — select one pair for CAN-H/CAN-L, one wire for ground, leave pin 2 (White) unconnected
- Wire order in 3M connector (clip blue-side up, pin 1 at left): Red (pin 1 / CAN-L), White (pin 2 / leave unconnected and tape off end), Blue (pin 3 / CAN-H), Black (pin 4 / GND)
- Use pliers to seat IDC connector — no special crimp tool required
- Verify wire seating before closing connector
- Make a minimum of 2 connectors — one for use, one spare for crimping errors

**Connecting drop cable to PiCAN2 screw terminal:**
- CAN-H: Blue wire (pin 3) → PiCAN2 CAN-H terminal
- CAN-L: Red wire (pin 1) → PiCAN2 CAN-L terminal
- GND: Black wire (pin 4) → PiCAN2 GND terminal
- White wire (pin 2, Firefly 12V bus): leave unconnected — tape off the end

**12V coach power tap:**
- Identify a 12V tap point at the DC bus or battery terminals in the rear seat compartment
- This circuit must go off when coach power is switched off at the LCD panel
- Add an inline fuse (1A or 2A) on the positive wire close to the tap point
- Connect 12V+ (fused) to PiCAN2 +Vin screw terminal
- Connect GND to PiCAN2 GND screw terminal (can share with drop cable GND)

**Mounting the Geekworm assembly:**
- Mount inside the rear seat compartment wall
- Use velcro (preferred — non-destructive to coach) or small self-tapping screws into composite wall
- Ensure screw terminal and cable entry points remain accessible for future service
- Secure drop cable and power wires with small zip ties — no loose wires

**Connecting and powering up:**
- Plug 3M connector into available Firefly Net Port socket
- Double-check all screw terminal connections
- Switch coach power on at LCD panel
- Pi should boot — allow 60–90 seconds for boot sequence
- Confirm LED activity on PiCAN2 board

**Joseph does:**
Follow physical-installation.md. Take photos of the Firefly panel, Net Port connection, 12V tap point, and mounted Geekworm assembly for documentation.

**Joseph confirms:**
Physical installation complete. Pi boots from coach 12V. Report any deviations — connector locations found, Net Port socket used, 12V tap point used, mounting method used.

**Claude Code does:**
Update physical-installation.md with confirmed installation details and any deviations.

---

## Step 11 — RV-C Connectivity Verification

**Claude Code does:**
Create `components/p-w-firefly/rvc-verification.md` covering:

**SSH into RV Pi:**
- If parked at home: SSH via home network reserved IP
- If on JCT-RV hotspot: SSH via 192.168.4.1
- If on Tailscale: SSH via RV Pi Tailscale IP

**Verify can0 interface is up:**
```bash
ip link show can0
```
Expected: interface listed with state UP

**If can0 is not up, bring it up manually:**
```bash
sudo ip link set can0 up type can bitrate 250000
```

**Capture RV-C traffic:**
```bash
candump can0
```
Expected: stream of CAN frames — confirms physical connection to Firefly network is working. Example output format:
```
can0  18EF4644   [8]  01 00 00 00 00 00 FF FF
can0  19FCA644   [8]  7D 7D 7D 7D FF FF FF FF
```
If no output: check wiring, confirm JP3 jumper is absent, confirm bitrate is 250000

**Verify eRVin dashboard shows live Firefly data:**
- Open eRVin dashboard in Chrome on Pixel
- Confirm live data appearing — tank levels, battery voltage, light states
- Spot check: turn a light on from the Vegatouch panel, confirm it appears ON in eRVin dashboard
- Turn the same light off, confirm dashboard updates
- Check tank level readings against known state

**Document sample candump output:**
- Copy several lines of candump output for the component documentation record

**Joseph does:**
SSH into RV Pi. Run ip link and candump commands. Verify eRVin dashboard shows live data. Perform spot checks. Report candump output sample and dashboard status.

**Joseph confirms:**
RV-C traffic confirmed on candump. Dashboard showing live Firefly data. Spot checks pass. Report any entities that appear missing or reading incorrectly.

**Claude Code does:**
Update rvc-verification.md with actual candump output sample. Document any missing or incorrect entities for follow-up.

---

## Step 12 — Full System Testing

**Claude Code does:**
Create `components/p-w-firefly/testing.md` with the complete validation checklist:

**Hardware and RV-C tests:**
- [ ] Pi boots from coach 12V power
- [ ] can0 interface comes up automatically at boot (no manual bring-up needed)
- [ ] candump can0 shows RV-C traffic
- [ ] eRVin dashboard loads and shows live Firefly data
- [ ] Fresh water tank level reads correctly
- [ ] Gray water tank level reads correctly
- [ ] Black water tank level reads correctly
- [ ] Coach battery voltage / state of charge reads correctly
- [ ] Shore power connected status correct
- [ ] Inverter status correct
- [ ] Light circuits respond to on/off commands from dashboard
- [ ] Generator start/stop works from dashboard (use with caution)
- [ ] Awning extend/retract works from dashboard
- [ ] Water pump on/off works from dashboard

**Network — Scenario 1 (home WiFi):**
- [ ] Pi connects to home WiFi automatically on boot
- [ ] eRVin dashboard accessible from Joseph's Pixel on home WiFi
- [ ] eRVin dashboard accessible from Robin's Pixel on home WiFi
- [ ] eRVin dashboard accessible from Windows PC browser on home network

**Network — Scenario 2 (Pixel hotspot / Tailscale):**
- [ ] Disable home WiFi on router — Pi switches to Pixel hotspot within 60 seconds
- [ ] Tailscale tunnel established
- [ ] eRVin dashboard accessible via Tailscale IP from Pixel
- [ ] Home Pi can ping RV Pi via Tailscale IP
- [ ] Re-enable home WiFi — Pi switches back to home network

**Network — Scenario 3 (JCT-RV fallback hotspot):**
- [ ] Disable home WiFi and turn off Pixel hotspot
- [ ] JCT-RV hotspot SSID appears within 60 seconds
- [ ] Joseph's Pixel connects to JCT-RV automatically
- [ ] Robin's Pixel connects to JCT-RV automatically
- [ ] eRVin dashboard accessible at 192.168.4.1 from both Pixels
- [ ] All coach controls functional in this mode

**Android home screen shortcuts:**
- [ ] Add eRVin dashboard to Joseph's Pixel home screen (Chrome → ⋮ → Add to Home Screen)
- [ ] Add eRVin dashboard to Robin's Pixel home screen
- [ ] Shortcut opens dashboard correctly in both network scenarios

**Joseph does:**
Work through the full testing checklist systematically in the coach. Report pass/fail for each item and any anomalies.

**Joseph confirms:**
Testing complete. Report any failed items.

**Claude Code does:**
Update testing.md with actual results. Create a troubleshooting section for any failed items and their resolutions.

---

## Step 13 — Permanent MicroSD Swap

**Claude Code does:**
Create `components/p-w-firefly/microsd-swap.md` covering:

- Confirm SanDisk MAX Endurance 32GB card is on hand before beginning
- SSH into RV Pi and note current eRVin version and confirmed configuration state
- Switch off coach power at LCD panel
- Remove on-hand MicroSD card from Pi
- Reflash SanDisk MAX Endurance card with eRVin image — repeat Steps 4 and 5 exactly
- Pre-load home WiFi credentials again (same as Step 4)
- Edit config.txt on boot partition again (same as Step 5)
- Insert SanDisk MAX Endurance card into Pi
- Switch on coach power
- Verify first boot on new card — repeat Step 6 abbreviated (static IP should be same, eRVin configuration file needs reinstalling per Step 7)
- Run abbreviated RV-C verification (Step 11) — confirm candump shows traffic and dashboard shows live data
- Check overlay filesystem option again on new card — enable if available
- Note: Tailscale authentication may not persist across card swap — re-authenticate if needed (Step 9 abbreviated)

**Joseph does:**
Follow microsd-swap.md to install the permanent SanDisk MAX Endurance card and verify full operation.

**Joseph confirms:**
Permanent card installed and verified. All systems operational. Report whether Tailscale re-authentication was required.

**Claude Code does:**
Update microsd-swap.md with actual procedure findings including Tailscale re-authentication outcome.

---

## Step 14 — README and Final Housekeeping

**Claude Code does:**
Create `components/p-w-firefly/README.md` as the permanent component reference. Use the garage-radar README as the closest structural model. Include:

- Component overview and purpose
- Vehicle details: 2018 Pleasure-Way Lexor FL, Ram ProMaster 3500, VIN 3C6URVJG9JE113400
- Coach control system: Firefly Integrations Vegatouch, RV-C protocol over CAN bus
- Hardware table with all components and part numbers
- PiCAN2 screw terminal wiring table
- 3M Mini-Clamp connector wiring table (all four pins, with pin 2 White not connected noted)
- Physical installation location: Firefly Gx panel Net Port, rear seat compartment
- Network architecture: all three scenarios with access URLs
- WiFi configuration: priority order, hotspot SSID JCT-RV
- Tailscale IP (confirmed in Step 9)
- eRVin dashboard access URLs for each scenario
- Coach systems accessible via dashboard (as confirmed in testing)
- Known behaviors and limitations
- Power loss behavior: abrupt cutoff via LCD panel switch, SanDisk MAX Endurance card, overlay filesystem status
- Storage behavior: Pi unpowered when coach power off — expected and correct
- Future enhancement: smart home integration (deferred — see Future Enhancement section above)
- Build document index listing all files in component directory

**Also complete the following final housekeeping:**
1. Update root `README.md` — change `p-w-firefly` entry from "(in progress)" to complete with full description
2. Update `jctsh-parts-inventory.md` inventory update log — Pi 3B+ ×1 consumed, Geekworm case ×1 consumed
3. Update root `CLAUDE.md` — add RV Pi to infrastructure table and Tailscale section with confirmed Tailscale IP
4. Update `ENVIRONMENT.md` — expand the RV section with Firefly interface details, eRVin dashboard URLs for each network scenario, and confirmed Tailscale IP

**Joseph confirms:**
README accurate and complete. All four housekeeping files updated correctly.

---

## Notes for Claude Code

- **This is not an ESP32/ESPHome component.** Do not apply ESP32, ESPHome, MQTT account creation, heartbeat, watchdog, or Node-RED flow standards from JCTsh-Build-Standards.md to this component. Those standards apply only to the future smart home integration phase.
- **Read CLAUDE.md and ENVIRONMENT.md first** to understand existing infrastructure before creating any files. The home Pi runs at `raspberrypi.local` / `192.168.1.117` / Tailscale `100.70.162.24`. Do not confuse home Pi and RV Pi.
- **Follow existing component conventions** for file naming, directory structure, and documentation style. Garage-radar README is the closest structural model for the component README.
- **RV-C bitrate is 250kbps — not 500kbps.** Document this prominently in pican2-config.md and rvc-verification.md. Wrong bitrate produces no CAN traffic and is the most common setup error.
- **JP3 termination jumper must NOT be installed.** Connecting as a Drop, not a Trunk endpoint. Document this warning in hardware-assembly.md and physical-installation.md. Installing it disrupts the entire Firefly RV-C bus.
- **eRVin image owns the RV Pi.** Do not attempt to install additional software that conflicts with the eRVin image without first researching compatibility at myervin.com.
- **Tailscale account is the existing JCTsh account.** Do not create a new account. RV Pi joins the same account as the home Pi at `100.70.162.24`.
- **Static IP reservation.** Document the confirmed reserved IP in first-boot.md and reference it consistently in every subsequent step requiring SSH access.
- **Bench power for Steps 6–9.** Power the Pi via micro-USB directly for all bench steps. Do not connect the PiCAN2 screw terminal to anything during bench work. The screw terminal is wired to coach 12V only during Step 10 (physical installation).
- **Secrets file.** `components/p-w-firefly/secrets.md` contains the JCT-RV hotspot password. Confirm this file is in `.gitignore` before Joseph enters any credentials. Follow the same gitignore pattern as other components.
- **Vehicle VIN is 3C6URVJG9JE113400.** Include in README and physical-installation.md.
- **Power switch clarification.** The LCD panel power switch cuts coach power for storage. The red battery disconnect key prevents solar charging during near-freezing weather only — it is NOT used for routine storage. Document this distinction correctly in physical-installation.md and README.
- **3M connector pin 2 (White wire) is the Firefly 12V bus supply.** It must NOT be connected to the PiCAN2. Tape off the end. Document clearly in hardware-assembly.md and physical-installation.md.
- **Bench/install boundary.** Enforce strictly — do not proceed to Step 10 until Joseph confirms all of Steps 1–9 are complete.
- **Do not proceed to the next step until Joseph confirms the current step is complete.**
- **Update documentation immediately when Joseph reports deviations.** Do not defer documentation updates to a later step.
