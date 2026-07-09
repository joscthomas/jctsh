# photo-server — Backup

Weekly rsync mirrors the primary Immich library (Seagate Backup Plus 1TB) to the local backup drive (Seagate Momentus 640GB).

| Property | Value |
|---|---|
| Script | `/usr/local/bin/photo-library-backup.sh` — version-controlled at `components/photo-server/photo-library-backup.sh` |
| Schedule | Weekly, Sunday 2:00 AM — **active** |
| Log | `/var/log/photo-library-backup.log` |
| Primary drive | `/mnt/photo-library` (Backup Plus 1TB, UUID `cd4612e2-7c14-4134-8dcb-f43a251f2127`) |
| Backup drive | `/mnt/photo-library-backup` (Momentus 640GB, UUID `db545672-4650-412e-980f-3a70bba26883`) |

**Incremental by design:** `rsync -av --delete` only transfers files that are new or changed since the last run — it does not re-copy the whole library every week. `--delete` additionally removes anything from the backup that no longer exists in the source, keeping it an exact mirror rather than an ever-growing pile. The very first run after a source change (e.g. the CARD-030 cleanup below) can be slow since it has to reconcile the full difference; steady-state weekly runs should be fast, just that week's new photos.

## CARD-030 Resolved (2026-07-09)

The zip files that filled the backup drive to 100% (`/mnt/photo-library-backup/takeout-staging/`, `/home/jct/takeout-staging/`, ~818GB combined) were deleted after CARD-039 confirmed the import was fully complete and verified. Cron re-enabled the same day. Space reclaimed: Momentus went from 100% used (4.3GB free) to 19% used (455GB free); the NVMe root drive went from 87% to 5% used.

## Dashboard Visibility (added 2026-07-09)

The backup script now publishes MQTT log messages so success/failure is visible on the JCTsh log dashboard without SSHing in — same pattern as the scheduled-reboot notifications (CARD-036):
- `"Backup starting."` (component `photo-server`, category `System`) published before `rsync` runs
- On success: `"Backup complete."` (category `System`)
- On failure: `"Backup failed (rsync exit <code>)."` (category `Alert`, non-collapsing)

Uses the existing `photo-server` MQTT account (`/etc/jctsh/heartbeat.env`) and `mosquitto_pub`, already installed for the reboot-notification work. Not yet live-verified end-to-end on a real run — the first post-cleanup backup was already in progress when this was added, so verification is pending its next run (or the next manual trigger).

## Capacity Monitoring

The Momentus 640GB backup drive is smaller than the 1TB primary. Flag when `/mnt/photo-library` approaches 550GB — at that point the backup drive needs to be replaced with a larger spare. Spares on hand (see `jctsh-parts-inventory.md`): Seagate Expansion 1TB (requires external power, unlike the currently bus-powered drives) or WD 750GB (too small — not a viable replacement).

**Note:** the primary library is at 615GB, already past the 550GB flag point. Worth deciding whether the Expansion 1TB swap should happen soon, or whether 640GB of headroom (Momentus's full capacity) is enough runway for now given the library's growth rate.

## How to Verify Backup Is Working

```bash
crontab -l                                    # confirm job is present and uncommented
/usr/local/bin/photo-library-backup.sh        # manual run
tail -f /var/log/photo-library-backup.log     # watch progress
df -h /mnt/photo-library-backup               # confirm space used matches primary
```

Also check the JCTsh log dashboard (`http://raspberrypi.local/`) for the `photo-server` component's `"Backup starting."`/`"Backup complete."` pair after any run, scheduled or manual.

## Related

See `jctsh-network.md`'s **Scheduled Maintenance Windows** table for how this job's timing relates to the M8's own weekly reboot and other recurring jobs across the network.
