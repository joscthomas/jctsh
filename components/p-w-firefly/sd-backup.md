# SD Card Backup — Pleasure-Way Firefly Interface

Image the configured SD card before physical RV installation. All bench configuration — eRVin flows, WiFi hotspot, Tailscale, heartbeat — is captured. If the card ever fails, flash the backup to a new SanDisk MAX Endurance and the Pi is operational immediately.

---

## When to Back Up

- **Before Step 10 (physical install)** — captures the completed bench build
- After any major configuration change

---

## Procedure

1. SSH into the Pi and shut down cleanly:

```
ssh pi@192.168.1.219 "sudo shutdown -h now"
```

2. Wait for the green activity LED to stop blinking (about 10 seconds), then remove the SD card.

3. Insert the SD card into your PC card reader.

4. Open **USB Image Tool** (free, portable — [alexpage.de/usb-image-tool](https://www.alexpage.de/usb-image-tool/download/)). Run as Administrator.

   Note: Win32DiskImager does not work on this Windows 11 setup (crashes after UAC prompt). USB Image Tool is the confirmed working tool.

5. Select the SD card from the device list. Click **Device → Image** and save as:

```
ervin-coachproxyos-backup-YYYYMMDD.img
```

6. The image will be ~30GB. Store in Documents or a backup drive.

7. Reinsert the SD card and power the Pi back up.

---

## Windows 11 Imaging Tool Notes

Tested on this machine (Windows 11 Home, May 2026):

| Tool | Result |
|---|---|
| **USB Image Tool** | Works — confirmed. Run as Administrator. Device → Image. |
| Win32DiskImager | Fails — crashes silently after UAC prompt on Windows 11 |
| PowerShell FileStream (`\\.\PhysicalDrive2`) | Fails — .NET `Read()` returns 0 prematurely at sector boundaries, produces a partial image (~1.2GB) |
| WSL `dd` with sudo | Fails — WSL2 block device reads return 0 bytes despite exit code 0 |

---

## Restoring from Backup

If the card fails, flash the backup image to a new SanDisk MAX Endurance 32GB using Raspberry Pi Imager (Use Custom → select .img file). The restored Pi will have the same hostname, IP reservation, Tailscale identity, and all configuration.

---

## Confirmed Details

| Item | Value |
|---|---|
| Backup taken | 2026-05-26 |
| Backup filename | ervin-coachproxyos-backup-20260526.img |
| Backup stored at | C:\Users\jcthomas\Documents\JCT Documents\SmartHome\ |
| Tool used | USB Image Tool (run as Administrator) |
