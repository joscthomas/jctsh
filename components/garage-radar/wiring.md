# Garage Radar — Wiring & Breadboard Assembly

## Connection Table

| LD2412 Pin | ESP32 Pin       | Notes |
|---|-----------------|---|
| 5V | 5V (VIN) pin 19 | Module has onboard regulator — requires 5V input, not 3.3V |
| GND | GND             | Any GND pin on the ESP32 |
| TX | GPIO16 (RX2)    | LD2412 **transmits** → ESP32 **receives** |
| RX | GPIO17 (TX2)    | ESP32 **transmits** → LD2412 **receives** |

> **Power note:** The LD2412 module uses an onboard 5V→3.3V regulator. Power it from
> the ESP32 5V (VIN) pin, which is connected to USB 5V when the ESP32 is powered via USB.
> The UART TX/RX lines operate at 3.3V logic despite the 5V supply — no level shifter
> is needed for GPIO16/17.

> **TX/RX warning — most common wiring error:**
> TX and RX labels are from the perspective of each device.
> LD2412 TX goes to ESP32 RX (GPIO16). LD2412 RX goes to ESP32 TX (GPIO17).
> Swapping these is the #1 wiring mistake — the radar will not communicate.
> Label both ends of each wire before assembling.

---

## ESP32 DevKitC-32 38-Pin Layout Reference

The 38-pin ESP32 DevKitC straddles the breadboard center channel with 19 pins per side.
Place it so the USB-C port faces one end of the breadboard.

```
                    USB-C
                   ┌─────┐
             3.3V  │ •   │  GND
              GND  │ •   │  GPIO13
             GPIO15│ •   │  GPIO12
              GPIO2│ •   │  GPIO14
              GPIO4│ •   │  GPIO27
              GPIO5│ •   │  GPIO26
             GPIO18│ •   │  GPIO25
             GPIO19│ •   │  GPIO33
             GPIO21│ •   │  GPIO32
             GPIO3 │ •   │  GPIO35
              RXD0 │ •   │  GPIO34
              TXD0 │ •   │  GPIO39
             GPIO22│ •   │  GPIO36
             GPIO23│ •   │  GPIO23
         GPIO16/RX2│ •   │  GPIO1
         GPIO17/TX2│ •   │  GPIO3
             GPIO5 │ •   │  EN
              GPIO5│ •   │  GND
              5V   │ •   │  VIN
                   └─────┘
```

> **Note:** Pin numbering varies slightly between ESP32 DevKit breakouts.
> Before wiring, verify GPIO16 and GPIO17 locations on your specific board using
> the silk-screen labels. GPIO16 is labeled **RX2** and GPIO17 is labeled **TX2**
> on most DevKitC-32 boards. See `ESP32pins.png` in this directory for the full pinout.

---

## Breadboard Assembly

### What you need
- Breadboard (standard 830-tie or half-size 400-tie)
- ESP32 DevKitC-32 (38-pin)
- HLK-LD2412 module
- 4 jumper wires (use different colors: red=VCC, black=GND, green=TX→RX, yellow=RX→TX)
- USB-C cable for power and first flash

### Assembly sequence

**1. Place the ESP32**
Insert the ESP32 straddling the breadboard center channel. The USB-C port can face
either end. Press firmly until all pins are seated. The board will use nearly the
full width of a standard breadboard.

**2. Place the LD2412**
Place the LD2412 module in an open area of the breadboard, away from the ESP32.
Leave enough space to route 4 wires cleanly.

**3. Wire power first**
- Red wire: LD2412 5V → ESP32 5V (VIN) pin
- Black wire: LD2412 GND → ESP32 GND pin (or ground rail)

**4. Wire UART**
- Green wire: LD2412 TX → ESP32 GPIO16 (RX2)
- Yellow wire: LD2412 RX → ESP32 GPIO17 (TX2)

**5. Visual verification before powering on**
Before connecting USB, verify:
- [ ] LD2412 5V is connected to ESP32 5V (VIN) pin
- [ ] LD2412 GND is connected to ESP32 GND
- [ ] LD2412 TX is connected to GPIO16 (labeled RX2)
- [ ] LD2412 RX is connected to GPIO17 (labeled TX2)
- [ ] No wires crossed between TX and RX on the same device

---

## LD2412 Module Pin Locations

The LD2412 module has a row of pads/pins along one edge. The four pins used are
typically labeled on the module silkscreen:

| Label on module | Connect to |
|---|---|
| 5V | ESP32 5V (VIN) |
| GND | ESP32 GND |
| TX | ESP32 GPIO16 (RX2) |
| RX | ESP32 GPIO17 (TX2) |

> **If your module has additional pins** (e.g., OUT, IO1, IO2): leave them unconnected
> for this build. Only VCC, GND, TX, and RX are used.

---

## Do not flash yet

Complete breadboard assembly and visual verification first. Flashing instructions
are in `flashing.md` (Step 3).
