# JCTsh Bedside Clock — Phase 1 Discovery and Feasibility
**Author:** Joseph C Thomas (JCT)
**Purpose:** Phase 1 planning document for the bedside-clock component — a battery-powered, tap-to-wake bedside clock for the Pleasure-Way camper van that syncs accurate time from Joseph's Pixel via Bluetooth LE.
**Version:** 1.2
**Version description:** Superseded the BLE Current Time Service sync approach after discovering Android does not natively run a CTS server — there is no built-in Android system service exposing time over BLE for a peripheral to read; the BLE plan as originally conceived was not viable without a custom Android app. Replaced with: DS3231 as the sole continuous time source (proven highly accurate on its own, ~1-2 minutes/year drift even uncalibrated), corrected only on a long-press-triggered WiFi hotspot + NTP sync, used solely to correct timezone when crossing zones (not for routine drift correction, which the DS3231 does not need). This reintroduces a narrow, occasional WiFi dependency, revising the original "no WiFi" goal — addressed explicitly below.

---

## Goal

Build a small bedside clock for the camper van that stays accurate no matter where the van travels, without depending on van house power or cellular connectivity. The clock should be unobtrusive at night and require minimal manual intervention when crossing time zones — limited to an occasional deliberate resync action, not routine upkeep. (Revised from the original "no WiFi" goal — see Time sync approach below for why a narrow, occasional WiFi dependency was reintroduced.)

---

## What Was Confirmed in Discovery

### Time sync approach: superseded — BLE Current Time Service was not viable

The original plan (Option A) assumed an ESP32 could read the current time directly from the Pixel over BLE, using the standard Bluetooth Current Time Service (CTS) profile. On investigation, this assumption was incorrect: stock Android does not run a CTS server. CTS is typically implemented by a *peripheral* device (e.g., a fitness tracker) advertising time to a *central* device like a phone — not the reverse. Making a phone expose CTS to an external peripheral would require a custom Android app; no built-in system service does this.

**Revised approach:**
- **DS3231 RTC is the sole, continuous time source.** Research into DS3231 accuracy confirmed it is highly stable on its own: the chip is rated ±2 ppm (0°C–40°C) to ±3.5 ppm (-40°C–85°C), and real-world long-term tests report drift as low as 1-2 minutes per year even with no calibration of the aging offset register. At the timescales relevant to a bedside clock (weeks to months between trips), this drift is imperceptible — DS3231 does not need routine resyncing for accuracy.
- **The only thing the DS3231 cannot self-correct is timezone**, since it has no awareness of where the van physically is. This reframes the sync problem: it was never really about keeping the clock "accurate" over time (DS3231 already does that), it was about telling the clock which timezone it's in.
- **Resolution: WiFi hotspot + NTP sync, triggered manually via long-press on the wake button**, used only when crossing time zones — not on any routine schedule. Joseph confirmed this is an acceptable interaction: turning on the phone's hotspot once per zone change and long-pressing the clock's button to trigger a resync.

This was a deliberate, explicit revision of the original "zero network dependency" design principle established in Phase 3. The tradeoff was evaluated for power and complexity impact:
- **Power:** negligible. A WiFi connect + NTP fetch + disconnect cycle takes roughly 5-10 seconds at WiFi's higher draw, but happens only a few times per year (timezone changes), not nightly — effectively a rounding error against the annual power budget already established by the deep-sleep architecture.
- **Complexity:** real but contained. Firmware needs two distinct wake paths — short-press (DS3231 read, display, sleep, as before) and long-press (WiFi connect, NTP fetch, update DS3231, disconnect, sleep) — with clear OLED feedback during resync ("connecting...", "synced", "failed, try again") and a connection timeout/retry path for when the hotspot isn't on yet. Hotspot SSID/password storage on the ESP32 is a secrets-management detail to resolve against `JCTsh-Build-Standards.md` conventions in Phase 4/5.

This is a narrower network dependency than any other JCTsh component carries — no MQTT, no SmartThings, no Home Assistant, no continuous connectivity — but it is not truly zero-footprint, which was the original Phase 3 framing. That framing is corrected here.

### Power source: battery, not van house power
Initial discussion considered powering from 12V van house power, which would have allowed continuous operation without deep sleep. Joseph specified battery power instead. This changes the design materially — continuous operation on battery would drain a LiPo in hours, so the component must spend almost all of its time in deep sleep and wake only briefly to update the display.

### Wake method: tap or motion (settled on simple pushbutton)
Both tap detection and accelerometer-based motion wake were discussed. A momentary pushbutton was settled on as the wake method — simple, reliable, low part count, and appropriate given Joseph expects to use the clock only once to three times per night.

