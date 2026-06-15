# Pleasure-Way Firefly Interface

Raspberry Pi 3B+ with PiCAN2 CAN-Bus HAT connected to the Firefly Integrations
Vegatouch RV-C network in the 2018 Pleasure-Way Lexor FL — providing a web dashboard
for monitoring and controlling coach systems from any browser.

**Status:** Production — installed and operational (June 2026)
**Hardware:** Raspberry Pi 3B+ + PiCAN2 SMPS HAT + Geekworm case

---

## What It Solves

The Firefly Integrations Vegatouch system has no native web dashboard or remote access.
The eRVin software (myervin.com) running on this Pi provides a browser-based interface
for all coach systems — lights, slides, tanks, climate — accessible on the home network,
on the JCT-RV local hotspot, and remotely via Tailscale from anywhere.

---

## Architecture

```
Firefly Integrations Vegatouch RV-C network
      │  CAN bus (250 kbps)
      ▼
PiCAN2 HAT (can0 interface)
      │
      ▼
eRVin OS (Raspberry Pi 3B+)
      ├── Web dashboard (port 80)
      ├── Node-RED (port 1880)
      └── jctsh-heartbeat (systemd timer, every 30 min)
            └── JCTsh home MQTT broker (via Tailscale)
                  └── Log dashboard + watchdog
```

---

## Dashboard Access

| Network | URL |
|---|---|
| Home network | http://192.168.1.219 |
| Away via Tailscale | http://100.90.246.43 |
| JCT-RV local hotspot | http://192.168.5.1 |

The JCT-RV hotspot (`192.168.5.1`) is a concurrent STA+AP mode access point on the Pi —
available even with no external WiFi or cellular. See [wifi-hotspot.md](wifi-hotspot.md).

Remote access via Tailscale requires the Pixel or other device to be on the same
Tailscale account. See [tailscale.md](tailscale.md).

---

## Quick Start

The system is fully operational. For day-to-day use and troubleshooting:

- See [operations.md](operations.md) — network access, common tasks, troubleshooting
- SSH: `pi@192.168.1.219` (home) or `pi@100.90.246.43` (Tailscale) — key auth from
  this machine

---

## How It Works

eRVin OS (v0.6.2, Raspbian Buster-based) reads the RV-C CAN bus at 250 kbps via the
PiCAN2 HAT and presents all Firefly-controllable coach systems through a web interface.
A Python systemd timer (`jctsh-heartbeat.py`, every 30 minutes) publishes a heartbeat
to the JCTsh home MQTT broker via Tailscale, confirming the Pi is reachable remotely.
The heartbeat appears in the log dashboard and triggers the Node-RED watchdog.

The JCT-RV hotspot provides local network access in the van without any external
connectivity — phones and tablets connect to `JCT-RV` to reach the dashboard at
`192.168.5.1`.

**SD card:** SanDisk MAX Endurance 32GB. Backup image at
`C:\Users\jcthomas\Documents\JCT Documents\SmartHome\ervin-coachproxyos-backup-20260526.img`
— use USB Image Tool (run as Admin) to restore.

---

## Files

| File | Purpose |
|---|---|
| `operations.md` | Day-to-day use, network access, troubleshooting |
| `bill-of-materials.md` | Parts list |
| `hardware-assembly.md` | Pi and PiCAN2 assembly |
| `image-setup.md` | eRVin SD card imaging |
| `first-boot.md` | Initial configuration after imaging |
| `pican2-config.md` | CAN interface setup |
| `ervin-configuration.md` | Dashboard customization |
| `wifi-hotspot.md` | JCT-RV fallback hotspot setup |
| `tailscale.md` | Tailscale remote access setup |
| `heartbeat.md` | 30-min heartbeat to JCTsh log dashboard and watchdog |
| `jctsh-heartbeat.py` | Heartbeat script — deployed to `/usr/local/bin/` on RV Pi |
| `jctsh-heartbeat.timer` | systemd timer unit — deployed to `/etc/systemd/system/` on RV Pi |
| `physical-installation.md` | RV installation — wiring, mounting, CAN connection |
| `rvc-verification.md` | RV-C bus verification |
| `sd-backup.md` | SD card backup and restore procedure |
| `testing.md` | Full system test results |
| `secrets.md` | Credentials — gitignored |
| `p-w-firefly-claude-code-instructions.md` | Full build instructions |
