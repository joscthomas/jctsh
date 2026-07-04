# JCTsh Parts Inventory
**Author:** Joseph C Thomas (JCT)
**Purpose:** On-hand parts inventory for JCTsh smart home component projects. Update quantities after each project build.
**Version:** 2.7
**Version description:** Corrected EEMB LiPo (Bag 7) remaining count to 2 via physical recount after the hiking-monitor battery swap (2026-07-03). Added LiPo Fireproof Charging Bag (ordered) per JCTsh-Build-Standards.md §2.14.
**Project:** JCTsh — Smart Home Automation
**Related files:** README.md, JCTsh-Component-Planning-Pattern.md

---

## Location Key

| Location           | Description                                                                                                                   |
|--------------------|-------------------------------------------------------------------------------------------------------------------------------|
| Box Label          | Plastic storage box with a label (like "Arduino") — houses Pi Zero W kit, other computing devices, and associated accessories |
| Bag N              | Numbered zip-lock or parts bag; label bag with number to match this inventory                                                 |
| Shelf              | Workshop shelf — larger or allocated items not yet deployed                                                                   |
| Bench              | Primary work surface / soldering station area                                                                                 |
| Music Response bin | Plastic storage bin labeled "Music Response" — houses discrete components and supplies for the music response project         |
| Deployed           | Installed in a live JCTsh component; not on hand                                                                              |

---

## Enclosure Convention

Open standoff mount is the default first option for ESP32 and small PCB projects. No enclosure panels. The perfboard (or dev board) is mounted vertically using M3 brass male-female standoffs, which space the board away from the mounting surface for cable clearance and serve as the attachment points. This approach suits the workshop environment, is inexpensive, reusable across projects, and keeps components accessible.

An acrylic lid panel (cut to perfboard footprint, held by the same standoffs) may be added as a future enhancement if dust accumulation becomes an issue. A full enclosure box (e.g., project box) is reserved for components that require weather resistance or a finished appearance outside the workshop.

---

## Servers & Mini PCs

| Component | Description | Qty | Location | Notes |
|---|---|---|---|---|
| GMKtec NucBox M8 | AMD Ryzen 5 PRO 6650H (6C/12T, 4.5GHz), 16GB LPDDR5, Netac 512GB NVMe SSD, dual Realtek 2.5GbE, RZ616 Wi-Fi 6E, USB4, OCuLink. Model: M8-5-33S. Serial: MB261801199. Windows 11 Pro OEM (BIOS-embedded key: QXNC8-CBB7V-2FMDW-FVXX7-XD8GG). Purchased 2026-07 Amazon Prime Day. | 1 | Shelf | Allocated: photo-server. OS to be replaced with Ubuntu Server LTS (per photo-server-claude-code-instructions.md Step 1). |

---

## Microcontrollers

| Component           | Description                                  | Qty | Location | Notes                                                                         |
|---------------------|----------------------------------------------|-----|----------|-------------------------------------------------------------------------------|
| ESP32 DevKitC-32    | hiBCTR 6-pack, 38-pin, CP2102 USB-C, WiFi+BT | 2   | Bag 1    | 1 used: garage radar. 1 used: front-porch-temp-sensor. 1 used: hiking-sensor. |
| ESP32 (salt sensor) | Separate board, not from 6-pack              | 1   | Deployed | Deployed on salt sensor project.                                              |

---

## Single-Board Computers

| Component | Description | Qty | Location | Notes |
|---|---|---|---|---|
| Raspberry Pi 3B+ |  | 1 | Shelf | Allocated as home based server for MQTT, Node-RED, and other JCTsh software components. |
| Raspberry Pi 3B+ | Element14 | 1 | Shelf | Allocated to upcoming RV project. |
| Raspberry Pi Zero W | Vilros Basic Starter Kit, ASIN B0748MPQT4. BCM2835, single-core 1GHz, 512MB RAM, 802.11b/g/n WiFi, BT 4.1, CSI camera connector. Kit includes: board, 2.5A PSU w/ inline switch, black case (3 covers), mini-HDMI adapter, micro-USB OTG adapter, 40-pin header (unsoldered), heatsink, camera module adapter cable. No SD card. | 1 | Arduino box | No project assigned. Suitable for: sensor logging (MQTT/Python), Pi-hole, lightweight single-purpose Linux tasks. Not suitable for: OpenCV/camera processing, Node-RED as primary host. Header requires soldering before GPIO use. Included PSU reported unreliable — use a known-good 5V/2.5A supply if instability occurs. |

