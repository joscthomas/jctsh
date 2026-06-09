# Pleasure-Way Firefly Interface

Raspberry Pi 3B+ with PiCAN2 CAN-Bus HAT connected to the Firefly Integrations Vegatouch RV-C network in the 2018 Pleasure-Way Lexor FL (RAM ProMaster 3500, VIN 3C6URVJG9JE113400). The eRVin software (myervin.com) provides a web dashboard for monitoring and controlling coach systems.

**Status: Complete — installed and operational as of June 2026.**

---

## Dashboard Access

| Location | URL |
|---|---|
| Home network | http://192.168.1.219 |
| Away via Tailscale | http://100.90.246.43 |
| JCT-RV local hotspot | http://192.168.5.1 |

See `operations.md` for full usage guide and troubleshooting.

---

## Documentation

| File | Contents |
|---|---|
| `operations.md` | Day-to-day use, network access, troubleshooting |
| `bill-of-materials.md` | Parts list |
| `hardware-assembly.md` | Pi and PiCAN2 assembly |
| `image-setup.md` | eRVin SD card setup |
| `first-boot.md` | Initial configuration after imaging |
| `pican2-config.md` | CAN interface setup |
| `ervin-configuration.md` | Dashboard customization |
| `wifi-hotspot.md` | JCT-RV fallback hotspot setup |
| `tailscale.md` | Tailscale remote access setup |
| `heartbeat.md` | Hourly heartbeat to JCTsh log dashboard |
| `physical-installation.md` | RV installation — wiring, mounting, CAN connection |
| `rvc-verification.md` | RV-C bus verification |
| `sd-backup.md` | SD card backup procedure |
| `testing.md` | Full system test results |
| `secrets.md` | Credentials (gitignored) |
