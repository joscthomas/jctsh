#!/bin/bash
set -a
. /etc/jctsh/heartbeat.env
set +a

MQTT_HOST=192.168.1.117
MQTT_USER=photo-server
LOG_TOPIC=jctsh/server/photo-server/log

mosquitto_pub -h "$MQTT_HOST" -p 1883 -u "$MQTT_USER" -P "$MQTT_PASSWORD" -t "$LOG_TOPIC" \
  -m '{"component":"photo-server","category":"System","message":"Backup starting."}'

rsync -av --delete /mnt/photo-library/ /mnt/photo-library-backup/
RC=$?

if [ $RC -eq 0 ]; then
  mosquitto_pub -h "$MQTT_HOST" -p 1883 -u "$MQTT_USER" -P "$MQTT_PASSWORD" -t "$LOG_TOPIC" \
    -m '{"component":"photo-server","category":"System","message":"Backup complete."}'
else
  mosquitto_pub -h "$MQTT_HOST" -p 1883 -u "$MQTT_USER" -P "$MQTT_PASSWORD" -t "$LOG_TOPIC" \
    -m "{\"component\":\"photo-server\",\"category\":\"Alert\",\"message\":\"Backup failed (rsync exit $RC).\"}"
fi

exit $RC
