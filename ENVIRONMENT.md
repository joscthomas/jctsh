# JCTsh — Smart Home Environment

Tucson, AZ | Joseph C Thomas

## Hub & Controller
| Device | Role |
|---|---|
| SmartThings Hub | Primary smart home controller — manages Zigbee, Z-Wave, and virtual switches |
| Raspberry Pi 3B+ | JCTsh automation server — see [CLAUDE.md](./CLAUDE.md) for services, ports, and access |

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
| High L/R Speakers | 2× Polk (ceiling-mounted) |
| Back L/R Speakers | 2× Polk (ceiling-mounted) |
| Back Center L/R Speakers | 2× Polk (ceiling-mounted) |
| Headphones | Bowers & Wilkins Px7 S2e (Bluetooth) |
| DVD Player | Rarely used |
| Chromecast / Google TV | Local TV channels, Amazon Prime, Peacock, other streaming, Amazon Music |

## Voice & Media
| Device | Location | Integration |
|---|---|---|
| Google Home | Garage | Google Home + SmartThings |
| Google Home | Master bedroom | Google Home + SmartThings |
| Google Home | Gathering room | Google Home + SmartThings |
| Google Home | Back porch | Google Home + SmartThings |
| Google Nest Display | Master bath | Google Home |
| Google Pixel Tablet + Dock | — | Google Home |
| Chromecast | — | Google Home |
| Google TV | — | Google Home |

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
