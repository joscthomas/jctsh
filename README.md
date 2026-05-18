# JCTsh — Smart Home Automation
Joseph C Thomas | Tucson, AZ

A monorepo for JCT smart home automation components running on
Raspberry Pi with MQTT, Node-RED, and a centralized Python log server.

## Components
- [salt-sensor](./components/salt-sensor/) — Water softener salt level sensor
- [garage-presence](./components/garage-presence/) — Garage presence countdown timer (HA-only)
- [automatic-garage-door-opener-closer](./components/automatic-garage-door-opener-closer/) — Automatic garage door opener/closer

## Infrastructure (jctsh\core\)
- **MQTT broker** (Mosquitto) — message bus for all components
- **Node-RED** — sensor logic and flow automation
- **Logging server** — Python service at http://raspberrypi.local
- **Home Assistant** — Docker, role: SmartThings bridge

## Conventions
- MQTT topics: `jctsh/<type>/<component>/<message-type>`
- Log topic: `jctsh/<type>/<component>/log`
- Future ESP components: ESPHome YAML (not Arduino C++)
- Pi access: `raspberrypi.local`
- Log dashboard: `http://raspberrypi.local`
