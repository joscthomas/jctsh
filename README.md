# JCTsh — Smart Home Automation
Joseph C Thomas | Tucson, AZ

A monorepo for JCT smart home automation components running on
Raspberry Pi with MQTT, Node-RED, and a centralized Python log server.

See [ENVIRONMENT.md](./ENVIRONMENT.md) for the full smart home device inventory.
See [CLAUDE.md](./CLAUDE.md) for infrastructure details, MQTT conventions, logging standards, and developer reference.

## Components
- [salt-sensor](./components/salt-sensor/) — Water softener salt level sensor
- [garage-presence](./components/garage-presence/) — Garage presence countdown timer (HA-only)
- [automatic-garage-door-opener-closer](./components/automatic-garage-door-opener-closer/) — Automatic garage door opener/closer
- [garage-radar](./components/garage-radar/) — 24GHz mmWave workbench presence radar (ESPHome + LD2412)
- [front-porch-temp-sensor](./components/front-porch-temp-sensor/) — Front porch temperature, pressure, and light sensor with push notifications (ESPHome)
- [p-w-firefly](./components/p-w-firefly/) — Pleasure-Way Firefly Interface (in progress)
