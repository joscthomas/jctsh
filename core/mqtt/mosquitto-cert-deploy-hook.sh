#!/bin/bash
# Certbot deploy-hook for jctsh.duckdns.org.
# Installed at /etc/letsencrypt/renewal-hooks/deploy/mosquitto-reload.sh
# Runs automatically after initial issuance and every renewal.
set -euo pipefail

CERT_DIR="/etc/letsencrypt/live/jctsh.duckdns.org"
DEST_DIR="/etc/mosquitto/certs"

cp "$CERT_DIR/fullchain.pem" "$DEST_DIR/fullchain.pem"
cp "$CERT_DIR/privkey.pem" "$DEST_DIR/privkey.pem"
chown root:mosquitto "$DEST_DIR/fullchain.pem" "$DEST_DIR/privkey.pem"
chmod 640 "$DEST_DIR/fullchain.pem" "$DEST_DIR/privkey.pem"

systemctl restart mosquitto
