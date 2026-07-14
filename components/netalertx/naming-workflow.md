# NetAlertX — Device Checking & Naming Workflow

**Purpose:** a repeatable process for periodically reviewing NetAlertX and naming new devices, so the tool gets actually used rather than set up once and left idle — the exact risk CARD-0063 flags as the reason further MQTT/dashboard integration work is deliberately parked until this workflow is proven out in practice.

---

## Access

URL: `http://photo-server.local:20211` (or `http://192.168.1.165:20211`)
Password: see `credentials.local.md` → NetAlertX (CARD-0059)

---

## Cadence

**Weekly.** Frequent enough to catch new devices while they're still easy to place ("what did I just plug in") without becoming a chore. Adjust if it turns out too frequent or too sparse in practice.

## Steps

1. **Open the dashboard** and check the device/presence list for anything flagged new or unknown since the last check.
2. **For each new device:**
   - Check NetAlertX's own vendor guess (OUI-based, derived from the MAC prefix) as the first clue.
   - Cross-reference the MAC against `jctsh-network.md`'s device table. If it matches a JCTsh-managed device (ESP32 fleet, Pi, M8, router, etc.), name it **identically** in NetAlertX — don't invent a second name for a device that already has one in the canonical table.
   - If it's not a JCTsh device, identify it from context (a new phone, a smart plug, a guest's device) where possible. If it can't be identified, rule out MAC randomization before assuming it's genuinely new (see gotcha below).
   - Assign a friendly name (and icon/group, if useful) in NetAlertX's UI.
3. **Devices that can't be identified at all:** treat as worth a closer look, not a shrug-and-ignore — this is the actual security-relevant case NetAlertX exists to catch (an unrecognized device on the LAN).

## Identification techniques (found useful in practice, 2026-07-13/14)

- **Google Home app MAC cross-reference.** For Chromecasts, Google/Nest speakers, and displays: open the device in the Google Home app → its settings (gear icon) → scroll to **"Device information"** — shows both IP and MAC address. Match the MAC directly against NetAlertX's list, not the IP — MAC stays fixed while IP can shift on DHCP renewal.
- **Google Nest app MAC cross-reference.** Nest-branded devices (Nest Protect, thermostats, cameras) live in the separate **Google Nest app**, not Google Home — same per-device "Device information" pattern applies there. This is what positively identified two "(name not found)" Google-vendor entries as Nest Protect smoke detectors.
- **OUI-elimination for non-obvious devices.** When a device's vendor tag doesn't match its actual purpose (e.g. the Rain Bird ESP-TM2 irrigation module showing up as "Espressif Inc.," since its WiFi module is Espressif-based, not "Rain Bird"), identify by process of elimination: it's the only unnamed device carrying that vendor tag once every already-known device sharing the same vendor is excluded.

## Known gotcha — MAC randomization

Modern Android and iOS phones randomize their MAC address per network by default. This can make the *same physical phone* reappear as a "new device" repeatedly across checks, which is confusing and can mask genuinely new devices in the noise. If a phone keeps showing up as new:

- Check that phone's WiFi settings for a per-network "Use randomized MAC" toggle.
- Switch it to "Use device MAC" (or equivalent) for the home network specifically, so it gets one stable identity NetAlertX can actually track long-term.

## Relationship to `jctsh-network.md`

`jctsh-network.md` remains the canonical source for JCTsh-managed devices — DHCP reservations, ESPHome hostnames, MACs. NetAlertX is scoped to *everything else*: third-party/commercial devices the router won't let you rename (Ring, Ecobee, Cast devices, guest phones, etc. — the original motivation for CARD-0059). Don't let naming decisions drift between the two systems for the same device; NetAlertX mirrors the existing name for anything already in the canonical table, and only originates new names for devices that aren't.
