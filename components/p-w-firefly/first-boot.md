# First Boot — Pleasure-Way Firefly Interface

Boot the assembled Pi on the home network and reserve a static IP.

---

## Bench Power — Important

The PiCAN2 SMPS accepts 12V at its screw terminal. **Do not connect the screw terminal to anything during bench steps.** Power the Pi via its **micro-USB port** directly for all bench work (Steps 6–9). This bypasses the SMPS entirely and is the correct bench approach. The screw terminal is wired to coach 12V only during Step 10 (physical RV installation).

Use a USB power supply or USB port capable of **5V/2A minimum**. The Pi 3B+ can draw up to ~2.5A under load — a quality 2A+ supply is recommended.

---

## First Boot Procedure

1. Insert the MicroSD card into the Pi
2. Connect a micro-USB cable from a 5V/2A+ power supply to the Pi's micro-USB power port
3. Apply power — the Pi will begin booting
4. **Wait approximately 10 minutes.** On first boot, the Pi expands the filesystem to fill the card and reboots automatically. Do not interrupt power during this process.

---

## Find the Pi on the Network

After the Pi has booted and connected to home WiFi, find its IP address using one of these methods:

**Option A — Router DHCP table:**
- Log into the home router admin page
- Check the DHCP client list for a new device — look for hostname `raspberrypi` or `ervin-rv`
- Note the assigned IP address and the Pi's WiFi MAC address

**Option B — Fing app on Pixel:**
- Open Fing, tap **Refresh**
- Look for a new device on the network — it will identify as a Raspberry Pi

---

## Reserve a Static IP

Once you have the Pi's IP address and WiFi MAC address:

1. Log into the home router admin page
2. Find the DHCP reservation or static lease settings
3. Add a reservation: bind the Pi's WiFi MAC address to a chosen static IP
4. Document the reserved IP in the Confirmed Details section below

The Pi will use this IP address permanently on the home network.

---

## Access the eRVin Dashboard

1. Open **Chrome** on a Pixel
2. Navigate to `http://<reserved-IP>` (e.g. `http://192.168.1.xxx`)
3. The eRVin dashboard should load
4. **RV-C data will not appear** at this stage — no CAN bus is connected during bench steps. This is expected. The dashboard UI loading is all that needs to be confirmed here.

---

## Check Overlay Filesystem

The eRVin image may support a read-only overlay filesystem, which protects the SD card from corruption on abrupt power loss (the coach cuts power via the LCD panel switch with no graceful shutdown). Check whether this option is available:

1. SSH into the Pi: `ssh pi@<reserved-IP>`
   - Default eRVin credentials — check myervin.com documentation if login fails
2. Run: `sudo raspi-config`
3. Navigate to **Performance Options** (or **Advanced Options** depending on version) → look for **Overlay File System** or **Overlayfs**
4. If available, enable it and reboot
5. Document the finding below

---

## Confirmed Details

*(Step 6 confirmed complete.)*

| Item | Value |
|---|---|
| Pi WiFi MAC address | B8:27:EB:BD:C6:63 |
| Reserved static IP | 192.168.1.219 |
| Hostname | coachproxyos |
| SSH credentials | pi / ervin2020 — see secrets.md |
| eRVin dashboard accessible | Yes — port 80 shows coach dashboard; port 1880 is Node-RED editor |
| Overlay filesystem available | raspi-config on eRVin image has no overlay option |
| Overlay filesystem enabled | No — deferred to backlog; SanDisk MAX Endurance provides interim protection |
