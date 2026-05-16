#!/bin/bash
# JCTsh Pi setup — run once as: bash /home/pi/jctsh/core/logging/setup_pi.sh

set -e

echo "[1/5] Installing Python dependencies..."
pip install -r /home/pi/jctsh/core/logging/requirements.txt --break-system-packages

echo "[2/5] Creating log server systemd service..."
sudo tee /etc/systemd/system/jctsh-logging.service > /dev/null << 'EOF'
[Unit]
Description=JCTsh Log Server
After=network.target mosquitto.service

[Service]
ExecStart=/usr/bin/python3 /home/pi/jctsh/core/logging/log_server.py
WorkingDirectory=/home/pi/jctsh/core/logging
Restart=always
User=pi
AmbientCapabilities=CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
EOF

echo "[3/5] Creating Avahi CNAME service..."
sudo tee /etc/systemd/system/jctsh-avahi.service > /dev/null << 'EOF'
[Unit]
Description=JCTsh mDNS hostname alias (JCTsh.local)
After=avahi-daemon.service
Requires=avahi-daemon.service

[Service]
ExecStart=/usr/bin/avahi-publish --no-fail -c JCTsh raspberrypi
Restart=on-failure
User=pi

[Install]
WantedBy=multi-user.target
EOF

echo "[4/5] Creating Avahi HTTP service discovery file..."
sudo tee /etc/avahi/services/jctsh.service > /dev/null << 'EOF'
<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name>JCTsh</name>
  <service>
    <type>_http._tcp</type>
    <port>80</port>
  </service>
</service-group>
EOF

echo "[5/5] Enabling and starting services..."
sudo systemctl daemon-reload
sudo systemctl enable jctsh-logging jctsh-avahi
sudo systemctl start jctsh-logging jctsh-avahi

echo ""
echo "=== Status ==="
sudo systemctl status jctsh-logging jctsh-avahi --no-pager
