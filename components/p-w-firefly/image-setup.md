# MicroSD Preparation and eRVin Image Flash — Pleasure-Way Firefly Interface

Flash the eRVin OS image to the bench MicroSD card with home WiFi credentials pre-loaded.

---

## Tools Required

- Windows PC (this machine)
- Bench MicroSD card (on-hand card — not the SanDisk MAX Endurance permanent card)
- MicroSD card reader
- Raspberry Pi Imager — download from raspberrypi.com/software if not already installed

---

## eRVin OS Image

Image file: **`ervinos_v062_20221018.img`** (eRVin OS v0.6.2, 2022-10-18, based on Raspberry Pi OS Bullseye)

This is a 32-bit ARMv7 image compatible with Raspberry Pi 3B+.

---

## Flash with Raspberry Pi Imager (includes WiFi pre-configuration)

Raspberry Pi Imager handles WiFi credential injection during the flash process. The eRVin v0.6.2 image is based on Raspberry Pi OS Bullseye, which supports the Imager's customisation injection.

1. Insert the bench MicroSD card into the card reader and connect to this PC
2. Open Raspberry Pi Imager
3. **Raspberry Pi Device** → select **Raspberry Pi 3**
4. **Operating System** → scroll to the bottom → **Use custom** → select `ervinos_v062_20221018.img`
5. **Storage** → select the bench MicroSD card — confirm it is the bench card, not the SanDisk MAX Endurance permanent card
6. Click **Next**
7. When prompted about OS customisation, click **Edit Settings** and configure:
   - **Configure wireless LAN**: enter home WiFi SSID and password; Wireless LAN country = US
   - **Enable SSH**: use password authentication
   - Set hostname if desired (e.g. `ervin-rv`)
8. Click **Save**, then **Yes** to apply customisation, then **Yes** to confirm flashing
9. Wait for flash and verification to complete — Imager ejects the card automatically when done

**If the eRVin image does not support Imager customisation injection:** If the Pi does not connect to home WiFi after first boot (Step 6), the fallback is to manually create `wpa_supplicant.conf` on the boot partition after flashing:

```
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=US

network={
    ssid="YOUR_HOME_WIFI_SSID"
    psk="YOUR_HOME_WIFI_PASSWORD"
    key_mgmt=WPA-PSK
    priority=10
}
```

---

## After Flashing

**Do not insert the MicroSD card into the Pi yet.**

Step 5 (PiCAN2 driver configuration) requires editing `config.txt` on the boot partition before first boot. Leave the MicroSD card in the PC and proceed to Step 5.

---

## Confirmed Details

*(Update after Step 4 is complete.)*

| Item | Value |
|---|---|
| eRVin version | v0.6.2 (ervinos_v062_20221018.img) |
| WiFi pre-config method used | firstrun.sh injected via cmdline.txt (RPi Imager skipped customisation dialog; initial wpa_supplicant.conf failed due to wrong SSID) |
| Correct home WiFi SSID | JCTnet1 |
| Hostname set | Default (not changed) |
