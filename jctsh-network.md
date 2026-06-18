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
| Raspberry Pi (eth0) | 192.168.1.117 | raspberrypi.local | B8-27-EB-A2-5C-E5 | Pi host — MQTT, Node-RED, HA, log server; wired, DHCP-reserved |
| Raspberry Pi (wlan0) | 192.168.1.217 | raspberrypi.local | B8-27-EB-F7-09-B0 | WiFi — dynamic IP, not reserved; not used for service access |
| coachproxyos (RV Pi) | 192.168.1.219 | coachproxyos.local | B8-27-EB-BD-C6-63 | eRVin — at home only when coach is home |
| garage-radar ESP32 | 192.168.1.119 | garage-radar.local | 04-B2-47-82-74-64 | ESPHome |
| salt-sensor ESP32 | 192.168.1.181 | salt-sensor.local | F4-65-0B-AB-6B-BC | Arduino; hostname pending reflash |
| front-porch-temp-sensor ESP32 | 192.168.1.202 | front-porch-temp-sensor.local | B4-BF-E9-C9-EF-68 | ESPHome |
| hiking-sensor ESP32 | 192.168.1.161 | hiking-monitor.local | 04-B2-47-97-DF-2C | ESPHome |
| SmartThings Hub | 192.168.1.112 | — | 24-FD-5B-01-72-23 | Samsung hub — stable IP required for HA integration |

## Tailscale

Tailscale creates a private encrypted mesh network so enrolled devices can reach each other by stable IP regardless of physical network — without exposing services to the public internet or dealing with dynamic IP addresses. Both the home Pi and coachproxyos have Tailscale installed. Each has its own Tailscale IP, reachable from any device on the same Tailscale account with any internet connection — laptop on hotel WiFi, Pixel on cellular, JCT-RV with masqueraded internet, etc. The Pixel hotspot is not required for Tailscale; it is just one source of internet.

| Device | Tailscale IP | Notes |
|---|---|---|
| Home Pi | 100.70.162.24 | MQTT broker, Node-RED, HA, log server — always reachable when Tailscale is running |
| RV Pi (coachproxyos) | 100.90.246.43 | eRVin dashboard at `http://100.90.246.43`; comes up when Pi has internet via Pixel hotspot |

## Remote and Field Networks

| Network | SSID | Subnet | Notes |
|---|---|---|---|
| Pixel hotspot | JCT Hotspot | Pixel-assigned | 2.4GHz — used by hiking-monitor and coachproxyos when away from home; any phone works with matching SSID/password; no re-flash needed |
| RV local AP | JCT-RV | 192.168.5.x | Always broadcasting (coachproxyos concurrent STA+AP); Pi at `192.168.5.1`; primary laptop access point in the RV |

**Remote MQTT for ESP32 devices:** ESP32s can't run Tailscale. When away from home they reach the MQTT broker via `jctsh.duckdns.org:1883` — DuckDNS resolves to the router public IP, which forwards port 1883 to 192.168.1.117. Confirmed working: hiking-monitor field test June 2026.

For coachproxyos access workflows and JCT-RV troubleshooting, see `components/p-w-firefly/operations.md`.
