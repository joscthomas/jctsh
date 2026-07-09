# JCTsh — Smart Home Environment

Tucson, AZ | Joseph C Thomas

## Hub & Controller
| Device | Role |
|---|---|
| TP-Link Archer AXE75 | Router (TP-Link AXE5400 Tri-Band Wi-Fi 6E) — gateway/DHCP server for the whole home network, `192.168.1.1`. See `jctsh-network.md` |
| SmartThings Hub | Primary smart home controller — manages Zigbee, Z-Wave, and virtual switches |
| Raspberry Pi 3B+ | JCTsh automation server — see [CLAUDE.md](./CLAUDE.md) for services, ports, and access |
| KeepConnect-27F8 | Router rebooter — power-cycles router/modem on internet-loss detection; scoped to router outlet only. See [keepconnect.md](./keepconnect.md) |

## Servers & Mini PCs
| Device | Role | Location |
|---|---|---|
| GMKtec NucBox M8 | photo-server — Immich self-hosted photo library | Home network, wired to TP-Link AXE5400 |

### GMKtec NucBox M8 — photo-server
| Attribute | Value |
|---|---|
| Model | M8-5-33S |
| Serial | MB261801199 |
| CPU | AMD Ryzen 5 PRO 6650H, 6C/12T, up to 4.5GHz, Zen 3+ |
| RAM | 16GB LPDDR5 6400MHz |
| Storage (internal) | Netac G932EQN3 512GB NVMe SSD (OS, database, thumbnails) |
| Storage (photo library) | External USB drive(s) — see photo-server component docs |
| GPU | AMD Radeon 660M (AV1/HEVC/VP9 hardware decode) |
| NIC 1 | Realtek Gaming 2.5GbE Family Controller |
| NIC 2 | Realtek Gaming 2.5GbE Family Controller #2 |
| WiFi | RZ616 Wi-Fi 6E 160MHz |
| Ports | USB4 (40Gbps), OCuLink, USB 3.2 Gen2 ×3, HDMI 2.0, DisplayPort 1.4, 3.5mm audio |
| OS | Windows 11 Pro (pre-installed; to be replaced with Debian Server or Proxmox) |
| Windows license | BIOS-embedded OEM key — retrievable via PowerShell if needed |
| Network | Wired 2.5GbE to TP-Link AXE5400 |
| Primary role | Immich photo server; potential consolidation host for HA/Node-RED/MQTT |
| Purchase date | 2026-07 (Amazon Prime Day) |

## Lighting & Power
- Zigbee and Z-Wave switches and plug adapters throughout the home
- Controls: lights, fans, and other loads via SmartThings

## Climate
- **Ecobee** smart thermostat — integrated with SmartThings and Google Home

## Sensors
| Device | Type | Integration |
|---|---|---|
| Door sensors (multiple) | Open/close | SmartThings (Z-Wave/Zigbee) |
| Garage door sensor | Open/close | SmartThings |
| Water softener salt sensor | Ultrasonic level (ESP32 + JSN-SR04T) | MQTT → Node-RED → SmartThings via HA |
| Ring cameras (garage, side yard, side gate, back porch, front porch, front door, gathering room) | Motion detection | SmartThings |
| Ring doorbell | Motion + video doorbell | SmartThings |

## Security & Cameras
- **Ring** doorbell and cameras at: garage, side yard, side gate, back porch, front porch, front door, gathering room
- All Ring devices integrated with SmartThings for motion detection automations

## Garage
- **Automated Garage Door Opener/Closer** — CreaCity visor remote (hardware-modified) + Zigbee low-voltage switch → LiftMaster opener
- Controlled via SmartThings routine and Google Home voice commands
- See `components/automatic-garage-door-opener-closer/`

## Gathering Room AV
| Component | Device |
|---|---|
| Receiver | Denon AVRX6400H (audio/video switching) |
| TV | Samsung 4K UHD |
| Front L/R Speakers | 2× Polk |
| Center Speaker | 1× Polk |
| High L/R Speakers | 2× (ceiling-mounted) |
| Back L/R Speakers | 2× (ceiling-mounted) |
| Back Center L/R Speakers | 2× (ceiling-mounted) |
| Headphones | Bowers & Wilkins Px7 S2e (Bluetooth) |
| DVD Player | Rarely used |
| Chromecast / Google TV | Local TV channels, Amazon Prime, Peacock, other streaming, Amazon Music |

## Voice & Media
| Device | Location        | Integration                       |
|---|-----------------|-----------------------------------|
| Google Home | Garage          | Google Home Speaker |
| Google Home | Gathering room  | Google Home |
| Google Home | Back porch      | Google Home     |
| Google Nest Display | Master bath     | Google Home                       |
| Google Pixel Tablet + Dock | Gathering room  | Google Home                       |
| Chromecast | Gathering room  | Google Home                       |
| Google TV | Gathering room | Google Home                       |

## Mobile
| Device | Owner |
|---|---|
| Google Pixel Pro 10 | Joseph Thomas |
| Google Pixel 7 | Robin |

## RV
- **Vehicle:** 2018 Ram ProMaster 3500 — VIN 3C6URVJG9JE113400
- **Coach:** Pleasure-Way Lexor FL
- **Control system:** Firefly network

## JCTsh Custom Components
See [README.md](./README.md) for the full component list.
