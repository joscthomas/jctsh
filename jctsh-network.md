# JCTsh Network

All device IPs are DHCP-reserved on the router. Update this file when adding a new device.

## Devices

| Device | IP | Hostname | MAC | Notes |
|---|---|---|---|---|
| Raspberry Pi | 192.168.1.117 | raspberrypi.local | — | Pi host — MQTT, Node-RED, HA, log server |
| garage-radar ESP32 | 192.168.1.119 | garage-radar.local | 04-B2-47-82-74-64 | ESPHome |
| salt-sensor ESP32 | 192.168.1.181 | salt-sensor.local | — | Arduino; hostname pending reflash |
| front-porch-temp-sensor ESP32 | 192.168.1.202 | front-porch-temp-sensor.local | — | ESPHome |