---

## Sensors

| Component | Description | Qty | Location | Notes |
|---|---|---|---|---|
| HLK-LD2412 | EC Buying, 24GHz mmWave radar, UART, ±75°, 9m range | 1 | Bag 18 | 1 used: garage radar project. |
| BH1750 (GY-302) | hiBCTR 3-pack, illumination/light sensor, I2C | 5 | Bag 19 | 1 used: front-porch-temp-sensor. |
| BMP280 (sold as BME280) | Podazz 3-pack, counterfeit — pressure/temp only, no humidity, I2C, 5V | 2 | Bag 2 | 3 returned 2026-05-26. 2 spares removed from front-porch-temp-sensor. |
| BME280 (GY-BME280) | 2PCS packs, genuine — temp/humidity/pressure, I2C/SPI, 5V breakout | 3 | Bag 3 | 1 deployed: front-porch-temp-sensor (2026-05-26). 1 used: hiking-sensor. 2 spares. |
| LTR390 UV Light Sensor | Adafruit #4831, STEMMA QT / Qwiic I2C, UV and ambient light, 3.3V/5V. https://www.amazon.com/dp/B0BPR31P59 | 1 | Bag 22 | 1 used: hiking-sensor. 1 spare. |
| SparkFun SEN-23715 | Sensirion SEN54, particle (PM1/2.5/4/10), VOC, humidity, temperature, I2C/UART. SparkFun SEN-23715. | 1 | Plastic Box | Allocated: air-quality-monitor project. |
| Adafruit SEN54/SEN55 Adapter Breakout | STEMMA QT / Qwiic, I2C adapter breakout for Sensirion SEN54/SEN55. | 1 | Bag 25 | Allocated: air-quality-monitor project. |
| DS3231 RTC Module | HiLetgo 5pcs, high precision real time clock, I2C, 3.3V/5V, CR2032 battery backup. https://www.amazon.com/dp/B01N1LZSK3 | 5 | Bag 28 | 1 allocated: bedside-clock. |
| Greekcreit Sensor Module Kit for Arduino | Kit of 37 modules including: active/passive buzzer, LED modules (common cathode red/green, two-color, RGB, colorful auto flash), knock/shock/tilt/magnet-ring/hall/analogy hall/magnetic spring sensors, photo resistor, push button, infrared TX/RX, rotate encoder, light break sensor, finger pulse sensor, obstacle avoidance, tracking, microphone, laser TX, relay, analog/digital/18b20 temperature, flame, voice, humidity, joystick PS2, touch sensor | — | Plastic Box | |

---

## Power Components

| Component | Description | Qty | Location | Notes |
|---|---|---|---|---|
| 18650 Battery Charger Module + Holder | AEDIKO 5-pack (charger + holder pairs), fast charge boost, PCB protection | 10 | Bag 4 | No project assigned. |
| EVE 3.3V 18650 Cell | 18650BatteryStore.com, 3200mAh, 10A, flat top | 5 | Bag 5 | No project assigned. |
| Mini Solar Panel | SUNYIMA, 5.5V 80mA, 2.36"×2.36", DIY photovoltaic | 10 | Bag 6 | No project assigned. |
| LI-ION Polymer Battery | EEMB, 3.7V 1100mAh 603449, JST connector. https://www.amazon.com/dp/B08VRYS8FT — confirm polarity before use. | 3 | Bag 7 | 1 in service: hiking-sensor. Hiking-sensor's original cell failed in the field (2026-07-03) and was replaced from this stock — physical recount confirmed 2 still remaining in Bag 7 afterward; trust this physical count over prior used/remaining math. |
| TP4056 Battery Charger Modules | USB TP4056, 3.7V–4.2V to 9V/5V, 2A, charge/discharge integrated step-up. https://www.amazon.com/dp/B098989NRZ | 5 | Bag 8 | 1 used: hiking-sensor. |
| DC Buck Converter 12V→5V 3A | 2pcs, 15W, USB-C output, compatible with Raspberry Pi 4. https://www.amazon.com/dp/B0CMZWN7WS | 2 | Bag 21 | No project assigned. |
| Power Supply Module 3.3V/5V | HiLetgo, dual output 3.3V and 5V, breadboard-compatible. | 5 | Music Response bin | No project assigned. |
| 9V Battery Clips I-Type DC Plug | HiLetgo, I-type DC barrel connector. | 10 | Music Response bin | No project assigned. |
| LiPo Fireproof Charging Bag | Silicone-coated fiberglass, for safe LiPo charging/storage per JCTsh-Build-Standards.md §2.14. | 1 | Ordered (2026-07-03) | Required practice for all LiPo charging going forward — not project-specific. |

