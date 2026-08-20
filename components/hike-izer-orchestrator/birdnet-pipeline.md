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
BirdNET Live app (phone, Live Mode through 2026-08-19 -- see CARD-0182;
switching to Survey Mode going forward, see Section 4)
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

A BirdNET Live session export: either the app's raw `.zip` (auto-extracted
in-memory by `birdnet.py`'s `_load_export()` — Joseph never has to unzip it
himself) or a bare `.json` already pulled out of one. Each `detections[]`
entry carries a precise UTC `timestamp`, `commonName`, `scientificName`,
and `confidence` — confirmed against two real hikes' exports, 2026-07-29
(Live Mode; see CARD-0182 — the export shape is shared across BirdNET
Live's modes via its common Session Review/export system, so this parsing
isn't mode-specific).

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

## Section 4 — Field recording practices while hiking (CARD-0182)

This pipeline only consumes BirdNET Live's already-identified detections
after the fact — it does no audio processing of its own, so recording
quality is entirely determined by phone/app setup on the trail. Raised
2026-08-18: trail noise (wind, footsteps, breathing) and phone mic/carry
setup degrade BirdNET Live's on-device recognition. Researched 2026-08-19;
sourced from general field-recording practice plus BirdNET-model-family
documentation (BirdNET-Pi/BirdNET-Analyzer) — the model-family concepts
below (confidence threshold, sensitivity, overlap) are well-documented for
those products, but **not independently confirmed against BirdNET Live's
own settings screen** — check there directly since the app is a different,
simpler UI than the Pi/Analyzer tools these ideas come from.

**Mode correction, 2026-08-19 — significant finding.** Every hike so far
has actually used **Live Mode**, not Survey Mode — the "Survey Mode"
references throughout this doc and `birdnet.py`'s docstring were CARD-0080's
original assumption, never actually verified, and never actually true.
Functionally this didn't break anything (see Section 1 — the export shape
`birdnet.py` parses is shared across modes, and the Route Map's per-sighting
location comes from the hike's own independent GPS track via
`build_hike_map.interpolate_position()`, not from any location BirdNET Live
itself reports — confirmed by reading that function directly, not assumed).

