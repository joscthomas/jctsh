# Hiking Monitor — WiFi Configuration (Step 21)

## Networks

The device tries networks in order — home WiFi first, hotspot second.

| Priority | SSID | When used |
|---|---|---|
| 1 | `JCTnet1` | At home — normal home mode, live data, replay |
| 2 | `JCT Hotspot` | In the field — hotspot sync after a hike |

Fallback AP (`hiking-monitor-fallback`) activates only if both networks fail at boot.

## Hotspot Setup

**SSID and password are fixed.** Changing them after flashing requires a re-flash.

The SSID `JCT Hotspot` is device-independent — any phone's hotspot can be used as long as its SSID and password match what's in `secrets.yaml`. No re-flash needed to switch to a different phone.

| Field | Value |
|---|---|
| SSID | `JCT Hotspot` |
| Band | 2.4 GHz (ESP32 does not support 5 GHz) |
| Password | stored in `credentials.local.md` |

To set on Pixel 10 Pro XL: Settings → Network & internet → Hotspot & tethering → Wi-Fi hotspot → set name to `JCT Hotspot` → set password → turn on.

## Hotspot Sync Workflow

1. At the trailhead or after returning from a hike: enable Pixel hotspot
2. Turn hiking-monitor switch OFF then ON (or plug in USB for upload mode)
3. Device connects to hotspot → connects to home Mosquitto broker over cellular
4. SPIFFS replay triggers automatically — identical to home sync
5. Replayed readings appear in Google Sheets with original hike timestamps
6. Log dashboard shows `Replaying N hike readings...` then `Hike log replay complete.`
7. Turn switch OFF when done

## Broker Reachability from Hotspot (open issue)

The ESP32 is not a Tailscale client. When it connects via the Pixel hotspot, its traffic goes out over cellular as regular internet traffic — it cannot reach Tailscale IPs or private LAN IPs.

| Address | Reachable from hotspot? |
|---|---|
| `raspberrypi.local` | No — mDNS is link-local only |
| `192.168.1.117` | No — private LAN, not internet-routable |
| `100.70.162.24` (Tailscale) | No — only accessible from other Tailscale clients |

**Resolution options (not yet implemented):**
- Port-forward port 1883 on the home router → Pi (requires dynamic DNS or static public IP)
- Tailscale Funnel (exposes Pi services to the internet via Tailscale relay)
- Accept limitation: hotspot only used at home for testing; hike data always syncs on returning home over JCTnet1

**Current behavior:** If the ESP32 connects via hotspot and cannot reach the broker, MQTT connect will timeout. The device will stay connected to the hotspot but no replay will occur. No data is lost — SPIFFS log is intact and replays when JCTnet1 is available.

- **Cellular data volume:** trivially small — ~200 bytes/reading × 180 readings/6-hour hike = ~36 KB per replay
- **Heartbeat publishes on hotspot connection** — watchdog will show device online; this is correct
- **GPS Track upload:** GPSLogger posts directly to Google over cellular — no Pi involved; works regardless of hotspot sync status

## secrets.yaml Entries

```yaml
hotspot_ssid: "JCT Hotspot"
hotspot_password: "<from credentials.local.md>"
```
