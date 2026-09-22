# hike-izer-orchestrator — Context

No curated context recorded yet — add design rationale, constraints, and gotchas here
as they're actually learned, per `JCTsh-Build-Standards.md` §7.1's intent for this
file. `README.md` in this directory is the permanent reference (what it does, current
behavior); this file is history/rationale, kept separate per `JCTsh-Operating-System.md`'s
Documentation Structure section.

## Gotchas

**Apps Script write failures last minutes-to-hours, not seconds — durable retry-eligibility across passes beats a bigger in-run retry budget (CARD-0276, observed live 2026-09-21).** Every write this component makes to the Google Apps Script endpoint (`_post_wildlife_detection`, and anything added later on the same path) is exposed to the same failure shape: a `The read operation timed out` where the write may well have **committed server-side** while the client never saw the response. Two consequences that have both bitten for real:

1. **Never mark a record "done" until its write actually succeeded.** `wildlife_life_list.py`'s `update_from_hike()` originally updated the local dedup cache unconditionally, right after the archive attempt — so a failed species was permanently marked archived and no later pass ever retried it. That's how 23 real rows went missing across two hikes. The per-species `archived` flag exists to keep a failed write retry-eligible; the later pass (CARD-0214's daily refresh) is what actually recovers it. Confirmed live on the 2026-09-21 hike: 2 species failed all 3 in-run attempts at 08:23 and were archived cleanly by the 17:01 refresh, ~8.6 hours later. The in-run retry (3 attempts, 10s apart) never succeeded — the cross-pass eligibility is what saved the data.
2. **Any retry on this path requires a server-side dedup guard, or retries create duplicates.** Because a timed-out attempt may have committed, retrying is only safe once the Apps Script handler checks for an existing row before `appendRow` and returns `{"status": "duplicate"}` (which the client must treat as success, not failure). `core/data-pipeline/environmental-data.gs` does this for the wildlife-detection branch, matching the GPS Track / Hiking Observations precedent (CARD-0243/CARD-0244). Adding a new write endpoint without this guard silently reintroduces the duplicate-row bug the moment a timeout happens.