But it does mean the background-operation question needs a real answer
for the mode actually in use. Checked BirdNET Live's own source
(`birdnet-team/birdnet-live-app` on GitHub): the `flutter_foreground_task`
package — Android's standard mechanism for keeping audio recording alive
through a screen lock or app-switch — is wired into a dedicated
`survey_notification.dart` for Survey Mode and `aru_notification.dart` for
ARU Mode. No equivalent file exists for Live Mode, and Live Mode's own docs
describe it as an actively-open, on-screen experience (scrolling
spectrogram, live-updating detection list, a "Ready" / "Identifying
species" status line) with no mention of a persistent notification or
background survival. Not a documented certainty either way, but strong
circumstantial evidence that **Live Mode likely stops or pauses listening
when the screen locks or another app takes focus** — every past hike may
have had silent gaps whenever the phone screen locked, on top of the
trail-noise degradation this card originally set out to fix.

**Decided 2026-08-19 (Joseph): switch to Survey Mode for hiking going
forward.** It's purpose-built for exactly this use case — confirmed
background survival via the persistent foreground notification (elapsed
time, detection count, species count, distance walked — worth a glance
partway through a hike to confirm it's still running, since some OEM
battery-optimization settings can still override standard foreground-
service protections), plus its own continuous GPS track (not needed by
this pipeline, but no downside). Setup is a 5-step wizard (name, observer
info, starting location, recording parameters, species alerts, pre-start
checklist); stop via the end-survey button in the top bar. Detection
Sampling controls which audio *clips* are kept on disk, not which
detections get logged — **All** keeps every clip, **Top N** (default 10)
keeps only the highest-confidence clips per species, **Smart** adds
spatial spreading so one persistent singer near the trailhead doesn't fill
storage with near-duplicate clips of the same individual. Not yet field-
tested — first real Survey Mode hike will confirm this actually resolves
the gaps.

**Confirmed 2026-08-19 — no pipeline changes needed for the mode switch.**
Checked BirdNET Live's own export documentation and `birdnet.py` directly
rather than assuming: the core export packaging (zip archive, JSON
detection records, `memos/` structure) is identical across every mode —
Survey Mode's exports carry *extra* fields on top (GPS track, spatial
metadata) that Live Mode's don't, but `birdnet.py` only ever reads
`data.get("detections", [])` from the top-level export and ignores every
other key, so those extra fields are inert. Session Review/export is
explicitly shared infrastructure across modes too (both Live and Survey
Mode's own docs use identical language — "saves the session and opens
Session Review") — so the existing AutoShare → Tasker → webhook path
(CARD-0122) needs no changes either; it triggers off that same shared
screen regardless of which mode produced the session. Net effect of the
mode switch: same file format, same sharing mechanism, same pipeline
output — the only real difference is Survey Mode keeps recording through a
screen lock or app-switch, where Live Mode likely didn't.

**Pixel 10 Pro XL microphone hardware, 2026-08-19.** Confirmed via Google's
own Pixel hardware diagram: three built-in mics — **top** (near the top
edge), **bottom** (next to USB-C — Google moved this to the *left* side of
the port on the Pixel 10 Pro XL specifically, a known change from the 9 Pro
XL that makes right-handed users more likely to cover it while holding the
phone), and **rear** (near the camera bar). Joseph's usual carry — front
cargo pocket, top of the phone exposed above the pocket opening — puts the
*top* mic in open air while bottom and rear stay muffled in-pocket, which
is the favorable mic for that carry style if the app is actually recording
from it.

**BirdNET Live's actual "Select audio source" screen, confirmed live via
screenshot (Joseph's real device, not app docs) — correction to what was
said earlier.** The generic app documentation claims built-in mics get
listed by position name ("bottom", "back") on phones that expose that —
**not true on this device.** The real screen has two sections:
- **PROCESSING** — `Phone default` (ships selected; whatever the phone
  normally uses, including its speech-oriented noise reduction) /
  `Unprocessed` (raw signal, no noise reduction or automatic gain —
  app's own description: "usually the best choice") / `Voice recognition`
  (also disables noise reduction and gain, works on nearly every phone —
  app's own guidance: try this if Unprocessed makes no difference).
- **MICROPHONE** — `System default` (ships selected) plus **two entries
  both generically labeled "Pixel 10 Pro XL"** with no position
  information at all — the app cannot tell Joseph which one is the top
  mic from the UI alone.

**Recommendation given the real screen:** switch **Processing** to
`Unprocessed` first (directly targets the original problem — phone speech
processing blurring bird calls — and the app calls it usually the best
choice); fall back to `Voice recognition` only if that doesn't help.
Leave **Microphone** on `System default` rather than guessing between two
identically-labeled options. To actually identify which one is the top
mic, if it matters enough to pin down: select one of the two non-default
options, cover the top mic hole with a finger, and watch the live
spectrogram/input level for a drop — repeat for the other option to
confirm. Not yet done.

**Inference/audio settings applied, 2026-08-19 (Joseph):**

| Setting | Applied | Recommended | Notes |
|---|---|---|---|
| Gain | 1.0× | 1.0× | Matches — default, unchanged. |
| High-pass filter | 150 Hz | ~150 Hz | Matches. |
| Window duration | 3 s | 3–5 s | Matches. |
| Confidence threshold | **50%** | ~20% (superseded, see correction below) | Joseph's call — turns out to be the better-reasoned choice once the review-step assumption below is corrected. |
| Sensitivity | 1.15 | ~1.15–1.25 | Matches — but the original "more false positives, mitigated by review" caveat is also invalid per the no-review correction below; kept at 1.15 (not the higher end of the range) is the more defensible choice given that. |
| Inference rate | 0.7 Hz | 0.70 Hz (default) | Matches — kept Survey Mode's default rather than the battery-saving 0.30 Hz option. |

Processing/Microphone (Unprocessed vs. Phone default; which physical mic)
not yet confirmed as applied — revisit before/after the first Survey Mode
hike.

**Correction, 2026-08-19 (Joseph): there is no manual review/curation step
in the actual workflow.** The confidence-threshold reasoning above ("lower
it and curate later at Session Review") assumed Joseph reviews and filters
detections before they reach the exported data — **he doesn't.** His own
words: "there is no review at the end of a session. I just take it as it
comes. I have no expertise for any review." Whatever the app confidently
reports flows straight through export → this pipeline → the published
hike's "Wildlife Heard" table and the cross-hike Wildlife Life List, with
no human filtering step anywhere in between. This reverses the earlier
reasoning: a **higher, more conservative confidence threshold is the
better-justified choice**, not a lower one — Joseph's own 50% turns out to
be well-reasoned on its own merits, independent of my original ~20%
suggestion, which was built on a wrong assumption about the workflow.

**Other general settings, recommended 2026-08-19 (not yet confirmed as
applied):**

- **Recording mode → "Detections only"**, not "Full." A multi-hour
  continuous raw recording is a lot of storage/battery for no benefit this
  pipeline currently uses — only clips around actual detections are
  needed.
- **Format → FLAC** over WAV — same audio quality, meaningfully smaller
  files, no real downside for this use case.
- **Timestamp display → Absolute**, not relative-to-session-start — makes
  it easier to cross-reference a detection against photos or the GPS track
  later, both of which key off real clock time.
- **Announcements (TTS)** — worth considering since the phone stays in a
  pocket and the screen isn't visible while hiking: an audible alert on
  detection means Joseph would actually know something was heard in real
  time, rather than only finding out at Session Review afterward. Set
  frequency to **Sparse** or verbosity to **Watchlist only** to avoid
  constant interruption for common species. Untested whether it's audible
  enough through a pocket to be worth using — a real trial would confirm.

**Checklist to try on the next hike:**

- **Carry position — chest, mic facing inward toward the body, not
  outward.** Chest-level placement reduces wind distortion significantly
  versus a neck lanyard or holding the phone up. Facing the capsule toward
  the chest uses your own clothing as a wind diffuser, at some cost to
  overall pickup — the tradeoff is worth it on breezy trail sections.
- **Favor the leeward side of your body** (the side facing away from the
  wind) when possible — your torso creates a turbulence shadow that can
  meaningfully cut wind noise at the mic versus a front-facing mount.
- **Wear quiet layers near the phone** — fleece or cotton rather than
  anything crinkly/rustly (rain shells, some synthetic packs) right against
  or near the carry pocket. Clothing rustle close to the mic is louder in
  the recording than it sounds in person.
- **Pause, don't record while actively hiking, when a call is worth
  capturing.** Footstep and trekking-pole noise reads as loud, sharp
  transients right next to the mic. Stopping for even a few seconds around
  a promising call meaningfully improves the recognizer's odds.
- **Hold steady if handheld.** Every shift of grip or brush of fabric
  against the phone shows up as a thud/scrape in the recording — brace
  against a trekking pole, rock, or your own chest rather than holding
  free in the air if you're not using a chest carry.
- **Set Audio source → Processing to `Unprocessed`** (see the confirmed
  screen contents above) — targets the original noise-reduction-blurring-
  bird-calls problem directly, and it's the app's own recommended default
  choice where supported.

**Not yet tried in the field** — this is a checklist to validate on a real
hike, not a confirmed fix. Revisit and update this section with results
once Joseph has tested it.

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
  condition fix), CARD-0147 (life-list "NEW species" badge), CARD-0182
  (field recording best practices, Section 4 above).
