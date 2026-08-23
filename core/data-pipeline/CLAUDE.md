# core/data-pipeline — Context

## Card History

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 5053B, over the 5000B size threshold.

### CARD-0099 · [bug] [data-pipeline] Timeline sheet's `timestamp_az` column hardcodes Arizona local time for every row, regardless of where it happened — RESOLVED 2026-07-25
**Status:** Done

**Raised 2026-07-25**, discovered while confirming CARD-0097's fix — Joseph asked "are there any other columns in any sheet so named," which surfaced this second, more serious instance of the same standing principle ([[feedback_no_location_assumptions]]).

**Real gap, not just a stale label (unlike `date_az` in Hike Start Forecast, which CARD-0097 already made cosmetic-only):** `refreshTimeline()` (JCTsh menu → Refresh Timeline) merges Environmental Data + Hiking Observations into the "Timeline" sheet, and unconditionally formatted every row's display time via `_azString()` — hardcoded Arizona (UTC-7, no DST) — regardless of where that reading/observation actually happened. A Michigan or Egypt hike's rows would have silently shown the wrong wall-clock time, mislabeled as if it were correct.

**Fix:** replaced `_azString()` with `_localString(utcDate, lat, lon, offsetCache)`, resolving each row's real UTC offset *and* IANA zone name via Open-Meteo's `timezone=auto` (same provider/mechanism as CARD-0097), cached per rounded `(lat,lon)` for the life of one `refreshTimeline()` run so repeated locations (a fixed home sensor, or many readings from one hike) cost one real HTTP call, not one per row. Column renamed `timestamp_az` → `timestamp_local` — and since this sheet is fully rewritten (`clearContents()` + header) on every refresh, the rename actually takes effect immediately, unlike the Hike Start Forecast header which only sets its header once at sheet creation.

**Format iterated twice at Joseph's request:** first cut appended just the raw UTC offset (e.g. `+03:00`) — Joseph pointed out a bare offset means nothing without already knowing which place maps to it. Switched to leading with the IANA zone name (e.g. `Africa/Cairo`), which Open-Meteo already resolves as part of the same lookup at no extra cost — then added the raw offset back in parentheses alongside it, since that's still useful for quick arithmetic between rows. Final format: `YYYY-MM-DD HH:MM:SS Zone/Name (±HH:MM)`, e.g. `2026-07-25 17:24:37 Africa/Cairo (+03:00)`. Rows with no GPS correlation yet, or where the Open-Meteo lookup itself fails, fall back to an explicit `... UTC` label rather than a wrong guess.

**Live-verified 2026-07-25** against real production data (14,545 rows, spanning 2019–2026): after redeploying and running Refresh Timeline, Joseph confirmed directly from the Sheet that the real Giza test coordinate (29.9792, 31.1342, left over from CARD-0097's verification) now shows `2026-07-25 17:26:45 Africa/Cairo (+03:00)`, while a real fixed Arizona sensor (lat 32.4612997, lon -111.1184154) correctly shows `America/Phoenix (-07:00)` — different locations resolving to their own correct zone, not one hardcoded assumption for everything. Sort order also confirmed correct: the Giza row's true UTC instant (14:26:45 UTC) sorts just before the Arizona rows (14:31:44 UTC onward), confirming the sort key is still the real timestamp, not the display string.

**Troubleshooting note during verification:** the first "Refresh Timeline" click produced no corresponding entry in the Apps Script Executions log at all — the menu click hadn't actually invoked the function (likely a stale menu binding in an already-open browser tab from before the redeploy). Fully reloading the Sheet tab and re-clicking fixed it; the resulting execution (`Head`/`Menu`/`refreshTimeline`, 38.9s, Completed) is what actually produced the correct data. Worth remembering for any future Apps Script custom-menu debugging in this repo: check the Executions log for a *matching* entry before assuming a run happened at all.

**Related discovery, not yet acted on:** verifying this fix via the `action=export` HTTP endpoint turned out to be unreliable in a way that goes beyond the endpoint's already-documented Timeline caveat — `_exportSheet` silently drops (not just mis-filters) any row whose column A doesn't parse as a valid JS `Date`, and this happens *unconditionally*, even when no `start`/`end` filter is requested. The old Arizona-only format happened to still parse via V8's lenient date parsing; the new zone-name format (e.g. `... Africa/Cairo (+03:00)`) does not, so the export endpoint was quietly hiding exactly the rows needed to verify this fix. Verification was completed instead by having Joseph read the Sheet directly. Not fixed as part of this card — flagged for a possible follow-up if `action=export` needs to reliably return Timeline rows in the future.

**Related:** CARD-0097 (same standing principle, same Open-Meteo `timezone=auto` mechanism, found first), [[feedback_no_location_assumptions]] (the standing principle both cards are instances of), `core/data-pipeline/environmental-data.gs`, `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`, `components/hiking-monitor/data-pipeline.md`.

---