---

## Prototyping and Build Hardware

| Component | Description | Qty | Location          | Notes |
|---|---|---|-------------------|---|
| Perfboard | Chanzon 34-pack, FR4 double-sided, 5 sizes: 2×8, 3×7, 4×6, 5×7, 7×9 cm, 2.54mm pitch, corner mounting holes | ~33 | Bag 9             | 1 used: garage radar. 5×7cm recommended for ESP32 projects. |
| Female Pin Header Strips | Glarks 120-pack, 2.54mm single row, 2–40 pin, storage box | Assortment | Plastic Box       | 40-pin strips can be cut to any length. Verify selection before planning. |
| M3 Brass Standoff Kit | ZYAMY 150-pack, M3 only: female-female 6/10mm, male-female 6+6/10+6/15+6mm, M3 nuts and M3×6 screws | Assortment | Plastic Box       | Default mounting hardware for ESP32 perfboard projects. Verify selection before planning. |
| M2 Hex Brass Standoff Kit | 390 pcs, M2 male-male hexagonal threaded pillar spacers, bolts, screws, nuts assortment for PCB/circuit board mounting. https://www.amazon.com/dp/B09X346JFL | Assortment | Plastic Box       | Verify selection before build. |
| Breadboards | 2×830 point, 2×400 point, solderless | 4 | Bag 12            | Prototyping only — freed up when project moves to perfboard. |
| Push Buttons | QTEATAK, 10 values, 4-pin, 6×6mm micro momentary tact. https://www.amazon.com/dp/B07VQF8P2Y | Assortment | Plastic Box       | Verify selection before build. |
| JST SM 2-Pin Connectors | Male/female pairs, EL wire cable style. https://www.amazon.com/dp/B00T2U76V0 | Assortment | Bag 14            | Verify selection before build. |
| Pin Header JST Plug Connectors | QTEATAK, 2P/3P/4P/5P, right angle, 2.54mm pitch. https://www.amazon.com/dp/B0CH8G2XN9 | Assortment | Plastic Box       | Verify selection before build. |
| Dupont Connector Kit 2.54mm | Taiss 600pcs, 1–7 pin housing, male/female crimp pins, 2.54mm pitch. https://www.amazon.com/dp/B0B11SX39B | Assortment | Plastic Box       | Use with SN-28B crimping tool. Verify selection before build. |
| Slide Switch Assortment | Gebildet 40pcs, SS12D10 (SPDT 1P2T 3-pin, 250V/3A) and SS12F15 (mini panel SPDT 3-pin, 50V/0.5A). https://www.amazon.com/dp/B0D55ZSH8Y | Assortment | Bag 23 | Verify rating before build. |
| Wire Lever Connectors | 32Pcs Lever Wire Connectors, DIY Mini Compact Splicing Assortment Quick Electrical Connector Kit for 24-12 AWG https://www.amazon.com/dp/B0B28GQVVG | Assortment | Plastic Box       | Verify selection before build. |
| Jumper Wires | Jumper Wire Kit - 840 Piece Breadboard Jumper Wire Set, 22ga 14 Assorted Lengths for Prototyping https://www.amazon.com/dp/B07WLPN929 | Assortment | Plastic Box       | Suitable for perfboard use, but not breadboards. |
| M2 Screw Assortment | 645 pcs metric, M2 countersunk flat-head hex socket cap screws, bolts, nuts, washers, 304 stainless steel. https://www.amazon.com/dp/B0GFDQ6457 | Assortment | Plastic Box       | Verify selection before build. |
| 3M Double Sided Foam Tape | 3M 5925, 0.5" × 15.4 ft, heavy duty, 0.025" thick, black, strong adhesive for mounting. https://www.amazon.com/dp/B0CHDVNS5T | 1 roll | Plastic Box       | No project assigned. |
| 2-Pin Screw Terminal Block 3.5mm | uxcell, 50 pcs, 2-pin, 3.5mm pitch, panel/PCB mount, green. https://www.amazon.com/dp/B01C3DGIBQ | 50 | Plastic Box       | No project assigned. |
| Heat Shrink Butt Connectors 26-24 AWG | 100 pcs, insulated waterproof crimp butt splice connectors, marine/automotive grade. https://www.amazon.com/dp/B08LR7NV7M | 100 | Bag 26 | No project assigned. |
| Momentary Push Button Switch 12mm | Twidec 6pcs, PBS-33B-BK-X, 12mm, 1/2" panel mount, waterproof, pre-soldered wires, black. https://www.amazon.com/dp/B08JHW8BPV | 6 | Bag 27 | 1 allocated: bedside-clock. |

