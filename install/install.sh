#!/bin/bash
# TAK-ADSB-Feeder One-Line Installer
# wget -O - https://raw.githubusercontent.com/cfd2474/feeder_test/main/install/install.sh | sudo bash

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  TAK-ADSB-Feeder Installer v2.0"
echo "  Ultrafeeder + TAK Server Integration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Install Docker
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

# Install Python
echo "Installing Python dependencies..."
apt-get update -qq
apt-get install -y python3 wget curl

# Create directories
echo "Creating directories..."
mkdir -p /opt/adsb/{config,scripts,ultrafeeder}

# Download files
echo "Downloading configuration files..."
REPO="https://raw.githubusercontent.com/cfd2474/feeder_test/main"
wget -q $REPO/config/docker-compose.yml -O /opt/adsb/config/docker-compose.yml
wget -q $REPO/config/env-template -O /opt/adsb/config/.env
wget -q $REPO/scripts/config_builder.py -O /opt/adsb/scripts/config_builder.py
chmod +x /opt/adsb/scripts/config_builder.py

# Create systemd service
echo "Creating systemd service..."
cat > /etc/systemd/system/ultrafeeder.service << 'SVCEOF'
[Unit]
Description=TAK-ADSB Ultrafeeder
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/adsb/config
EnvironmentFile=/opt/adsb/config/.env
ExecStartPre=/usr/bin/python3 /opt/adsb/scripts/config_builder.py
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable ultrafeeder

# Set permissions
if [ "$SUDO_USER" ]; then
    chown -R $SUDO_USER:$SUDO_USER /opt/adsb
fi

# Done
IP=$(hostname -I | awk '{print $1}')
echo ""
echo "✓ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Configure: sudo nano /opt/adsb/config/.env"
echo "2. Start: sudo systemctl start ultrafeeder"  
echo "3. Map: http://$IP:8080"
echo ""
