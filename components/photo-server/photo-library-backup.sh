#!/bin/bash
set -a
. /etc/jctsh/heartbeat.env
set +a

MQTT_HOST=192.168.1.117
MQTT_USER=photo-server
LOG_TOPIC=jctsh/server/photo-server/log

JOSEPH_ID=b877bff7-37a3-465e-8920-c9fa1ccf3ce9
ROBIN_ID=34fc3f59-37ee-400d-bde3-9273c9501a29

# Split by account: each destination gets one owner's upload/thumbs/encoded-video
# tree, excluded by the *other* owner's UUID (any new per-user top-level dir
# Immich adds later is included automatically since only the other owner's ID is
# excluded, not an explicit allow-list). Shared, non-per-user data (backups/ —
# Postgres DB dumps — plus the negligible library/profile/takeout-staging dirs)
# goes to both. lost+found is filesystem cruft, not Immich data, excluded from both.
#
# --delete-before (not plain --delete, which defaults to --delete-during): with
# --delete-during, deletions happen incrementally as rsync walks the tree, in
# directory-encounter order. backups/ (shared, not per-user) gets walked before the
# per-user upload/thumbs/encoded-video dirs where the actual space-freeing deletions
# live -- on a destination that's already full, rsync fails writing a new file in
# backups/ before it ever reaches the deletions that would have freed the space
# needed. --delete-before removes everything that needs removing up front, before
# any transfer starts, avoiding that chicken-and-egg deadlock.
#
# --delete-excluded (required in addition to --delete*): by default rsync's --delete
# variants only delete files that are missing from the (filtered) source -- files
# matching an --exclude rule are left alone on the destination, not deleted, as a
# protective default so an exclude rule can't accidentally wipe data. Since the whole
# point here is to remove the *other* account's already-excluded files from each
# destination, --delete-excluded is required to actually do that. Without it, this
# script silently never cleans up Momentus, which is exactly what happened here.

mosquitto_pub -h "$MQTT_HOST" -p 1883 -u "$MQTT_USER" -P "$MQTT_PASSWORD" -t "$LOG_TOPIC" \
  -m '{"component":"photo-server","category":"System","message":"Backup starting."}'

rsync -av --delete-before --delete-excluded \
  --exclude="lost+found" \
  --exclude="*/${ROBIN_ID}/***" \
  /mnt/photo-library/ /mnt/photo-library-backup-joseph/
RC_JOSEPH=$?

rsync -av --delete-before --delete-excluded \
  --exclude="lost+found" \
  --exclude="*/${JOSEPH_ID}/***" \
  /mnt/photo-library/ /mnt/photo-library-backup/
RC_ROBIN=$?

if [ $RC_JOSEPH -eq 0 ] && [ $RC_ROBIN -eq 0 ]; then
  # CARD-0051: heartbeat watches this marker's age to catch the backup simply never
  # running at all (cron broken, script missing) — a gap the success/failure MQTT
  # message above can't cover, since it only fires when the script actually runs.
  touch /home/jct/photo-library-backup-success.stamp
  mosquitto_pub -h "$MQTT_HOST" -p 1883 -u "$MQTT_USER" -P "$MQTT_PASSWORD" -t "$LOG_TOPIC" \
    -m '{"component":"photo-server","category":"System","message":"Backup complete."}'
else
  mosquitto_pub -h "$MQTT_HOST" -p 1883 -u "$MQTT_USER" -P "$MQTT_PASSWORD" -t "$LOG_TOPIC" \
    -m "{\"component\":\"photo-server\",\"category\":\"Alert\",\"message\":\"Backup failed (joseph exit $RC_JOSEPH, robin exit $RC_ROBIN).\"}"
fi

exit $(( RC_JOSEPH != 0 || RC_ROBIN != 0 ))
