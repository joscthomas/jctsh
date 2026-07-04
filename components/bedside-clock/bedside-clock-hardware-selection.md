# JCTsh Bedside Clock — Phase 2 Hardware Selection
**Author:** Joseph C Thomas (JCT)
**Purpose:** Phase 2 planning document for the bedside-clock component — on-hand parts inventory scan, confirmed bill of materials, and enclosure decision.
**Version:** 1.3
**Version description:** Applied JCTsh-Build-Standards.md §2.14 (Battery-Powered Component Safety Standards) — added compliance table, corrected stale spare-battery count (1 remaining, not 2, after the hiking-monitor battery swap), flagged firmware low-battery cutoff as a required Phase 4 deliverable, and raised the boost-vs-direct-LDO architecture (§2.14 point 7) as an open decision for Joseph.
**Related files:** bedside-clock-planning.md (Phase 1)

---

## Inventory Scan (First Action of Phase 2)

Per the planning pattern, `JCTsh-Parts-Inventory.md` was scanned before any purchasing discussion began.

| Needed | On hand? | Inventory entry |
|---|---|---|
| ESP32 DevKitC-32 | Yes — 2 remaining | Bag 1 (hiBCTR 6-pack) |
| EEMB 603449 LiPo, 1100mAh | Yes — **2 remaining** (physically recounted 2026-07-03 after the hiking-monitor battery swap — trust this count over prior inventory-doc arithmetic) | Bag 7 |
| TP4056 charge module | Yes — 4 remaining | Bag 8 |
| Boost converter (3.7V → 5V) | Not separately needed | TP4056 module (Bag 8) has integrated step-up; confirmed sufficient on its own — no additional boost module was required for the hiking-sensor build, and the same applies here |
| Momentary pushbutton (PCB-mount) | Yes | Plastic Box, QTEATAK 6×6mm micro momentary tact assortment |
| Momentary pushbutton (panel-mount) | No | Not in inventory — ordered: Twidec PBS-33B-BK-X, 12mm momentary, prewired (see Enclosure section) |
| DS3231 RTC module | No | Not in inventory. (Phase 1 doc originally and incorrectly stated this was on hand at Bag 19 — Bag 19 is actually BH1750 light sensors. Corrected in Phase 1 doc v1.1.) |
| 1.3" I²C OLED display | No | Not in inventory — no OLED of any kind on hand |
| CR2032 coin cell | No | Not in inventory — typically ships pre-installed on DS3231 modules |

**Correction carried forward from Phase 1:** the DS3231 was incorrectly assumed on-hand in the original Phase 1 doc. It is not — confirmed via this inventory scan. Phase 1 doc has been corrected to v1.1.

---

## Hardware Research and Selection

### DS3231 RTC module

Three categories of product were considered:

| Option | Assessment |
|---|---|
| Generic AT24C32 combo boards (Rakstore, Aideepen, AITRIP, etc.) | Rejected. These bundle an unneeded AT24C32 EEPROM, and a verified product review documented a real safety hazard: some of these boards ship wired to trickle-charge the coin cell, making it unsafe to install a standard non-rechargeable CR2032 without first modifying the board to remove a diode or resistor. One reviewer measured 4.8V at the battery terminals from a 5V supply. This is the same class of risk as the BMP280-sold-as-BME280 counterfeit incident on the front-porch-temp-sensor build, and was avoided for the same reason. |
| Adafruit DS3231 Precision RTC Breakout | Considered. Known-good, well-documented, single-unit board. Rejected in favor of the HiLetgo pack below — same DS3231 chip, no meaningful accuracy advantage for this application, and higher per-unit cost with no spares. |
| **HiLetgo 5-pack (selected)** | **Selected.** Adapts to both 3.3V and 5V systems with no level conversion needed. Provides continuous timing battery backup and full clock/calendar function with leap year compensation through 2100. Timing accuracy of ±5 PPM (±0.432 sec/day) across -40°C to +85°C, both 1Hz and 32.768kHz outputs, 400kHz I²C. No reported trickle-charge/CR2032 safety issue. Four spares remain for van sensor suite, p-w-firefly, or future timestamping needs. |

