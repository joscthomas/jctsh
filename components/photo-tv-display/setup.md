# photo-tv-display — Setup

## Prerequisites (already satisfied)

- Node.js v24.18.x already installed on the M8 (`photo-server` build, Step 15).
- Immich reachable at `http://localhost:2283` on the M8; API keys for both
  accounts already exist (from the original immich-go migration) and are
  reused here — see `credentials.local.md`.
- `media_player.groom_tv` confirmed live in Home Assistant (Cast integration
  entity for the gathering room Google TV).
- Shared `HA_TOKEN` (already used by Node-RED/Claude Code) reused rather than
  generating a dedicated token.

## Deploy from the repo

Source of truth is this repo — edit here, then copy to the M8 (do not edit
directly on the M8):

```bash
scp package.json server.js .env jct@photo-server.local:~/photo-tv-display/
scp routes/*.js jct@photo-server.local:~/photo-tv-display/routes/
scp public/* jct@photo-server.local:~/photo-tv-display/public/
ssh jct@photo-server.local "cd ~/photo-tv-display && npm install"
```

## systemd service

`/etc/systemd/system/photo-tv-display.service` on the M8:

```ini
[Unit]
Description=JCTsh Photo TV Display
After=network.target docker.service

[Service]
Type=simple
User=jct
WorkingDirectory=/home/jct/photo-tv-display
ExecStart=/usr/bin/node server.js
Restart=on-failure
EnvironmentFile=/home/jct/photo-tv-display/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable photo-tv-display
sudo systemctl start photo-tv-display
sudo systemctl status photo-tv-display
journalctl -u photo-tv-display -f
```

**Installed and running 2026-08-03 19:01 MST** — `enabled` (survives reboot),
`active (running)`, both `/tv` and `/controller` confirmed responding. Joseph
ran the privileged steps himself (the harness's auto-mode classifier blocks
Claude Code from piping a sudo password non-interactively, by design).

## Deletion-log Apps Script

1. Create a new Google Sheet (e.g. "JCTsh Photo Deletion Log") — **not** the
   existing JCTsh Environmental Data sheet, kept isolated per Phase 2 planning.
2. Add a sheet tab named `Deletions` with header row:
   `timestamp | filename | date_taken | album_folder | immich_asset_id | deleted_by`
3. Extensions → Apps Script, paste in `components/photo-tv-display/apps-script.gs`.
4. Project Settings → Script Properties → add `API_KEY` = the value currently
   in `.env`'s `DELETION_LOG_SHEET_APPS_SCRIPT_KEY`.
5. Deploy → New deployment → Web app → Execute as: Me, Who has access: Anyone.
6. Copy the deployment URL into `DELETION_LOG_SHEET_APPS_SCRIPT_URL` in
   `~/photo-tv-display/.env` on the M8 (replacing the placeholder), then
   `sudo systemctl restart photo-tv-display`.
7. Verify: `curl "<deployment-url>?action=version"` — should return
   `{"status":"ok","version":"..."}` with no `key` param needed for the
   version check.

**Done 2026-08-03** — deployed by Joseph, URL confirmed live in `.env` on the
M8 and the `?action=version` check returns `{"status":"ok","version":"2026-08-03.1-initial"}`.

## Environment variables

See `.env.example` for the full list. `.env` itself is gitignored; real values
live only on the M8 and in `credentials.local.md`.
