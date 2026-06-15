# Operations — Pleasure-Way Firefly Interface

Day-to-day use of the eRVin dashboard in the 2018 Pleasure-Way Lexor FL.

---

## Accessing the Dashboard

### At home (RV parked, connected to JCTnet1)

Open a browser on any device on the home network:

```
http://192.168.1.219
```

### Away with phone signal (Tailscale)

The Pi connects to your Pixel's hotspot and establishes a Tailscale tunnel. Use either phone or any Tailscale-connected device:

```
http://100.90.246.43
```

Both Pixels have this address bookmarked on the home screen.

### Away without phone signal (JCT-RV local hotspot)

When the Pi has no known network available, it broadcasts a local hotspot named **JCT-RV**. Connect your phone to JCT-RV, then open:

```
http://192.168.5.1
```

Both Pixels are saved to JCT-RV and will connect automatically.

---

## What the Dashboard Controls

| System | Status | Control |
|---|---|---|
| Fresh water tank | Level % | — |
| Gray water tank | Level % | — |
| Black water tank | Level % | — |
| Coach battery | Voltage | — |
| Lights | On/off per circuit | On/off |
| Water pump | On/off | On/off |
| Generator | Running/stopped | Start/stop (untested) |
| Sofa | Extend/retract | Extend/retract |

### Not available from dashboard

| System | Reason |
|---|---|
| Vent fan | Fan-Tastic uses Firefly rolling-code authentication — Pi cannot issue authenticated commands; use Vegatouch panel |
| Awning | Not added to dashboard; use Vegatouch panel |
| Shore power status | Xantrex Freedom Xi is not on the RV-C bus |
| Inverter status | Same reason |
| Charging amps | No DC current sensor on the RV-C bus |

---

## Network

The Pi uses concurrent STA+AP mode — `wlan0` connects to a known WiFi network while `uap0` broadcasts JCT-RV **simultaneously and permanently**. JCT-RV is always available regardless of what network `wlan0` is connected to.

`wlan0` connects in this priority order:

1. **JCTnet1** (home WiFi) — preferred
2. **Your Pixel hotspot** — fallback when away

If neither network is in range, `wlan0` is idle. JCT-RV remains up in all cases.

`wlan0` switching between known networks takes up to 60 seconds. No reboot required.

---

## Pi Power

The Pi runs from coach 12V power. It powers on and off with the coach power switch on the LCD panel — not the red battery disconnect key.

- **Boot time:** 60–90 seconds after coach power on
- **Shutdown:** coach power off; no graceful shutdown needed (SanDisk MAX Endurance card tolerates hard power loss)

---

## Troubleshooting

### Dashboard won't load at home

1. Confirm the RV is powered on (Vegatouch screen lit)
2. Wait 90 seconds after power-on for boot to complete
3. Try `http://192.168.1.219` from a device on JCTnet1
4. SSH to the Pi: `ssh pi@192.168.1.219` — if this works, eRVin may need a restart

### Dashboard loads but shows stale or no data

CAN bus may have lost connection. On the Pi:

```
candump can0
```

Should show a continuous stream of RV-C frames. If silent, check the 3M connector at the Firefly Net Port.

### Pi not reachable on home network

Check `192.168.1.219` is in the router's DHCP lease table. If the Pi is not visible:

1. Confirm coach power is on
2. Allow 2 minutes for boot and WiFi association
3. If still absent, connect directly to JCT-RV hotspot and access via `http://192.168.5.1`

### JCT-RV hotspot not appearing

The hotspot only activates when no known network is in range. If you are at home and the Pi is on JCTnet1, JCT-RV will not be broadcast.

### Robin's Pixel won't stay connected to JCT-RV

Reboot the Pixel. This resolved a transient Android network-stack issue observed during setup.

---

## SSH Access

```
ssh pi@192.168.1.219        (home network)
ssh pi@100.90.246.43        (Tailscale, from anywhere)
ssh pi@192.168.5.1          (JCT-RV hotspot)
```

Credentials in `secrets.md`.