**Selected:** HiLetgo 5pcs DS3231 High Precision RTC Module — Amazon ASIN B01N1LZSK3.

### 1.3" OLED display

The 1.3" size in 128×64 resolution is dominated by the **SH1106** driver chip in practice, even though most listings advertise "SSD1306-compatible." This is a real distinction, not just labeling — SH1106 has a 132×64 internal buffer versus SSD1306's native 128×64, and requires a library or display-driver configuration that explicitly supports SH1106 (e.g., Adafruit_SH1106, or U8g2 configured for SH1106). A stock SSD1306 library will not initialize correctly. This must be respected in firmware during Phase 5 — flagged for the Claude Code instruction set.

| Option | Assessment |
|---|---|
| hiBCTR 1.3" SH1106 module (single) | Considered. Same brand family as the on-hand ESP32 6-pack. Functionally equivalent to the option below. |
| MakerFocus 2-pack | Considered (Joseph-proposed). SH1106 driver, 0.06W, 3.3V/5V. Functionally equivalent to the Hosyond option; smaller pack size at similar per-unit cost. |
| **Hosyond 5-pack, white (selected)** | **Selected** (Joseph-proposed). SH1106 driver, 128×64, 3.3V–5V, >160° viewing angle. 4.4-star rating across 69 reviews. Manufacturer documentation explicitly confirms the SH1106-vs-SSD1306 library distinction, consistent with the caveat above. Five units gives four spares for future builds — same spares logic applied to the DS3231 selection. |

**Selected:** Hosyond 5 Pcs 1.3" IIC I2C OLED Display Module, SH1106, white — Amazon ASIN B0C3L7N917.

**I²C address compatibility confirmed:** OLED defaults to 0x3C; DS3231 sits at a fixed 0x68 (with companion EEPROM, if present, at 0x57). No address conflict — both share the ESP32's I²C bus without remapping.

---

## Battery Safety Standards Compliance (JCTsh-Build-Standards.md §2.14)

Bedside-clock uses the same EEMB 603449 LiPo + TP4056 charge/boost combo as hiking-monitor, whose original battery failed in the field (2026-07-03) with no advance warning — the incident that produced §2.14. Since bedside-clock hasn't been built yet, these can be designed in from the start rather than retrofitted:

| §2.14 requirement | Status for bedside-clock |
|---|---|
| 1. PCM-protected cell | **Satisfied.** EEMB 603449 confirmed PCM-protected (overcharge/over-discharge/overcurrent/short-circuit) and UN 38.3 compliant — same cell, same confirmation as hiking-monitor. |
| 2. Firmware low-battery cutoff | **Not yet designed — required for Phase 4.** The Claude Code instruction set must include a `battery_v`-watching cutoff (3.4V threshold) forcing safe shutdown, following the hiking-monitor pattern (`components/hiking-sensor/hiking-sensor.yaml`, `low_battery_shutdown` script), adapted for the OLED display instead of e-ink (OLED does not hold a frame with power removed, so the "recharge now" warning strategy needs rethinking for this display type — likely just show it briefly then power down, rather than relying on a persistent held frame). |
| 3. Charging safety (fireproof bag, no unattended charging, never charge a damaged cell) | Operational practice — applies regardless of hardware, carries forward automatically. |
| 4. Storage (40-60% charge for spares) | Applies to the 1 remaining spare EEMB cell in Bag 7 shared between projects. |
| 5. Disposal | Applies if/when this cell is ever retired. |
| 6. Connector polarity verification | **Required at wiring/perfboard step (Phase 5+)** — verify with multimeter before first connection, do not assume color convention. |
| 7. Prefer direct LiPo-to-LDO over boost-then-buck (recommended default, not mandatory) | **Decided (2026-07-03): keep the on-hand TP4056+boost module.** No new parts needed — uses existing Bag 8 stock, matches the hiking-monitor pattern. Bedside-clock spends most of its time on a shelf near USB power (only battery-powered when moved to the bed during travel/storage), so the over-discharge risk that motivated point 7 for the hiking-monitor is lower here. |

