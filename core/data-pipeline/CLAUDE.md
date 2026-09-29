# core/data-pipeline — Context

Card history archived to `card-archive.md` (CARD-0290) — on-demand only, not part of routine reading. Curated gotchas, per `JCTsh-Build-Standards.md` §7.1 — read `README.md` for how the pipeline works; this file is only what bit us.

- **The live Node-RED flow is what runs, not the repo export.** Both `environmental-data.flow.json` and `sheet-health.flow.json` sat stale in the repo through the CARD-0349 cutover (CARD-0369). After any editor change, re-export the tab from `/home/pi/.node-red/flows.json`.
- **Cloudflare's Bot Fight Mode 403s Python's default `urllib` User-Agent** before a request reaches the gateway (`hikes.jctnet.com`). Any new caller sends an identifiable UA — `fetch_hike_data.py` and `sheet_health.py` both do.
- **`init/schema.sql` runs once.** Editing it does nothing on the live database; a schema change is a hand-written `ALTER` plus the matching file edit.
- **Bump `VERSION` in `api/app.py` on every gateway change** — `/version` is the only deploy fingerprint.
- **Alert text must never carry secrets.** A subprocess failure formats its whole argv into the exception message; the orchestrator scrubs at the publish boundary (`mqtt_log.redact`, CARD-0367). Anything else that publishes exception text needs the same.
- **Design doc vs. code:** `timescaledb-design.md` predates the build and is wrong in places (e.g. it names a `bearing_deg` column; the real one is `direction`). Trust `init/schema.sql` and `api/app.py`.
