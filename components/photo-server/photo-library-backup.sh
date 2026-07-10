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

mosquitto_pub -h "$MQTT_HOST" -p 1883 -u "$MQTT_USER" -P "$MQTT_PASSWORD" -t "$LOG_TOPIC" \
  -m '{"component":"photo-server","category":"System","message":"Backup starting."}'

rsync -av --delete \
  --exclude="lost+found" \
  --exclude="*/${ROBIN_ID}/***" \
  /mnt/photo-library/ /mnt/photo-library-backup-joseph/
RC_JOSEPH=$?

rsync -av --delete \
  --exclude="lost+found" \
  --exclude="*/${JOSEPH_ID}/***" \
  /mnt/photo-library/ /mnt/photo-library-backup/
RC_ROBIN=$?

if [ $RC_JOSEPH -eq 0 ] && [ $RC_ROBIN -eq 0 ]; then
  mosquitto_pub -h "$MQTT_HOST" -p 1883 -u "$MQTT_USER" -P "$MQTT_PASSWORD" -t "$LOG_TOPIC" \
    -m '{"component":"photo-server","category":"System","message":"Backup complete."}'
else
  mosquitto_pub -h "$MQTT_HOST" -p 1883 -u "$MQTT_USER" -P "$MQTT_PASSWORD" -t "$LOG_TOPIC" \
    -m "{\"component\":\"photo-server\",\"category\":\"Alert\",\"message\":\"Backup failed (joseph exit $RC_JOSEPH, robin exit $RC_ROBIN).\"}"
fi

exit $(( RC_JOSEPH != 0 || RC_ROBIN != 0 ))
