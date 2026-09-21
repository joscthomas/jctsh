# House & Lot Coordinates — 7172 W. Cape Final Trail
**Author:** Joseph C Thomas (JCT)
**Purpose:** Approximate lat/lon coordinates for property corners, house footprint corners, and edge midpoints, derived from the Pulte Homes plot plan (Plan 4215-3 A(R), Lot 324, Dove Mountain).
**Version:** 1.3
**Version description:** Corrected the back-patio measurement from v1.2 — the outlet lies *between* the patio's SW and SE corners, not past the SE corner. Replaced the single (wrong) P1 point with four points: SW corner, outlet, SE corner, and NE corner (closure).

---

## Method & Assumptions

- Reference point: house footprint centroid = **32.46136965083809, -111.1184196174227** (center of house per Google Maps).
- Plot plan pixel scale: ~15.004 px/ft (calibrated from the 52.00' × 120.00' lot dimensions).
- Lot rotation off true N/S is negligible (~0.19°) and was ignored — plan treated as North-up, East-right.
- House footprint = "Total Footprint" (2,691 sq ft per plan), including optional covered patio, owner's suite bay window, garage, porch, and front step/notch. Computed polygon area ≈ 2,700 sq ft (within 0.3% of the labeled value — good agreement).
- All coordinates are **approximate** (plan-derived, ±1-2 ft typical), suitable for general reference/siting purposes — not survey-grade.

---

## Property (Lot) Corners

| Point | Latitude | Longitude |
|---|---|---|
| NW corner (rear-west) | 32.4615450 | -111.1185006 |
| NE corner (rear-east) | 32.4615450 | -111.1183319 |
| SE corner (front-east) | 32.4612164 | -111.1183319 |
| SW corner (front-west) | 32.4612164 | -111.1185006 |
| Property centroid | 32.4613807 | -111.1184163 |

## Property Edge Midpoints

| Edge | Latitude | Longitude |
|---|---|---|
| NW → NE (rear edge) | 32.4615450 | -111.1184163 |
| NE → SE (east edge) | 32.4613807 | -111.1183319 |
| SE → SW (front edge) | 32.4612164 | -111.1184163 |
| SW → NW (west edge) | 32.4613807 | -111.1185006 |

---

## House Footprint Corners

Corners are listed in order going around the footprint (clockwise from the rear-west/patio corner).

| Point | Description | Latitude | Longitude |
|---|---|---|---|
| H1 | Patio NW (rear-west corner) | 32.4614512 | -111.1184924 |
| H2 | Rear wall / bay junction (west side) | 32.4614512 | -111.1183907 |
| H3 | Bay window, NW corner | 32.4614567 | -111.1183896 |
| H4 | Bay window, NE corner | 32.4614567 | -111.1183572 |
| H5 | Bay window / east wall junction | 32.4614512 | -111.1183475 |
| H6 | East wall / garage SE corner | 32.4612842 | -111.1183481 |
| H7 | Garage front, west end | 32.4612842 | -111.1184154 |
| H8 | Front porch | 32.4612997 | -111.1184154 |
| H9 | Front notch, west end | 32.4612997 | -111.1184416 |
| H10 | Porch front step | 32.4612833 | -111.1184416 |
| H11 | Porch SW corner (meets west wall) | 32.4612833 | -111.1184924 |
| — | House footprint centroid (= reference point) | 32.4613697 | -111.1184196 |

## House Footprint Edge Midpoints

| Edge | Latitude | Longitude |
|---|---|---|
| H1 → H2 (rear wall, west of bay) | 32.4614512 | -111.1184416 |
| H2 → H3 (bay, west chamfer) | 32.4614540 | -111.1183902 |
| H3 → H4 (bay, rear face) | 32.4614567 | -111.1183734 |
| H4 → H5 (bay, east chamfer) | 32.4614540 | -111.1183523 |
| H5 → H6 (east wall) | 32.4613677 | -111.1183478 |
| H6 → H7 (garage front wall) | 32.4612842 | -111.1183818 |
| H7 → H8 (notch, east side) | 32.4612920 | -111.1184154 |
| H8 → H9 (notch, north wall) | 32.4612997 | -111.1184285 |
| H9 → H10 (notch, west side) | 32.4612915 | -111.1184416 |
| H10 → H11 (porch front wall) | 32.4612833 | -111.1184670 |
| H11 → H1 (west wall) | 32.4613673 | -111.1184924 |

---

## Other Named Points

Points here are not footprint corners — added on demand for specific siting needs (e.g. a sensor mount), derived from Joseph's on-site tape-measurements offset from the nearest known footprint corner rather than the plan's pixel scale. Same approximate precision as the rest of this document.

**Back Patio, corrected 2026-09-21 (Joseph, CARD-0219 Planning):** H1 is the patio's NW corner (existing point, at the patio's *outer* edge). The patio is 12 ft deep (H1 south to the house wall) — this is where the SW/SE corners below sit, at the actual wall the outlet is mounted on. The outlet lies 16 ft east of the SW corner along that wall, with the SE corner a further 12 ft east of the outlet (28 ft total SW→SE, matching the patio's known length). NE corner added by closure (same latitude as H1, same longitude as SE) — not independently measured.

| Point | Description | Latitude | Longitude |
|---|---|---|---|
| P1 | Back Patio, SW corner (at house wall, 12 ft south of H1) | 32.4614183 | -111.1184924 |
| P2 | Back Patio, outlet (16 ft east of P1 along the house wall) | 32.4614183 | -111.1184405 |
| P3 | Back Patio, SE corner (12 ft east of P2 / 28 ft east of P1) | 32.4614183 | -111.1184016 |
| P4 | Back Patio, NE corner (closure only — same latitude as H1, same longitude as P3) | 32.4614512 | -111.1184016 |

---

## Notes

- "House Footprint Corners" trace the exterior outline of the house including all optional structures shown on the plan (covered patio, bay window bump-out at the owner's suite, garage, porch, and a small front step/notch between the porch and garage).
- The interior "OPT OWNER'S BATH" dash-dot outline shown on the plan is an interior layout option and was not treated as part of the exterior footprint.
- Property corners correspond to the 52.00 ft (N89°48'34"W) × 120.00 ft (S00°11'26"W) rectangular lot lines.