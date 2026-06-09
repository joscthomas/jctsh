# PiCAN2 Driver Configuration — Pleasure-Way Firefly Interface

Edit `config.txt` on the boot partition to enable the MCP2515 CAN controller and SPI bus.
The MicroSD card should already be in the PC from Step 4 — the boot partition is at D:\.

---

## Edit config.txt

1. Open `D:\config.txt` in a text editor (Notepad is fine)
2. Scroll to the end of the file
3. Add the following three lines:

```
dtparam=spi=on
dtoverlay=mcp2515-can0,oscillator=16000000,interrupt=25
dtoverlay=spi-bcm2835-overlay
```

4. Save the file
5. Safely eject the MicroSD card

**What these lines do:**
- `dtparam=spi=on` — enables the SPI bus the MCP2515 uses to communicate with the Pi
- `dtoverlay=mcp2515-can0,oscillator=16000000,interrupt=25` — loads the MCP2515 driver; `oscillator=16000000` matches the 16MHz crystal on the PiCAN2; `interrupt=25` is the GPIO pin wired to the MCP2515 INT pin on the PiCAN2
- `dtoverlay=spi-bcm2835-overlay` — enables the SPI device tree overlay

---

## RV-C Bitrate — Critical

**The RV-C bus runs at 250kbps — NOT 500kbps.**

Using the wrong bitrate produces no CAN traffic and no error messages. If `candump can0` shows nothing after connecting to the coach, wrong bitrate is the first thing to check.

The `can0` interface must be brought up with exactly:

```bash
sudo ip link set can0 up type can bitrate 250000
```

---

## Persistent can0 at Boot

The eRVin image may bring up `can0` automatically as part of its startup sequence. This will be confirmed during Step 11 (RV-C verification) — run `ip link show can0` after boot to check the interface state.

If `can0` is not up automatically, add it to `/etc/network/interfaces` on the Pi:

```
auto can0
iface can0 inet manual
    pre-up /sbin/ip link set can0 up type can bitrate 250000
    down /sbin/ip link set can0 down
```

Or as a systemd service at `/etc/systemd/system/can0.service`:

```ini
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
```

Enable with: `sudo systemctl enable can0`

Document the finding in the Confirmed Details section below after first boot (Step 6).

---

## Confirmed Details

*(Update after first boot.)*

| Item | Value |
|---|---|
| config.txt lines added | Confirmed Step 5 |
| can0 auto-up at boot | Yes — eRVin image brings up can0 automatically at 250000 bps; no manual configuration needed |
