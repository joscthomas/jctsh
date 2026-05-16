# JCTsh — Smart Home Automation
Joseph C Thomas | Tucson, AZ

A monorepo for JCT smart home automation components running on
Raspberry Pi with MQTT, Node-RED, and a centralized Python log server.

## Components
- [salt-sensor](./components/salt-sensor/) — Water softener salt level sensor

## Infrastructure (jctsh\core\)
- **MQTT broker** (Mosquitto) — message bus for all components
- **Node-RED** — sensor logic and flow automation
- **Logging server** — Python service at http://JCTsh.local
- **Home Assistant** — Docker, role TBD (possible SmartThings bridge)

## Conventions
- MQTT topics: `jctsh/<type>/<component>/<message-type>`
- Log topic: `jctsh/<type>/<component>/log`
- Future ESP components: ESPHome YAML (not Arduino C++)
- Pi access: `raspberrypi.local`
- Log dashboard: `http://JCTsh.local`
