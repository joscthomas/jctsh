# Hike-izer — BirdNET Live Integration (CARD-0080)

Current-state architecture reference for how a BirdNET Live bird/wildlife
survey export gets from Joseph's phone onto a published hike page and into
the cross-hike Wildlife Life List. Not a separate service — BirdNET parsing
is one more optional resource hike-izer's own generation pass reads from a
hike's staging directory, same shape as the Gaia GPS embed. For the staging
mechanism itself (directory layout, the SSHFS-Win `Z:` mount, manual
fallback), see `staging.md` — this file covers what happens to a BirdNET
export specifically, once it's staged.

---

## Architecture Overview

```
BirdNET Live app (phone, Survey Mode)
    │  session export (.zip, or .json pulled from it)
    ▼
AutoShare app → Tasker → POST /webhook/stage-file?kind=birdnet&key=<SECRET>
    │  (+ local_datetime param, CARD-0136 — same Joda-Time pattern the
    │   hike-end webhook uses, lets the race case below resolve correctly)
    ▼
app.py _handle_stage_file()
    │
    ├─ hike for that date already known (normal case) ──► <file_stem>_staging/
    │
    └─ shared *before* the hike-end webhook has arrived (CARD-0136 race —
       confirmed real, 2026-08-03) ──► pending_birdnet_<date_str>/
                                              │
                                              ▼  generation.py run() (step 1),
                                                 on creating the real hike's
                                                 own staging dir: claims any
                                                 matching pending_birdnet_*
                                                 directory automatically
                                              │
                                              ▼
                                       <file_stem>_staging/
                                              │
                                              ▼
    birdnet.py, read at generation time (step 1 best-effort, full at step 2):
        parse_detections()   → species-aggregated rows  ─┐
        parse_occurrences()  → per-sighting, time-grouped ┤
                                (CARD-0133, interpolated   │
                                GPS via build_hike_map.    │
                                interpolate_position())    │
                                                            ▼
                                              templating.py renders:
                                                - birdnet_table_rows() →
                                                  "Wildlife Heard" table
                                                - _build_event_markers() →
                                                  Route Map bird markers
                                              │
                                              ▼
                              wildlife_life_list.update_from_hike()
                                  merges this hike's species into
                                  /srv/hike-izer-private/wildlife_life_list.json
                                              │
                                              ▼
                        components/hike-izer/build_wildlife_index.py
                            renders the persisted JSON into the standalone
                            wildlife.html cross-hike index page
```

No API calls anywhere in this pipeline — BirdNET Live already does the
species classification on-device; `birdnet.py` only parses what the app
already produced.

---

## Section 1 — What actually gets shared, and how it lands

A BirdNET Live Survey Mode session export: either the app's raw `.zip`
(auto-extracted in-memory by `birdnet.py`'s `_load_export()` — Joseph never
has to unzip it himself) or a bare `.json` already pulled out of one. Each
`detections[]` entry carries a precise UTC `timestamp`, `commonName`,
`scientificName`, and `confidence` — confirmed against two real hikes'
exports, 2026-07-29.

**Normal path (fully automatic, CARD-0122):** AutoShare → Tasker → `POST
/webhook/stage-file?kind=birdnet` lands the file directly in the correct
`<file_stem>_staging/` directory, no manual step.

**Race case (CARD-0136, confirmed real 2026-08-03):** if the phone share
arrives *before* the hike-end webhook itself (a real ~27-second gap was
observed), there's no `file_stem` yet to attach it to. `local_datetime` (a
Tasker-added query param, same pattern the hike-end webhook already uses)
lets `_handle_stage_file()` derive the real local calendar date and stage
into a provisional `pending_birdnet_<date_str>/` holding directory instead of
guessing at some other, already-published hike. The moment step 1
(`generation.py run()`) creates that hike's real staging directory, it
checks for and claims any matching pending directory automatically — no
manual recovery needed for new hikes going forward. (One real file did need
manual recovery when this was first found; see CARD-0136 for that
incident.)

