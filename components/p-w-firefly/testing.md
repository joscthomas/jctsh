# Full System Testing — Pleasure-Way Firefly Interface

Complete validation of all hardware, RV-C, network, and control functions.

Items marked ✓ were confirmed during earlier build steps.

---

## Hardware and RV-C

- [x] Pi boots from coach 12V power (buck converter) ✓
- [x] can0 interface comes up automatically at boot ✓
- [x] candump can0 shows RV-C traffic ✓
- [x] eRVin dashboard loads and shows live Firefly data ✓
- [x] Fresh water tank level reads correctly ✓
- [x] Gray water tank level reads correctly — 25%, matches Vegatouch ✓
- [x] Black water tank level reads correctly ✓
- [x] Coach battery voltage reads correctly — 13.2 V, matches Vegatouch ✓
- [x] Shore power connected status — not available; Xantrex Freedom Xi is not on the RV-C bus (confirmed candump with shore power connected — no new source addresses appeared) ✓
- [x] Inverter status — not available; same reason ✓
- [x] Light circuits respond to on/off commands from dashboard — all lights correctly configured ✓
- [ ] Generator start/stop — not tested; skipped
- [ ] Awning — not adding to eRVin dashboard; operated from Vegatouch panel only
- [x] Water pump on/off works from dashboard ✓

---

## Network — Scenario 1 (Home WiFi)

- [x] Pi connects to home WiFi automatically on boot ✓
- [x] eRVin dashboard accessible from Joseph's Pixel on home WiFi ✓
- [x] eRVin dashboard accessible from Robin's Pixel on home WiFi ✓
- [x] eRVin dashboard accessible from Windows PC browser on home network ✓

---

## Network — Scenario 2 (Pixel Hotspot / Tailscale)

- [ ] Disable home WiFi on router — Pi switches to Pixel hotspot within 60 seconds
- [x] Tailscale tunnel established ✓
- [x] eRVin dashboard accessible via Tailscale IP (http://100.90.246.43) from Pixel ✓
- [x] Home Pi can ping RV Pi via Tailscale IP ✓
- [ ] Re-enable home WiFi — Pi switches back to home network within 60 seconds

---

## Network — Scenario 3 (JCT-RV Fallback Hotspot)

- [x] JCT-RV hotspot SSID appears when no known network available ✓
- [x] Joseph's Pixel connects to JCT-RV automatically ✓
- [x] Robin's Pixel connects to JCT-RV automatically ✓
- [x] eRVin dashboard accessible at http://192.168.5.1 from both Pixels ✓
- [x] All coach controls functional in hotspot mode — lights tested ✓

---

## Dashboard Customization

Changes to the eRVin Node-RED flows via the editor at `http://192.168.1.219:1880`.

- [x] Sofa Extend/Retract — sofa is present; leaving eRVin default controls in place ✓
- [x] Vent fan control — not added; Fan-Tastic uses Firefly rolling-code authentication on AIR_CONDITIONER_COMMAND (DGN 0x1FFE0, source 0x9A); Pi cannot issue authenticated commands; Vegatouch-only control ✓
- [x] Charging amps — not available; DC_SOURCE_STATUS_1 reports voltage only (current bytes are 0xFF); no DC current sensor on RV-C bus ✓
- [x] Shore power and inverter investigation — complete; Xantrex Freedom Xi and Go Power solar controller are not on the RV-C bus; candump with shore power connected showed no new source addresses ✓

---

## Android Home Screen Shortcuts

- [x] Add eRVin dashboard to Joseph's Pixel home screen ✓
- [x] Add eRVin dashboard to Robin's Pixel home screen ✓
- [x] Shortcut opens dashboard correctly in both network scenarios ✓

---

## Confirmed Details

| Item | Value |
|---|---|
| Testing completed | June 2026 |
| WiFi signal after permanent mount | -52 dBm open compartment; -57 dBm with cushions/bedding in place — both excellent |
| Generator test | Skipped — not testing in the field |
| MicroSD | SanDisk MAX Endurance 32GB — was used for the build from the start; no swap needed |
| Any entities missing or reading incorrectly | None |
