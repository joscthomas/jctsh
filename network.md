# JCTsh — Home Network Reference

## WiFi

| SSID | Band | Use |
|---|---|---|
| JCTnet1 | 2.4GHz | All JCTsh devices — Raspberry Pi, ESP32 |
| JCTnet1_5G | 5GHz | Not used for JCTsh devices |

**Always use JCTnet1 (2.4GHz) for all JCTsh devices.** Raspberry Pi 3B+ and ESP32 have 2.4GHz-only WiFi radios — JCTnet1_5G will not connect on these devices.

## Wired

| Device | IP | Notes |
|---|---|---|
| Home Pi (raspberrypi.local) | 192.168.1.117 | DHCP reservation — WiFi (wlan0) |
| Home Pi (raspberrypi.local) | 192.168.1.210 | DHCP reservation — Ethernet (eth0) |

## Tailscale

| Device | Tailscale IP | Notes |
|---|---|---|
| Home Pi | 100.70.162.24 | Always reachable when Tailscale is running |
| RV Pi (coachproxyos) | 100.90.246.43 | eRVin dashboard at http://100.90.246.43 |
