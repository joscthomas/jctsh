# RV-C Connectivity Verification — Pleasure-Way Firefly Interface

Verify the PiCAN2 receives RV-C traffic from the Firefly network and that eRVin shows live coach data.

---

## Step A — Pre-Flight: Fix CAN Wiring

The Firefly interface cable was wired incorrectly during Step 10 — the wires were in the wrong pin positions in the 3M connector. Re-crimp the drop cable with correct pin assignments before testing RV-C connectivity.

**Correct pin assignments (re-crimp to this):**

| 3M Pin | Signal | CAT5 Wire | PiCAN2 Terminal |
|---|---|---|---|
| 1 | 12V bus | Empty — **do not insert a wire** | — |
| 2 | CAN-H | Blue | CAN-H |
| 3 | CAN-L | Blue-White | CAN-L |
| 4 | GND | Brown | GND |

Use Blue and Blue-White (the same twisted pair) for CAN-H and CAN-L — this gives the bus common-mode noise rejection.

**Procedure:**
1. Switch off coach power at the LCD panel.
2. Unplug the 3M connector from the Firefly Net Port.
3. Crimp a fresh drop cable using a new 3M 37104-A165-00E connector with the pin assignments above.
4. Plug the new connector into the Firefly Net Port.

---

## Step B — Pre-Flight: Install Buck Converter (Proper Switched 12V Power)

The Pi is currently powered from the coach USB outlet. That outlet may not switch off with the LCD panel, which would leave the Pi running in storage. Install the buck converter on the 12V bus so the Pi powers off and on with the rest of the coach.

**Wiring:**

| Connection | Detail |
|---|---|
| 12V tap | Unused wire on the 12V power panel under the rear seat (confirmed Step 10) |
| Inline fuse | 1A, on the positive wire close to the tap point |
| Buck converter 12V+ input | Fused positive wire from tap |
| Buck converter GND input | Coach GND from tap |
| PiCAN2 GND screw terminal | Second GND wire from same coach GND tap (shares terminal with drop cable Pin 4 Brown) |
| Buck converter USB-C output | USB-C to micro-USB cable → Pi micro-USB power port |
| PiCAN2 +Vin screw terminal | **Not used** — no SMPS fitted on this board; leave unconnected |

1. Run the fused 12V+ wire from the tap to the buck converter + input.
2. Run a GND wire from the tap to both the buck converter − input and the PiCAN2 GND screw terminal.
3. Plug the USB-C output cable into the Pi micro-USB port.
4. Remove the coach USB outlet micro-USB cable.
5. Switch coach power on at the LCD panel — confirm Pi boots.
6. Switch coach power off — confirm Pi powers down (green ACT LED stops blinking within ~10 seconds).

---

## SSH Access

| Network scenario | SSH command |
|---|---|
| Home network | `ssh pi@192.168.1.219` |
| JCT-RV hotspot | `ssh pi@192.168.5.1` |
| Tailscale | `ssh pi@100.90.246.43` |

Password: `secrets.md`

---

## Check WiFi Signal Strength

While SSH'd in from the home network, check the Pi's signal level from its installed location under the rear seat:

```
iwconfig wlan0
```

Look for the `Link Quality` and `Signal level` values in the output, e.g.:

```
Link Quality=55/70  Signal level=-55 dBm
```

| Signal level | Quality |
|---|---|
| −50 dBm or better | Excellent |
| −51 to −67 dBm | Good — reliable for dashboard and Tailscale |
| −68 to −75 dBm | Fair — usable but may drop under load |
| −76 dBm or worse | Poor — consider a WiFi extender or antenna |

Document the reading in Confirmed Details below. If signal is below −70 dBm, the eRVin dashboard and Tailscale tunnel may be unreliable when parked at home — note it for follow-up.

---

## Check can0 Interface

After boot, verify the can0 interface came up automatically:

```
ip link show can0
```

