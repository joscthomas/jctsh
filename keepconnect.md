# KeepConnect Router Rebooter

Standalone network-resilience device — not a JCTsh MQTT component. Watches internet
connectivity and power-cycles the router/modem when it detects an outage. No integration
with Mosquitto, Node-RED, or Home Assistant.

## Device Identity

| Attribute | Value |
|---|---|
| Product | KeepConnect Router Rebooter (Johnson Creative) |
| Device ID | KeepConnect-27F8 |
| Hostname | esp32-5227F8 |
| MAC | 34-98-7A-52-27-F8 |
| Config UI | `192.168.4.1` (device's own AP mode) or DHCP-assigned IP once on home network |

## Network Identity

| Attribute | Value |
|---|---|
| IP | 192.168.1.108 — DHCP reservation on router (bound to MAC above), not a static IP set on the device |
| Subnet Mask | 255.255.255.0 |
| Default Gateway | 192.168.1.1 |
| DNS Server 1 | 192.168.1.1 (or 8.8.8.8) |
| DNS Server 2 | 1.1.1.1 |
| "Enable Static IP" (device setting) | Unchecked — router-side DHCP reservation handles consistent assignment, avoiding a duplicate source of truth |

See `jctsh-network.md` for the full device IP/MAC table.

## Physical Setup

Confirmed 2026-07-08: in the equipment closet, KeepConnect's switched outlet controls the
router only. Every other device in the closet — Raspberry Pi, GMKtec M8 (photo-server /
Immich), SmartThings hub, and other closet gear — is on a separate surge-protected power
strip, never power-cycled by this device.

**Rationale for router-only scope:**
- Immich relies on PostgreSQL; a hard power cut mid-write risks database/filesystem
  corruption (worse on SD card than SSD).
- KeepConnect triggers on internet loss, but Immich and SmartThings function fine on
  LAN during ISP outages — no need to reboot them.
- A SmartThings hub reboot forces a Zigbee/Z-Wave mesh rebuild, causing unnecessary
  automation downtime.

## Configuration

### Mode

| Setting | Value |
|---|---|
| Operating mode | Master, Hybrid comms (KeepLink + LAN) |
| Monitor mode | Require Full TCP/HTTPS Success (switched from "Keep Connect HTTPS Roundtrip" to avoid dependency on the vendor's own server uptime) |
| Primary Test Domain | google.com |
| Backup Test Domain | cloudflare.com (kept distinct from primary — testing the same domain twice defeats the purpose of a backup check) |
| Ignore DNS failures if ping 8.8.8.8 works | Unchecked |
| Loss of WiFi Reset Mode | Reboot/Retry before Resetting |

Note: the "200 kcSuccess" suffix seen on the original placeholder fields is specific to
Roundtrip mode's string-matching check against Johnson Creative's own servers — not
applicable under TCP/HTTPS mode.

### Timing

| Setting | Value |
|---|---|
| Check interval | 5 min |
| Backup check delay after primary failure | 1 min |
| Power-cut duration | 30 sec |
| Reconnect wait after reset | 4 min (increased from default 3 min, to give the modem/router more headroom to fully sync, e.g. DOCSIS ranging) |
| Power-on delay | 0 sec |
| Max continuous resets | 3, then backs off to retry every 4 hrs during a sustained outage |

### Scheduled Auto Reset

| Setting | Value |
|---|---|
| Schedule | Every 7 days at 3 AM |
| Timezone | UTC-7 US Mountain, DST disabled (correct for Arizona) |

### Notifications

| Setting | Value |
|---|---|
| SMS | Enabled |

### Misc

| Setting | Value |
|---|---|
| Wireless mode | 802.11b/g/n |
| Reduce Wireless Transmit | Unchecked |

## Related: Pi/M8 Scheduled Reboot

Resolved 2026-07-08 (CARD-0035) — see `SOFTWARE-ENVIRONMENT.md` (Pi) and
`components/photo-server/operations.md` (M8) for the weekly systemd-timer reboot
schedule, independent of KeepConnect's own reset schedule. First scheduled run:
Mon 2026-07-13.