**Manual fallback (mount down, or bypassing the automatic path on
purpose):** drop the export — any filename ending `.zip` or `.json`, exact
name doesn't matter — into that hike's `<file_stem>_staging/` directory via
the `Z:` SSHFS-Win mount (`staging.md`). More than one export can be staged
for the same hike (e.g. multiple survey sessions); `birdnet.py` parses all
of them.

**No taxon filtering:** BirdNET+ classifies amphibians/mammals/insects
alongside birds in the same unified model output — nothing here filters to
"just birds" (Joseph's call: report whatever the model reports).

**Staged files are never deleted after use** (same as Gaia embeds) — a later
re-render of the same hike doesn't need anything re-staged.

---

## Section 2 — Parsing: two different shapes for two different needs

`birdnet.py` reads every staged export once (`_load_all_detections()`) and
feeds two independent parsers, since the table and the map markers need
different things from the same raw detections:

- **`parse_detections()`** — species-aggregated rows for the "Wildlife
  Heard" table. Deliberately does **no** location correlation (Joseph's
  call, CARD-0080) — BirdNET Live only gives one session-level lat/lon for
  the whole survey, not per-detection, so the table's Time column is the
  only location-relevant signal, by design.
- **`parse_occurrences()`** (CARD-0133) — groups raw detection timestamps
  into per-sighting rows (default 5-minute gap threshold) for the Route
  Map's bird markers, which *do* need a real position per sighting. Each
  occurrence gets a `representative_timestamp` that the caller interpolates
  against the actual GPS track (`build_hike_map.interpolate_position()`) for
  an approximate location — genuine interpolation, not the session-level
  single point `parse_detections()` accepts as good enough for a table.

---

## Section 3 — Rendering and the cross-hike life list

`templating.py`:
- `birdnet_table_rows()` — builds the per-hike "Wildlife Heard" table,
  flagging species new to the life list (CARD-0147).
- `_build_event_markers()` — folds `birdnet_occurrences` in alongside photo
  and observation markers on the Route Map.

`wildlife_life_list.py`:
- `update_from_hike(file_stem, date_str, birdnet_rows)` — idempotent merge
  of this hike's species into the persisted life list
  (`/srv/hike-izer-private/wildlife_life_list.json`) — re-running step 2 for
  an already-recorded hike just re-adds its own `file_stem` to each species'
  hikes list rather than duplicating it.
- `load()` — read back for both the per-hike "NEW species" badge and the
  standalone index build.

`components/hike-izer/build_wildlife_index.py` renders that persisted JSON
into `wildlife.html` — the cross-hike species index, separate from any
single hike's own page.

---

## Related
- `components/hike-izer-orchestrator/staging.md` — the staging directory
  mechanism itself (both staged-resource types, the `Z:` mount).
- `components/hike-izer-orchestrator/birdnet.py` — parsing, most complete
  inline design rationale in its own module docstring.
- `components/hike-izer-orchestrator/generation.py` — `_read_staging()`,
  `pending_birdnet_dir()`, `_claim_pending_birdnet()`, `run()`/`run_step2()`.
- `components/hike-izer-orchestrator/app.py` — `_handle_stage_file()`
  (the webhook receiver).
- `components/hike-izer-orchestrator/templating.py` — `birdnet_table_rows()`,
  `_build_event_markers()`.
- `components/hike-izer-orchestrator/wildlife_life_list.py`,
  `components/hike-izer/build_wildlife_index.py` — the cross-hike index.
- Kanban: CARD-0080 (original integration), CARD-0112 (staging mechanism),
  CARD-0119 (staging.md + SSHFS-Win mount), CARD-0122 (automatic phone→server
  path), CARD-0133 (Route Map occurrence markers), CARD-0136 (hike-end race
  condition fix), CARD-0147 (life-list "NEW species" badge).