### Display: e-ink ruled out, OLED selected
E-ink was excluded by Joseph at the outset. Because the design now requires deep sleep between wakes, a display with no persistent memory (such as a 7-segment TM1637) was also ruled out, since it goes blank the instant the ESP32 sleeps and offers no advantage over a display that can be fully powered off. A 1.3" I²C OLED (SSD1306 driver) was selected:
- Zero power draw while the ESP32 is in deep sleep — the display itself is powered off, not merely dimmed
- Instant-on when the ESP32 wakes
- Readable in the dark at low brightness
- Same I²C interface Joseph already has experience with (BME280, BH1750)
- 1.3" preferred over 0.96" for larger, easier-to-read digits on a groggy middle-of-the-night glance

### Real-time clock: DS3231 as the sole authoritative time source

Joseph rejected "last known time" as a fallback display, which is what originally brought the DS3231 RTC into the design. With the BLE sync approach superseded (see above), the DS3231's role has actually become more central, not less: it is now the clock's only continuous time source, correct on its own between deliberate timezone resyncs. The display always reads from the DS3231 — there is no scenario where the clock shows a stale "last known" value, since the DS3231 keeps accurate time independently regardless of phone proximity or connectivity.

A CR2032 coin cell backup for the DS3231 was discussed. It is not load-bearing in this design: the LiPo remains continuously connected (charging happens without disconnecting the battery), so the DS3231's connection to power doesn't depend on the coin cell. The coin cell is retained for insurance — the case of a fully drained LiPo — but is not a design-critical requirement. Most DS3231 modules ship with the holder and cell already populated, so it is left in by default.

### Display format
12-hour time, with date displayed in a smaller line beneath. Day-of-week is also feasible given the screen real estate on a 1.3" OLED with a two-line layout.

### Power budget reasoning
Joseph wants the ESP32's actual power characteristics to dictate battery sizing rather than picking a battery first. Working through realistic usage (2–4 wake cycles per night, deep sleep at ~10–20µA between wakes, brief BLE-scan-and-display wake cycles of roughly 20–35 seconds at ~80–100mA average), the EEMB 603449 LiPo (1100mAh) already used in the hiking monitor is comfortably sufficient — even after derating heavily for BLE overhead, LiPo aging, and boost converter inefficiency, multi-month runtime between charges is expected. This is the same cell and TP4056 charging approach Joseph already uses, so no new battery part is required.

---

## What Is Proven vs. Uncertain

**Proven / well-understood:**
- DS3231 timekeeping accuracy is well-documented and independently verified: ±2-3.5 ppm rated, with real-world long-term tests showing as little as 1-2 minutes/year drift uncalibrated — confirmed sufficient as the clock's sole continuous time source with no routine resync needed
- DS3231 RTC behavior and I²C wiring — well-documented part, standard I²C interface consistent with Joseph's existing sensor experience (BME280, BH1750)
- SSD1306 OLED I²C wiring and library support — extremely common, well-documented
- EEMB 603449 LiPo + TP4056 charging — already proven in the hiking monitor build
- ESP32 deep sleep current draw in the 10–20µA range is well-documented and consistent across DevKitC-32 boards
- ESP32 WiFi + NTP sync is a standard, well-documented pattern — no novel implementation risk

**Uncertain / to confirm in Phase 2 or bench testing:**
- Real-world wake-cycle current draw — bench measurement will refine the power budget beyond the rough estimate above
- Final enclosure approach for a bedside form factor (consult `JCTsh-Build-Standards.md` enclosure convention in Phase 2)
- Hotspot SSID/password storage approach on the ESP32 — needs to be checked against `JCTsh-Build-Standards.md` secrets-management convention in Phase 4/5
- Long-press vs short-press button debounce/discrimination logic — needs bench validation to confirm reliable, unambiguous detection

---

## Key Components Identified

| Component | Role |
|---|---|
| ESP32 DevKitC-32 | Main controller, WiFi/NTP client (timezone resync only), deep sleep management |
| DS3231 RTC module | Sole continuous time source, accurate independently between resyncs — **not on hand, must be purchased** (see Phase 2 doc) |
| 1.3" I²C OLED (SSD1306) | Display, powered fully off during sleep |
| Momentary pushbutton | Wake trigger |
| EEMB 603449 LiPo (1100mAh) | Battery power |
| TP4056 charge module | USB-C charging without disconnecting battery |
| Boost converter (3.7V → 5V) | Power regulation, consistent with existing builds |
| CR2032 coin cell | DS3231 backup (non-critical insurance) |

---

## Next Step

Phase 2 (Hardware Selection) is complete — see `bedside-clock-hardware-selection.md` for the inventory scan results, confirmed bill of materials, and enclosure decision. Phase 3 (Architecture and Integration Design) is also complete, but its original "zero network footprint" framing has since been revised by this document (v1.2): bedside-clock now has a narrow, occasional WiFi dependency (hotspot + NTP, long-press triggered, timezone resync only) — still no MQTT, no SmartThings, no Home Assistant, no continuous connectivity, and no watchdog registration, but not literally zero network footprint as originally stated. Phase 4 (Claude Code instruction set) should account for this revised sync architecture: short-press wake (DS3231 read/display/sleep) and long-press wake (WiFi/NTP resync) as two distinct firmware paths.