---

## Wire

| Component | Description | Qty | Location | Notes |
|---|---|---|---|---|
| Silicone Hookup Wire 24 AWG | TUOFENG, 6 colors (30ft/9m each), tinned copper, silicone rubber insulation, OD 1.6mm. https://www.amazon.com/dp/B07G2BWBX8 | 6 rolls | Shelf | Flexible; general-purpose hookup wire for perfboard builds and wiring harnesses. |
| Solid Core Hookup Wire 24 AWG | 6 colors (40ft each), tinned copper. https://www.amazon.com/dp/B0C6K5T8BW | 6 rolls | Shelf | Solid core; holds shape for point-to-point wiring and surface traces. |

---

## Cables and Adapters

| Component | Description | Qty | Location | Notes |
|---|---|---|---|---|
| USB-C to Micro USB Adapter | JXMOX 4-pack, Type-C female to Micro USB male, supports charge and data sync, grey. https://www.amazon.com/dp/B07GH5KJH2 | 4 | Bag 20 | Useful for powering or connecting Micro USB devices from USB-C sources. |
| 3M Mini-Clamp Connectors | 3M, 4-conductor. Pinout for p-w-firefly CAN bus: Red=12V+ (leave unconnected), White=CAN-H, Green/Blue=CAN-L, Black=GND. | 3 | Bag 24 | Allocated: p-w-firefly project. Do not connect Red (12V+) to PiCAN2. |
| JST GH 1.25mm Pitch 6-Pin Cable | 100mm long. | 1 | Bag 25 | Allocated: air-quality-monitor project. |

---

## Discrete Semiconductors

| Component | Description | Qty | Location | Notes |
|---|---|---|---|---|
| BC557B PNP Transistor | Diotec, PNP 45V 0.1A TO-92. DigiKey 4878-BC557BCT-ND | 10 | Music Response bin | General-purpose small-signal PNP. |
| BC547B NPN Transistor | Diotec, NPN 45V 0.1A TO-92. DigiKey 4878-BC547BCT-ND | 50 | Music Response bin | General-purpose small-signal NPN. |
| 1N4148 Signal Diode | onsemi, 100V 200mA DO-35. DigiKey 1N4148FS-ND | 50 | Music Response bin | Fast switching signal diode. |

---

## LEDs and Resistors

| Component | Description | Qty | Location | Notes |
|---|---|---|---|---|
| 5mm LED Assortment | 200pcs, 5 colors (red, green, yellow, blue, white), 40 each | Assortment | Plastic Box | 330Ω confirmed available for current limiting at 3.3V. |
| 5mm LED Assortment | Greekcreit, red/yellow/green/blue/clear assortment | Assortment | Music Response bin | No project assigned. |
| Resistor Assortment | 600pcs, 30 values, 10Ω–1MΩ, 20 each | Assortment | Bag 17 | Verify selection before planning. |
| Resistor 100Ω 1/4W | Stackpole, 1% axial. DigiKey RNF14FTD100RCT-ND | 50 | Music Response bin | Precision 1% tolerance. |
| 10K Ohm Trim Potentiometer | Flutesan kit, 10K ohm | 24 | Music Response bin | No project assigned. |

