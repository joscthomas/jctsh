# photo-server — Backup

Weekly rsync mirrors the primary Immich library (Seagate Backup Plus 1TB) to **two** local backup drives, split by account.

| Property | Value |
|---|---|
| Script | `/usr/local/bin/photo-library-backup.sh` — version-controlled at `components/photo-server/photo-library-backup.sh` |
| Schedule | Weekly, Sunday 2:00 AM — **active** |
| Log | `/var/log/photo-library-backup.log` |
| Primary drive | `/mnt/photo-library` (Backup Plus 1TB, UUID `cd4612e2-7c14-4134-8dcb-f43a251f2127`) |
| Joseph's backup drive | `/mnt/photo-library-backup-joseph` (Seagate 1TB, model `ST31000528AS`, UUID `214f8cf4-80de-44a1-91ed-ece4c5400598`) |
| Robin's backup drive | `/mnt/photo-library-backup` (Momentus 640GB, UUID `db545672-4650-412e-980f-3a70bba26883`) |

**Incremental by design:** `rsync -av --delete` only transfers files that are new or changed since the last run — it does not re-copy the whole library every week. `--delete` additionally removes anything from the backup that no longer exists in the source, keeping it an exact mirror rather than an ever-growing pile. A first run against an empty/changed destination can be slow since it has to reconcile the full difference; steady-state weekly runs should be fast, just that week's new photos.

## Split-by-Account Architecture (2026-07-10)

Two separate `rsync` invocations run per backup, filtered by owner UUID:

```bash
JOSEPH_ID=b877bff7-37a3-465e-8920-c9fa1ccf3ce9
ROBIN_ID=34fc3f59-37ee-400d-bde3-9273c9501a29

rsync -av --delete --exclude="lost+found" --exclude="*/${ROBIN_ID}/***" \
  /mnt/photo-library/ /mnt/photo-library-backup-joseph/

rsync -av --delete --exclude="lost+found" --exclude="*/${JOSEPH_ID}/***" \
  /mnt/photo-library/ /mnt/photo-library-backup/
```

`upload/`, `thumbs/`, and `encoded-video/` are each organized as `<dir>/<ownerId>/...` — the filter excludes only the *other* account's UUID within those, so each destination gets one account's asset tree. This also means any new per-user top-level directory Immich adds in the future is included automatically, since the filter is an exclude-the-other-owner rule, not an explicit allow-list. Non-per-user data (`backups/` — Postgres DB dumps, ~2.2GB, contains both accounts mixed together — plus the negligible `library/`, `profile/`, `takeout-staging/` dirs) is copied to **both** destinations, since it isn't per-account and is small. `lost+found` (ext4 filesystem cruft, not Immich data) is excluded from both.

| Account | Usage (2026-07-09) | Destination | Capacity | Headroom |
|---|---|---|---|---|
| Joseph | 403.3 GB | `photo-library-backup-joseph` | ~870GB usable | ~467GB |
| Robin | 186.5 GB | `photo-library-backup` (Momentus) | ~586GB usable | ~400GB |

**Why split instead of pooling both drives into one volume:** pooling (e.g. LVM) would add real management complexity without adding redundancy — a failure on either physical drive loses that portion of a pooled volume just the same as it would a standalone drive. Splitting by account keeps both drives simple, independent, and productively used, with Joseph's larger/faster-growing library getting the bigger drive.

## Why This Setup Happened (2026-07-10 incident)

Momentus alone (640GB) could no longer hold the full primary library (624GB, essentially no margin left) — a scheduled backup run failed with `rsync error: some files/attrs were not transferred (code 23)` after `No space left on device`. Fixing this required a second backup drive. While connecting it, two things went wrong that are worth remembering:

- **Grabbed the wrong spare first.** The WD 750GB (P/N WD7500H1U-00) was connected instead of the intended Seagate Expansion 1TB (P/N 9SF2A4-500) — the two spares aren't easy to tell apart at a glance. Always check the P/N label before connecting either. See `jctsh-parts-inventory.md`.
- **Neither spare drive was actually blank.** Both had a leftover `vfat` + `ext3` + `swap` partition layout from prior use (likely an old Linux system disk). Confirm what's on a "spare" drive before formatting it — don't assume blank.
- **Momentus suffered a real hardware-level failure during the drive-swapping** (`dmesg`: "device offline error", "Buffer I/O error", "JBD2: I/O error when updating journal superblock", forced unmount) — almost certainly a jostled USB connector, not a failing drive; it came back clean on remount with no further errors. The primary library also briefly went read-only during the same window (caught correctly by CARD-0032's storage-health check) and recovered the same way. Neither incident got dashboard visibility in real time — the primary library's blip resolved faster than the 30-minute heartbeat interval could catch it, and Momentus's failure exposed a real gap (CARD-0046): the storage-health check only covers the primary library, not either backup drive.

Full incident writeup: `DEVLOG.md`, 2026-07-10.

## Dashboard Visibility (added 2026-07-09, updated 2026-07-10 for the split)

The backup script publishes MQTT log messages so success/failure is visible on the JCTsh log dashboard without SSHing in — same pattern as the scheduled-reboot notifications (CARD-0036):
- `"Backup starting."` (component `photo-server`, category `System`) published before either `rsync` runs
- On success (both jobs exit 0): `"Backup complete."` (category `System`)
- On failure (either job fails): `"Backup failed (joseph exit <code>, robin exit <code>)."` (category `Alert`, non-collapsing)

Uses the existing `photo-server` MQTT account (`/etc/jctsh/heartbeat.env`) and `mosquitto_pub`. **Still not yet live-verified end-to-end** — see CARD-0040 in `backlog.md`.

**Known gap (CARD-0046):** this notification only fires when the backup script itself runs (scheduled or manual) — it doesn't catch a backup drive failing *between* runs, the way CARD-0032's continuous 30-minute heartbeat check does for the primary library. See CARD-0046 for the proposed fix.

## Capacity Monitoring

Flag when either account's usage approaches its backup drive's capacity: Joseph at ~870GB usable (Seagate 1TB), Robin at ~586GB usable (Momentus). The remaining spare (WD 750GB) is too small to replace either and isn't blank — see `jctsh-parts-inventory.md` before considering it for anything.

## How to Verify Backup Is Working

```bash
crontab -l                                        # confirm job is present and uncommented
/usr/local/bin/photo-library-backup.sh            # manual run
tail -f /var/log/photo-library-backup.log         # watch progress
df -h /mnt/photo-library-backup-joseph            # confirm Joseph's space used matches his account usage
df -h /mnt/photo-library-backup                   # confirm Robin's space used matches her account usage
```

Also check the JCTsh log dashboard (`http://raspberrypi.local/`) for the `photo-server` component's `"Backup starting."`/`"Backup complete."` pair after any run, scheduled or manual.

## Related

See `jctsh-network.md`'s **Scheduled Maintenance Windows** table for how this job's timing relates to the M8's own weekly reboot and other recurring jobs across the network. See `backlog.md` CARD-0030 (original cron re-enable), CARD-0040 (dashboard visibility, still pending live verification), and CARD-0046 (backup-drive health check gap).
