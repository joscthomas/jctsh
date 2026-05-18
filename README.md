# JCTsh — Smart Home Automation
Joseph C Thomas | Tucson, AZ

A monorepo for JCT smart home automation components running on
Raspberry Pi with MQTT, Node-RED, and a centralized Python log server.

See [ENVIRONMENT.md](./ENVIRONMENT.md) for the full smart home device inventory.
See [CLAUDE.md](./CLAUDE.md) for infrastructure details, MQTT conventions, and developer reference.

## Components
- [salt-sensor](./components/salt-sensor/) — Water softener salt level sensor
- [garage-presence](./components/garage-presence/) — Garage presence countdown timer (HA-only)
- [automatic-garage-door-opener-closer](./components/automatic-garage-door-opener-closer/) — Automatic garage door opener/closer