---

## Enclosures and Cases

| Component | Description | Qty | Location | Notes |
|---|---|---|---|---|
| Geekworm Pi HAT Case | Universal HAT size, acrylic, fits Pi 5/4B/3B+/3B/2B/B+ | 1 | Shelf | Allocated to upcoming RV project. Not suitable for ESP32 DevKit. |
| Pi Zero W Case | Vilros black plastic, 3 covers: closed / GPIO access / camera mount | 1 | Arduino box | Paired with Pi Zero W board. |
| Project Boxes | ABS plastic, 5-pack, 72×42×23mm (2.83×1.65×0.91 in), white | 5 | Plastic Box | Very small. |

---

## Displays

| Component | Description | Qty | Location | Notes |
|---|---|---|---|---|
| E-Ink Display | Waveshare 2.13" HAT V4, 250×122, SPI, partial refresh, compatible with Pi Zero W/2W/3B/4B/5/Pico. https://www.amazon.com/dp/B071S8HT76 | 0 | Deployed | 1 used: hiking-sensor. |
| SH1106 OLED Display 1.3" | Hosyond 5pcs, 128×64, I2C, white, SH1106 driver (not SSD1306). https://www.amazon.com/dp/B0C3L7N917 | 5 | Bag 29 | 1 allocated: bedside-clock. |

---

## Tools — Bench Equipment

| Tool | Description | Location | Notes |
|---|---|---|---|
| Soaiy Soldering Kit | Soldering station kit | Bench | Primary soldering station. |
| Power Probe Butane Soldering Kit | Portable butane-powered soldering iron | Bench | For fieldwork or when bench station is impractical. |
| Solder Sucker | Desoldering pump | Bench | |
| iCrimp SN-28B Dupont Crimping Tool | AWG 18–28, 2.54mm/2.5mm/3.96mm pitch, JST XH/VH and Dupont connectors. https://www.amazon.com/dp/B00OMM4YUY | Shelf | Use with Taiss Dupont connector kit. |
| TP88A Piercing Needle Test Probes | Non-destructive multimeter test probes, piercing needle tip. https://www.amazon.com/dp/B01LYVHFDK | Shelf | For probing insulated wires without stripping. |
| USB C Power Meter Tester | Multimeter 4.5-50V 0-12A two-way measurement, gravity sensor, voltage/current/capacity/amp/volt readout, for chargers/power banks/cables. https://www.amazon.com/dp/B0D9QH4C7S | Shelf | |

---

## Tools — Consumables

| Item | Description | Qty / Amount | Location | Notes |
|---|---|---|---|---|
| Soldering Iron Tips | FEITA 900M-T conical replacement tips, 5pc, for 936/852D+/907 stations. https://www.amazon.com/dp/B07X7P8KMG | 5 | Bench | Compatible with Soaiy soldering station. |
| Solder Wire | — | — | Bench | Update brand/gauge when known. |
| Solder Wick | Desoldering braid | — | Bench | Update brand/width when known. |
| Flux Pens | Rosin flux | — | Bench | Update brand/count when known. |
| No Clean Solder Flux Paste | Lead-free rosin flux, no-clean formula, 4-pack 10cc syringes. https://www.amazon.com/dp/B0GGQNNF98 | 4 | Plastic Box | No project assigned. |

---

## Inventory Update Log

