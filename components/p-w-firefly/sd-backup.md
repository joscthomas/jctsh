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

4. Open **Win32DiskImager** (free — [sourceforge.net/projects/win32diskimager](https://sourceforge.net/projects/win32diskimager/)).

5. Select the SD card drive. Click **Read**. Save as:

```
ervin-coachproxyos-backup-YYYYMMDD.img
```

6. The image will be ~32GB. Store in Documents or a backup drive.

7. Reinsert the SD card and power the Pi back up.

---

## Restoring from Backup

If the card fails, flash the backup image to a new SanDisk MAX Endurance 32GB using Raspberry Pi Imager (Use Custom → select .img file). The restored Pi will have the same hostname, IP reservation, Tailscale identity, and all configuration.

---

## Confirmed Details

| Item | Value |
|---|---|
| Backup taken | |
| Backup filename | |
| Backup stored at | |
