# JCTsh Parts Inventory
**Author:** Joseph C Thomas (JCT)
**Purpose:** On-hand parts inventory for JCTsh smart home component projects. Update quantities after each project build.
**Version:** 1.0
**Version description:** Initial release. Populated from garage radar and salt sensor project builds.
**Project:** JCTsh — Smart Home Automation
**Related files:** README.md, JCTsh-Component-Planning-Pattern.md

---

## Enclosure Convention

Open standoff mount is the default first option for ESP32 and small PCB projects. No enclosure panels. The perfboard (or dev board) is mounted vertically using M3 brass male-female standoffs, which space the board away from the mounting surface for cable clearance and serve as the attachment points. This approach suits the workshop environment, is inexpensive, reusable across projects, and keeps components accessible.

An acrylic lid panel (cut to perfboard footprint, held by the same standoffs) may be added as a future enhancement if dust accumulation becomes an issue. A full enclosure box (e.g., project box) is reserved for components that require weather resistance or a finished appearance outside the workshop.

---

## Microcontrollers

| Component | Description | Qty On Hand | Notes |
|---|---|---|---|
| ESP32 DevKitC-32 | hiBCTR 6-pack, 38-pin, CP2102 USB-C, WiFi+BT | 4 | 1 used: garage radar. 1 allocated: front porch sensor (in planning). |
| ESP32 (salt sensor) | Separate board, not from 6-pack | 1 (deployed) | Deployed on salt sensor project. |

---

## Single-Board Computers

| Component | Description | Qty On Hand | Notes |
|---|---|---|---|
| Raspberry Pi 3B+ | Element14 | 1 | Allocated to upcoming RV project. |

---

## Sensors

| Component | Description | Qty On Hand | Notes |
|---|---|---|---|
| HLK-LD2412 | EC Buying, 24GHz mmWave radar, UART, ±75°, 9m range | 2 | 1 used: garage radar project. |
| BH1750 (GY-302) | hiBCTR 3-pack, illumination/light sensor, I2C | 3 | All on hand. No project assigned yet. |
| BME280 | Podazz 3-pack, temperature/humidity/pressure, I2C, 5V | 6 | 2 packs (6 total) on hand. No project assigned yet. |

---

## Power Components

| Component | Description | Qty On Hand | Notes |
|---|---|---|---|
| 18650 Battery Charger Module + Holder | AEDIKO 5-pack (charger + holder pairs), fast charge boost, PCB protection | 10 | 2 packs (10 pairs) on hand. No project assigned yet. |
| Mini Solar Panel | SUNYIMA, 5.5V 80mA, 2.36"×2.36", DIY photovoltaic | 10 | All on hand. No project assigned yet. |

---

## Prototyping and Build Hardware

| Component | Description | Qty On Hand | Notes |
|---|---|---|---|
| Perfboard | Chanzon 34-pack, FR4 double-sided tinned through-holes, 5 sizes: 2×8, 3×7, 4×6, 5×7, 7×9 cm, 2.54mm pitch, corner mounting holes | ~33 | 1 used: garage radar project. 5×7cm boards recommended for ESP32 projects. |
| Female Pin Header Strips | Glarks 120-pack, 2.54mm single row, sizes: 2–40 pin, storage box | Selection on hand | Not tracked by count. Check inventory before planning a project to confirm selection covers requirements. 40-pin strips can be cut to any length. |
| M3 Brass Standoff Kit | ZYAMY 150-pack, M3 only, female-female 6/10mm, male-female 6+6/10+6/15+6mm, M3 nuts and M3×6 screws | Selection on hand | Not tracked by count. Check inventory before planning a project to confirm sizes needed are available. Default mounting hardware for ESP32 perfboard projects — see Enclosure Convention above. |
| Breadboards | 4-pack: 2×830 point, 2×400 point, solderless | 4 | Used for prototyping only — freed up when project moves to perfboard. Not tracked by quantity. |

---

## LEDs and Resistors

| Component | Description | Qty On Hand | Notes |
|---|---|---|---|
| 5mm LED Assortment | 200pcs, 5 colors (red, green, yellow, blue, white), 40 of each color | Selection on hand | Not tracked by count. Check inventory before planning a project. Green and yellow confirmed available for ESP32 status indicators. |
| Resistor Assortment | 600pcs, 30 values, 10Ω to 1MΩ, 20 of each value | Selection on hand | Not tracked by count. Check inventory before planning a project. 330Ω confirmed available for LED current limiting at 3.3V. |

---

## Enclosures and Cases

| Component | Description | Qty On Hand | Notes |
|---|---|---|---|
| Geekworm Pi HAT Case | Universal HAT size, acrylic, fits Pi 5/4B/3B+/3B/2B/B+ and HAT expansion boards | 1 | Allocated to upcoming RV project. Not suitable for ESP32 DevKit (different footprint and mounting holes). |

---

## Inventory Update Log

| Date | Project | Change |
|---|---|---|
| 2026-05 | Garage radar | ESP32 ×1 used; LD2412 ×1 used; perfboard ×1 used |