| Date | Project | Change |
|---|---|---|
| 2026-05 | Garage radar | ESP32 ×1 used; LD2412 ×1 used; perfboard ×1 used |
| 2026-05 | front-porch-temp-sensor | ESP32 ×1 used; BH1750 ×1 used; BMP280 ×1 used; perfboard ×1 reserved |
| 2026-05-26 | BME280 order received | GY-BME280 ×4 received; Podazz BMP280 ×3 returned (counterfeit) |
| 2026-05-26 | front-porch-temp-sensor | GY-BME280 ×1 deployed (replaced counterfeit BMP280); humidity now active |
| 2026-05-27 | Stock | EVE 3.3V 18650 3200mAh ×5 received |
| 2026-05-28 | hiking-sensor, Stock | E-ink display and push buttons added, various other |
| 2026-05-30 | Stock | Raspberry Pi Zero W ×1 added (Vilros kit B0748MPQT4, BCM2835 single-core); no project assigned |
| 2026-05-30 | Structure | Added Location column; assigned bag numbers 1–19; added Tools section |
| 2026-05-30 | Structure | Source cleanup: normalized table spacing, shortened placeholder text |
| 2026-06-01 | Stock | Silicone hookup wire 24 AWG ×6 rolls (Shelf); USB-C to Micro USB adapters ×4 (Bag 20); DC buck converters 12V→5V ×2 (Bag 21). Wire and Cables and Adapters sections added. Duplicate rows removed. |
| 2026-06-02 | Stock | LTR390 UV light sensor ×2 added (Sensors, Bag 22) |
| 2026-06-04 | Stock | Music Response bin added to Location Key. BC557B ×10, BC547B ×50, 1N4148 ×50 (Discrete Semiconductors, new section); 100Ω resistors ×50, 10K trim pots ×24, LED assortment (LEDs and Resistors); power supply module ×5, 9V battery clips ×10 (Power Components); all in Music Response bin |
| 2026-06-08 | p-w-firefly | 3M Mini-Clamp connectors received, added to Cables and Adapters, Bag 24 |
| 2026-06-07 | Stock | SparkFun SEN-23715 Sensirion sensor ×1 added (Sensors, Plastic Box) |
| 2026-06-06 | Stock | Gebildet slide switch assortment added (Prototyping and Build Hardware, Plastic Box); FEITA 900M-T soldering tips ×5 added (Tools — Consumables, Bench) |
| 2026-06-05 | Stock | iCrimp SN-28B crimping tool added (Tools — Bench Equipment, Shelf); Taiss 600pc Dupont connector kit added (Prototyping and Build Hardware, Plastic Box) |
| 2026-06-04 | hiking-sensor | ESP32 ×1 used; BME280 ×1 used; LTR-390 ×1 used; e-ink display ×1 used; push button ×1 used; EEMB LiPo ×1 used; TP4056+boost ×1 used |
| 2026-06-10 | garage-radar | Build complete. ESP32 ×1 used; HLK-LD2412 ×1 used; green LED ×1 used; yellow LED ×1 used; 330Ω resistors ×2 used; female headers (19-pin ×2, 4-pin ×1) used; M3 standoffs ×4 used; 5×7cm perfboard ×1 used |
| 2026-06-14 | Stock | No clean solder flux paste ×4 syringes (Plastic Box); M2 screw assortment 645 pcs (Plastic Box); 3M double-sided foam tape ×1 roll (Plastic Box); M2 hex brass standoff kit 390 pcs (Plastic Box); 2-pin screw terminal block 3.5mm ×50 (Plastic Box) |
| 2026-07-01 | air-quality-monitor | Adafruit SEN54/SEN55 STEMMA QT adapter breakout ×1 received, added to Sensors, Bag 25; JST GH 1.25mm 6-pin cable (100mm) ×1 received, added to Cables and Adapters, Bag 25 |
| 2026-07-01 | Stock | Heat shrink butt connectors 26-24 AWG ×100 added (Prototyping and Build Hardware, Bag 26) |
| 2026-07-01 | Stock | Momentary push button switch 12mm waterproof ×6 added (Prototyping and Build Hardware, Bag 27) |
| 2026-07-01 | Stock | DS3231 RTC module ×5 added (Sensors, Bag 28); 1 allocated: bedside-clock |
| 2026-07-01 | Stock | SH1106 OLED display 1.3" ×5 added (Displays, Bag 29); 1 allocated: bedside-clock |
| 2026-07-01 | air-quality-monitor | SparkFun SEN-23715 (Sensirion SEN54, Plastic Box) allocated to air-quality-monitor project |
| 2026-07-02 | photo-server | GMKtec NucBox M8 ×1 added (Servers & Mini PCs, Shelf); allocated: photo-server |