Expected: a line containing `can0` with state `UP`.

If the interface is DOWN or not found, bring it up manually:

```
sudo ip link set can0 up type can bitrate 250000
```

**RV-C bitrate is 250000 — not 500000.** Wrong bitrate produces no CAN traffic and no error message. This is the second most common cause of empty candump output.

If manual bring-up works, add it as a systemd service so it persists across reboots:

```
sudo tee /etc/systemd/system/can0.service > /dev/null << 'EOF'
[Unit]
Description=CAN bus interface can0
After=network.target

[Service]
Type=oneshot
ExecStart=/sbin/ip link set can0 up type can bitrate 250000
ExecStop=/sbin/ip link set can0 down
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable can0
sudo systemctl start can0
```

---

## Capture RV-C Traffic

```
candump can0
```

Expected: a continuous stream of CAN frames within a few seconds. Example:

```
can0  18EF4644   [8]  01 00 00 00 00 00 FF FF
can0  19FCA644   [8]  7D 7D 7D 7D FF FF FF FF
can0  19F21244   [8]  00 80 00 80 FF FF FF FF
```

Press Ctrl+C to stop. Copy 4–6 lines of output to the Confirmed Details section below.

**If no output:**
1. Confirm the 3M connector is crimped with correct pin assignments (Step A) and fully seated in the Firefly Net Port socket.
2. Confirm can0 is UP (`ip link show can0`).
3. Confirm JP3 jumper is absent on the PiCAN2.
4. Confirm bitrate is 250000 (`ip link show can0` shows the configured bitrate in the output).

---

## Verify eRVin Dashboard — Live Data

1. Open Chrome on a Pixel.
2. Navigate to `http://192.168.1.219` (home network) or `http://192.168.5.1` (JCT-RV hotspot).
3. Confirm live Firefly data is appearing — tank levels, battery voltage, light states.

**Spot checks:**
- Turn a light on at the Vegatouch touch panel. Confirm it shows ON in the eRVin dashboard.
- Turn the same light off. Confirm dashboard updates to OFF.
- Check fresh water tank level against known state (visual estimate of fill level).
- Note the battery voltage reading — should be 12.x–13.x V depending on charge state.

---

## Confirm can0 Auto-Up at Boot

Reboot the Pi and check whether can0 came up automatically without the manual `ip link set` command:

```
sudo reboot
```

After reboot, SSH in and run:

```
ip link show can0
```

If state is UP without any manual intervention, eRVin handles can0 automatically — document this in pican2-config.md. If state is DOWN, the systemd service above is required.

---

## Confirmed Details

*(Update after Step 11 confirmed complete.)*

| Item | Value |
|---|---|
| WiFi signal level (dBm) — preliminary (pre-mount) | −53 dBm, Link Quality 57/70 |
| WiFi signal level (dBm) — final (post-mount) | recheck after permanent mount |
| CAN wiring corrected (same twisted pair) | Yes — Blue/Blue-White pair for CAN-H/CAN-L |
| Buck converter installed and switched power verified | Yes |
| can0 auto-up at boot | Yes — eRVin image handles it automatically |
| can0 systemd service installed | Not needed |
| candump shows RV-C traffic | Yes — confirmed |
| Sample candump output | `can0  19FFFD9E   [8]  01 FF 08 01 00 8E 35 77` |
| eRVin dashboard shows live data | Yes |
| Light spot check (Vegatouch → dashboard) | Pass — Entry Light toggled on Vegatouch, reflected on dashboard |
| Control spot check (dashboard → coach) | Pass — Water pump turned on from eRVin dashboard, pump activated |
| Battery voltage reading | 13.2 V — matches Vegatouch panel |
| Grey water tank reading | 25% — matches Vegatouch panel |
| LPG reading | ~80% — matches Vegatouch panel |
| Fresh water tank reading | Not checked |
| Any entities missing or reading incorrectly | None observed |
