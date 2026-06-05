# JCTsh Network

All device IPs are DHCP-reserved on the router. Update this file when adding a new device.

## WiFi

| SSID | Band | Use |
|---|---|---|
| JCTnet1 | 2.4GHz | All JCTsh devices — Raspberry Pi, ESP32 |
| JCTnet1_5G | 5GHz | Not used for JCTsh devices |

**Always use JCTnet1 (2.4GHz) for all JCTsh devices.** Raspberry Pi 3B+ and ESP32 have 2.4GHz-only WiFi radios — JCTnet1_5G will not connect on these devices.

## Devices

| Device | IP | Hostname | MAC | Notes |
|---|---|---|---|---|
| Raspberry Pi (wlan0) | 192.168.1.117 | raspberrypi.local | B8-27-EB-A2-5C-E5 | Pi host — MQTT, Node-RED, HA, log server |
| Raspberry Pi (eth0) | 192.168.1.210 | raspberrypi.local | — | Wired fallback |
| coachproxyos (RV Pi) | 192.168.1.219 | coachproxyos.local | B8-27-EB-BD-C6-63 | eRVin — at home only when coach is home |
| garage-radar ESP32 | 192.168.1.119 | garage-radar.local | 04-B2-47-82-74-64 | ESPHome |
| salt-sensor ESP32 | 192.168.1.181 | salt-sensor.local | F4-65-0B-AB-6B-BC | Arduino; hostname pending reflash |
| front-porch-temp-sensor ESP32 | 192.168.1.202 | front-porch-temp-sensor.local | B4-BF-E9-C9-EF-68 | ESPHome |
| hiking-sensor ESP32 | 192.168.1.162 | hiking-monitor.local | 04-B2-47-97-DF-2C | ESPHome; reservation pending (Step 18) |
| SmartThings Hub | 192.168.1.192 | — | C6-5B-05-84-AC-03 | Samsung hub — stable IP required for HA integration |

## Tailscale

| Device | Tailscale IP | Notes |
|---|---|---|
| Home Pi | 100.70.162.24 | Always reachable when Tailscale is running |
| RV Pi (coachproxyos) | 100.90.246.43 | eRVin dashboard at http://100.90.246.43 |
