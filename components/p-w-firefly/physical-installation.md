# Physical RV Installation — Pleasure-Way Firefly Interface

Install the assembled Pi unit in the 2018 Pleasure-Way Lexor FL (RAM ProMaster 3500, VIN 3C6URVJG9JE113400) and connect it to the Firefly RV-C network and coach 12V power.

---

## Safety Precautions

- **Switch off coach power at the LCD panel power switch before any wiring.** The LCD panel switch cuts the 12V bus — all wiring must be done with the coach powered off.
- Confirm the Pi unit is powered off before connecting it to coach 12V.
- Do not connect the Firefly Net Port until all wiring is complete and inspected.
- The red battery disconnect key is NOT the coach power switch — it is used only to prevent solar charging in near-freezing weather. Do not use it for installation power control.

---

## Locating the Firefly Gx Panel

1. Lift the rear seat cushion of the 2018 Pleasure-Way Lexor FL
2. The Firefly Gx distribution panel is mounted in the electrical compartment alongside the batteries, DC load center, converter/charger, and Xantrex inverter
3. The panel face has a green NET LED and one or more 3M Mini-Clamp sockets labeled "Net" or "Network"
4. Identify an available (unused) Net Port socket for the drop cable connection

---

## Crimping the 3M Mini-Clamp Drop Cable

### Wire selection — CAT5 pair assignment

**Do this before cutting the cable.**

CAN-H and CAN-L must run on the **same twisted pair**. The twist cancels common-mode noise that affects both wires equally — splitting them across different pairs loses that noise rejection.

Standard CAT5 pairs and their colors:
| Pair | Colors |
|---|---|
| Pair 1 | Blue / Blue-White |
| Pair 2 | Orange / Orange-White |
| Pair 3 | Green / Green-White |
| Pair 4 | Brown / Brown-White |

**Recommended assignment for this build:**
- **CAN-H and CAN-L** — use one solid-color wire and its striped partner from the same pair (e.g. Orange and Orange-White, or Green and Green-White)
- **GND** — any remaining wire from a different pair

Pin 2 is left empty regardless of cable used.

### Confirmed Firefly Net Port pinout

Measured directly at the Firefly Net Port socket with a multimeter:

| Pin | Signal | Voltage |
|---|---|---|
| 1 | 12V bus power — **do NOT connect** | 12V |
| 2 | CAN-H | ~2.5V |
| 3 | CAN-L | ~2.5V |
| 4 | GND | 0V |

### Wire order in 3M connector — clip blue-side up, pin 1 at left

| Pin | Function | Connect to |
|---|---|---|
| 1 | 12V — **leave empty** | — |
| 2 | CAN-H | PiCAN2 CAN-H screw terminal |
| 3 | CAN-L | PiCAN2 CAN-L screw terminal |
| 4 | GND | PiCAN2 GND screw terminal |

### Procedure

1. Measure from the Firefly Net Port to the intended Pi mounting location — add 6 inches for slack. Cut the drop cable to this length.
2. Do not strip the wires — the 3M Mini-Clamp is an IDC connector. Insert wires with insulation intact; the IDC blades cut through on closing.
3. Insert wires into the 3M 37104-A165-00E connector in the order above (clip blue-side up, pin 1 at left). Leave pin 2 empty.
4. Press the connector cap firmly with pliers to seat the IDC blades — no special crimp tool required. Verify each wire is fully seated before fully closing.
5. Make a minimum of 2 connectors — one for use, one spare in case of a crimping error.

---

## Connecting the Drop Cable to the PiCAN2 Screw Terminal

| PiCAN2 Screw Terminal | Wire | 3M Pin |
|---|---|---|
| CAN-H | TBD — from same twisted pair | 2 |
| CAN-L | TBD — from same twisted pair | 3 |
| GND | TBD | 4 |
| +Vin | 12V coach power wire (next section) | — |

---

## 12V Coach Power Tap

1. Identify a 12V tap point at the DC bus or battery terminals in the rear seat compartment. **This circuit must go off when coach power is switched off at the LCD panel** — verify this before committing to the tap point.
2. Add an inline fuse (1A or 2A) on the positive wire, placed close to the tap point.
3. Connect the fused positive wire to the PiCAN2 **+Vin** screw terminal.
4. Connect GND to the PiCAN2 **GND** screw terminal — this can share with the drop cable GND.

---

## Mounting

1. Mount the Geekworm assembly inside the rear seat compartment wall.
2. **Preferred method:** Velcro — non-destructive to the coach. Alternatively, small self-tapping screws into composite wall.
3. Orient the unit so the screw terminal and cable entry points remain accessible for future service.
4. Secure the drop cable and power wires with zip ties — no loose wires.

---

## Connecting and Powering Up

1. Plug the 3M connector into the available Firefly Net Port socket.
2. Double-check all screw terminal connections — confirm correct wires, confirm pin 2 is empty.
3. Confirm JP3 termination jumper is absent on the PiCAN2. **Do not install JP3** — connecting as a Drop, not a Trunk endpoint. The Firefly network already has two termination resistors; a third disrupts the RV-C bus.
4. Switch coach power on at the LCD panel.
5. Pi should boot — allow 60–90 seconds for the boot sequence.
6. Confirm LED activity on the PiCAN2 board.
7. Verify WiFi: wait 2 minutes, then check whether the Pi appears on the home network at `192.168.1.219` (if the RV is parked at home) or whether the JCT-RV hotspot SSID is visible (if away from home).

---

## Troubleshooting — No CAN Traffic

If Step 11 (`candump can0`) shows no output:

1. **Check pair assignment first** — if CAN-H and CAN-L are on different twisted pairs, noise rejection is reduced. Rewire them onto the same pair (see Wire selection above) and retest before investigating anything else.
2. Check that the 3M connector is fully seated in the Firefly Net Port socket.
3. Confirm can0 is up: `ip link show can0` — bring up manually if needed: `sudo ip link set can0 up type can bitrate 250000`
4. Confirm JP3 jumper is absent on the PiCAN2.
5. Confirm bitrate is 250000 (RV-C spec) — not 500000.

---

## Confirmed Details

*(Step 10 confirmed complete)*

| Item | Value |
|---|---|
| Firefly Net Port socket used | Net port on the 12V power panel under the rear seat |
| 12V tap point | Unused wire on the 12V power panel under the rear seat |
| Drop cable length | ~3 feet |
| Mounting method | Velcro on case bottom — planned mount under 12V panel, off to the side; deferred until RV-C connectivity confirmed |
| Pi boots from coach power | Yes — micro-USB from coach USB power outlet |
| Power method | Micro-USB (coach USB outlet) — PiCAN2 SMPS non-functional (0V on GPIO 5V pins, no visible damage; bench steps always used micro-USB so SMPS was never tested) |
| CAN-H/CAN-L wiring confirmed | Orange (pin 1) → CAN-L, Blue (pin 3) → CAN-H, Brown (pin 4) → GND; CAN-H and CAN-L on different CAT5 pairs |
| JP3 jumper absent confirmed | Yes |
| eRVin dashboard accessible | Yes — http://192.168.1.219 |