---

## Enclosure Decision

Per Build Standards, the open standoff mount is the default convention for ESP32/perfboard projects, reserved for workshop-adjacent installs (e.g., garage radar, front-porch sensor) where an open-board appearance is acceptable. A full enclosure is the documented exception, reserved for components requiring weather resistance or a finished appearance outside the workshop.

**Decision: full enclosure, not open standoff mount.** Bedside-clock sits in the van's sleeping area, is handled and operated by touch at night, and needs a clean finished face rather than exposed perfboard and wiring next to where Joseph and Robin sleep. This is a clear case for the documented exception.

### Enclosure parameters confirmed

- **Mounting:** none. Freestanding — sits flat on a shelf in normal use, moved to the bed during travel or storage. No screw bosses, no wall-mount hardware, no latching mechanism.
- **Stability:** footprint wide enough relative to height to resist tipping from minor bumps or van movement while parked.
- **Material:** PLA or PETG. Indoor, climate-controlled van interior only — no weather exposure, so ASA is not required for this component (unlike the front porch sensor or hiking monitor enclosures).
- **Printer:** Bambu A1 Mini (Xerocraft) — consistent with existing PLA/PETG enclosure work.
- **Front face:** OLED viewing window, plus panel-mount pushbutton.
- **Side or back face:** USB-C cutout for TP4056 charging access without opening the case.
- **Pushbutton mounting:** panel-mount, not through-hole. On-hand pushbuttons (Plastic Box, QTEATAK assortment) are PCB-mount only and unsuitable for a panel-mount installation. Selected and ordered: Twidec PBS-33B-BK-X, 12mm momentary, normally-open, prewired with pre-soldered leads — chosen for a more positive tactile click and better durability under repeated nightly use by feel in the dark, versus a through-hole press against a PCB-mount button. Sold as a 6-pack; spares available for future panel-mount needs.
- **Internal layout:** standoffs or friction-fit retention for ESP32, DS3231, and LiPo within the enclosure interior.
- **Access:** case opens for assembly and service only — no need for quick access in normal use.

### Open sourcing item

None remaining. Panel-mount pushbutton selected and ordered (Twidec PBS-33B-BK-X) — see Pushbutton mounting above.

---

## Confirmed Bill of Materials

| Component | Source | Status |
|---|---|---|
| ESP32 DevKitC-32 | Bag 1 | On hand |
| EEMB 603449 LiPo, 1100mAh | Bag 7 | On hand |
| TP4056 charge/boost module | Bag 8 | On hand |
| DS3231 RTC module (HiLetgo 5-pack) | Amazon B01N1LZSK3 | To purchase |
| 1.3" OLED, SH1106 (Hosyond 5-pack, white) | Amazon B0C3L7N917 | To purchase |
| Panel-mount momentary pushbutton (Twidec PBS-33B-BK-X) | Amazon | Ordered |
| 3D-printed enclosure (PLA/PETG) | Xerocraft Bambu A1 Mini | To design/print |

---

## Next Step

Phase 2 is fully complete — all BOM items are either on hand or ordered. Phase 3 (Architecture and Integration Design) has also been completed in conversation, though its original "zero network footprint" framing was subsequently revised in Phase 1 doc v1.2: the originally planned BLE time sync from Joseph's phone was found not viable (stock Android does not run a CTS server), and was replaced with the DS3231 serving as the sole continuous time source, corrected only via an occasional long-press-triggered WiFi hotspot + NTP resync when crossing time zones. Bedside-clock still carries no MQTT, no SmartThings, and no watchdog registration — but is not literally zero-network, as originally stated. No BOM changes result from this — same ESP32 handles WiFi natively. Proceed to Phase 4 — production of the Claude Code instruction set — accounting for the two distinct firmware wake paths (short-press glance, long-press resync), the SH1106-vs-SSD1306 driver distinction, and the JCTsh-Build-Standards.md §2.14 battery safety requirements (see table above) — the firmware low-battery cutoff is a required deliverable of Phase 4, not deferred.
