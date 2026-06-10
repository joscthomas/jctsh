# JCTsh Access Reference

How to reach each service from different locations and devices.
IP addresses always work. MagicDNS names (e.g. `raspberrypi`) work when Tailscale is connected.

---

## Robin's Android phone — Home Assistant only

| Access method | URL / Action |
|---|---|
| Android app (recommended) | Open **Home Assistant** app — works at home and remotely automatically |
| Browser, home WiFi | http://192.168.1.117:8123 |
| Browser, remote | https://icvrjrdip5r1bzposjrtpprrivn9sovx.ui.nabu.casa |

Robin does not need Tailscale.

---

## Joseph's Windows laptop — All Services

Tailscale runs automatically as a Windows service — no manual connect needed.

### At home (JCTnet1 WiFi)

| Service | URL |
|---|---|
| Home Assistant | http://192.168.1.117:8123 |
| Log dashboard | http://192.168.1.117 |
| Node-RED editor | http://192.168.1.117:1880 |
| SSH to Pi | `ssh pi@192.168.1.117` |
| eRVin dashboard (coach home) | http://192.168.1.219 |
| eRVin Node-RED | http://192.168.1.219:1880 |
| SSH to RV Pi | `ssh pi@192.168.1.219` |

### Remote (Tailscale auto-connected)

| Service | URL |
|---|---|
| Home Assistant | http://raspberrypi:8123 |
| Log dashboard | http://raspberrypi |
| Node-RED editor | http://raspberrypi:1880 |
| SSH to Pi | `ssh pi@raspberrypi` |
| eRVin dashboard | http://coachproxyos |
| eRVin Node-RED | http://coachproxyos:1880 |
| SSH to RV Pi | `ssh pi@coachproxyos` |

If MagicDNS names don't resolve in the browser, use the Tailscale IPs directly:
- Home Pi: `100.70.162.24`
- RV Pi: `100.90.246.43`

---

## Joseph's Android phone — All Services

Tailscale is manual: open the Tailscale app and tap Connect before using remote URLs.

### At home (JCTnet1 WiFi, no Tailscale needed)

| Service | URL |
|---|---|
| Home Assistant | http://192.168.1.117:8123 or HA app |
| Log dashboard | http://192.168.1.117 |
| Node-RED editor | http://192.168.1.117:1880 |
| eRVin dashboard (coach home) | http://192.168.1.219 |

### Remote (open Tailscale app and tap Connect first)

| Service | URL |
|---|---|
| Home Assistant | HA app (no Tailscale needed) |
| Log dashboard | http://raspberrypi |
| Node-RED editor | http://raspberrypi:1880 |
| eRVin dashboard | http://coachproxyos |

---

## At the RV — any device connected to JCT-RV hotspot

No internet required. Tailscale not needed.

| Service | URL |
|---|---|
| eRVin dashboard | http://192.168.5.1 |
| eRVin Node-RED | http://192.168.5.1:1880 |

---

## Home Assistant Android App Setup (Robin's phone and Joseph's phone)

The HA companion app handles home vs. remote automatically via Nabu Casa:

1. Install **Home Assistant** from the Play Store
2. Open the app → **Get started**
3. Enter the Nabu Casa URL: `https://icvrjrdip5r1bzposjrtpprrivn9sovx.ui.nabu.casa`
4. The app discovers the local URL automatically when at home

Account: joscthomas@gmail.com

---

## Notes

- **`.local` hostnames** (raspberrypi.local, salt-sensor.local, etc.) are unreliable — use IPs or MagicDNS names instead.
- **ESP32 devices** (garage-radar, salt-sensor, front-porch-temp-sensor, hiking-sensor) are managed through HA and Node-RED — you don't access them directly during normal use.
- Full IP/MAC table: `jctsh-network.md`
