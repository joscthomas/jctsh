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
| TP-Link Archer AXE75 (router) | 192.168.1.1 | — | F0-09-0D-AB-E1-40 | TP-Link AXE5400 Tri-Band Wi-Fi 6E; gateway/DHCP server for every device below. IPv6 LAN: `FE80::F209:DFF:FEAB:E140/64`. Power controlled by KeepConnect — see `keepconnect.md` |
| Raspberry Pi (eth0) | 192.168.1.117 | raspberrypi.local | B8-27-EB-A2-5C-E5 | Pi host — MQTT, Node-RED, HA, log server; wired, DHCP-reserved |
| Raspberry Pi (wlan0) | 192.168.1.217 | raspberrypi.local | B8-27-EB-F7-09-B0 | WiFi — dynamic IP, not reserved; not used for service access |
| coachproxyos (RV Pi) | 192.168.1.219 | coachproxyos.local | B8-27-EB-BD-C6-63 | eRVin — at home only when coach is home |
| garage-radar ESP32 | 192.168.1.119 | garage-radar.local | 04-B2-47-82-74-64 | ESPHome |
| salt-sensor ESP32 | 192.168.1.181 | salt-sensor.local | F4-65-0B-AB-6B-BC | Arduino; hostname pending reflash |
| front-porch-temp-sensor ESP32 | 192.168.1.202 | front-porch-temp-sensor.local | B4-BF-E9-C9-EF-68 | ESPHome |
| hiking-sensor ESP32 | 192.168.1.161 | hiking-monitor.local | 04-B2-47-97-DF-2C | ESPHome |
| SmartThings Hub | 192.168.1.112 | — | 24-FD-5B-01-72-23 | Samsung hub — stable IP required for HA integration |
| photo-server (GMKtec M8) | 192.168.1.165 | photo-server.local | 70-70-FC-09-AD-A5 | Immich photo server + photo-tv-display (planned); wired gigabit direct to router; DHCP-reserved |
| KeepConnect-27F8 (router rebooter) | 192.168.1.108 | esp32-5227F8 | 34-98-7A-52-27-F8 | Not a JCTsh component — see `keepconnect.md`; DHCP-reserved |

## Tailscale

Tailscale creates a private encrypted mesh network so enrolled devices can reach each other by stable IP regardless of physical network — without exposing services to the public internet or dealing with dynamic IP addresses. Both the home Pi and coachproxyos have Tailscale installed. Each has its own Tailscale IP, reachable from any device on the same Tailscale account with any internet connection — laptop on hotel WiFi, Pixel on cellular, JCT-RV with masqueraded internet, etc. The Pixel hotspot is not required for Tailscale; it is just one source of internet.

| Device | Tailscale IP | Notes |
|---|---|---|
| Home Pi | 100.70.162.24 | MQTT broker, Node-RED, HA, log server — always reachable when Tailscale is running |
| RV Pi (coachproxyos) | 100.90.246.43 | eRVin dashboard at `http://100.90.246.43`; comes up when Pi has internet via Pixel hotspot |
| photo-server (GMKtec M8) | 100.111.16.14 | Immich + photo-tv-display (planned) — reachable remotely for admin |

## Scheduled Maintenance Windows

Consolidated view across all recurring reboot/backup jobs, so a new one can be scheduled without colliding with an existing one. Individual jobs are documented in each host's own doc (linked below) — this table exists purely to catch conflicts at a glance.

| Job | Schedule | Host | Doc |
|---|---|---|---|
| KeepConnect router reboot | Weekly, Wed 3:00 AM (drifts — see note) | Router | `keepconnect.md` |
| Pi scheduled reboot | Weekly, Mon 3:00 AM | Pi | `SOFTWARE-ENVIRONMENT.md` |
| M8 scheduled reboot | Weekly, Mon 4:00 AM | M8 (photo-server) | `components/photo-server/operations.md` |
| M8 backup (rsync) | Weekly, Sun 2:00 AM | M8 (photo-server) | `components/photo-server/backup.md` |
| M8 heartbeat | Every 30 min | M8 (photo-server) | `components/photo-server/heartbeat.md` |
| M8 Immich update check | Daily, 6:00 AM | M8 (photo-server) | `components/photo-server/operations.md` |
| Pi watchdog heartbeat | Hourly | Pi | `CLAUDE.md` |

**KeepConnect's day drifts** — its "every 7 days" timer appears to restart from *any* reset, scheduled or outage-triggered, so Wednesday isn't fixed and could land on a different day later (it had already drifted once before, originally landing on a different day — see `keepconnect.md`). The Pi/M8 reboot stagger (1 hour apart, Mon 3am/4am) is deliberate — the M8's heartbeat publishes to the Pi's MQTT broker, so overlapping the two would produce a false "M8 down" reading. The router reboot isn't coordinated against the others since it's only a brief (~30 sec cut, ~4 min reconnect) network blip that the other jobs tolerate regardless of timing — but if a new recurring job is ever added, check this table first and prefer a time with at least an hour of clearance from anything above.

## Remote and Field Networks

| Network | SSID | Subnet | Notes |
|---|---|---|---|
| Pixel hotspot | JCT Hotspot | Pixel-assigned | 2.4GHz — used by hiking-monitor and coachproxyos when away from home; any phone works with matching SSID/password; no re-flash needed |
| RV local AP | JCT-RV | 192.168.5.x | Always broadcasting (coachproxyos concurrent STA+AP); Pi at `192.168.5.1`; primary laptop access point in the RV |

**Remote MQTT for ESP32 devices:** ESP32s can't run Tailscale. When away from home they reach the MQTT broker via `jctsh.duckdns.org:8883` (TLS) — DuckDNS resolves to the router public IP, which forwards port 8883 to 192.168.1.117. Confirmed working: hiking-monitor field test June 2026 (pre-TLS, plaintext 1883); TLS cutover completed 2026-07-13 (CARD-0003) — hiking-monitor verified connecting over 8883 via live Mosquitto log. Port 1883 is no longer forwarded to the internet; it remains LAN-only for stationary devices (garage-radar, salt-sensor, front-porch-temp-sensor, etc.).

For coachproxyos access workflows and JCT-RV troubleshooting, see `components/p-w-firefly/operations.md`.
