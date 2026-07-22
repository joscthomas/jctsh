# Salt Sensor — Enclosure Plan

Plain planning doc (CARD-0067) — not forced into a template structure yet, since the enclosure-template question (`JCTsh-3D-Enclosure-Instructions-Template.md`, pending on CARD-0009's Reflection step) is deliberately deferred. Measurements captured here as raw data first, for a later double-check pass, per Joseph's explicit request.

**Reference convention:** following hiking-monitor's compass terminology (`hiking-monitor-enclosure-plan.md`) — walls labeled N/S/E/W, two-part enclosure (bottom + top shell), same overall approach.

## Board Footprint

| Dimension | Value | Notes |
|---|---|---|
| Board size | 70mm × 90mm | Same footprint as hiking-monitor's enclosure |
| Height | 37mm | |
| Standoff height | 10mm (assumed) | "Would match the hiking-monitor enclosures" — hiking-monitor's plan used a 10mm standoff (`hiking-monitor-enclosure-plan.md` dimensions table: "10mm standoff + 21mm component + 2mm margin + 3mm wall"). Inherited, not independently re-derived for salt-sensor — worth confirming this is still the right value once actual perfboard component heights are checked. |
| Shell count | 2 (two-part enclosure) | Bottom + top shell, same overall approach as hiking-monitor |

## South Wall — Micro USB Opening

| Property | Value |
|---|---|
| Wall | South |
| Connector size | 11mm wide × 6mm high |
| Distance, top of perfboard to bottom of connector | 10mm |
| Distance from West wall | 26mm |
| Distance from East wall | 13mm |

## North Wall — JSN-SR04T Connector Opening

| Property | Value |
|---|---|
| Wall | North — confirmed 2026-07-13 |
| Connector size | 9mm wide × 8mm high |
| Distance, perfboard to bottom of opening | 18mm |
| Distance from West wall | 18mm |
| Distance from East wall | 25mm |

## Notes

- **No margins included in any measurement above** — these are raw connector/position dimensions as measured. Clearance/interference-fit margins (matching hiking-monitor's convention — e.g. its vent insert used "0.2mm interference fit on width and height") need to be added when the actual CAD apertures are cut, not baked into this table.
- **Not yet double-checked** — Joseph's own request: capture first, verify later. Worth a sanity pass once CAD work starts: for each opening, `(distance from West) + (connector width) + (distance from East)` should be checked against the relevant wall's actual length, to catch any transcription error in these raw numbers.
