#!/bin/bash
# TAKNET-PS-ADSB-Feeder One-Line Installer v2.1
# curl -fsSL https://raw.githubusercontent.com/cfd2474/feeder_test/main/install/install.sh | sudo bash

set -e

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  ⚠️  ERROR: Root privileges required"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "This installer must be run with sudo to:"
    echo "  • Install Docker"
    echo "  • Create systemd services"
    echo "  • Configure system packages"
    echo ""
    echo "Please run with sudo:"
    echo ""
    echo "  curl -fsSL https://raw.githubusercontent.com/cfd2474/feeder_test/main/install/install.sh | sudo bash"
    echo ""
    echo "Or if you downloaded the script:"
    echo ""
    echo "  sudo bash install.sh"
    echo ""
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  TAKNET-PS-ADSB-Feeder Installer v2.1"
echo "  Ultrafeeder + TAKNET-PS + Web UI"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Install Docker
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl daemon-reload
    systemctl enable docker
    systemctl start docker
    
    # Add user to docker group if SUDO_USER is set
    if [ "$SUDO_USER" ]; then
        usermod -aG docker $SUDO_USER
        echo "✓ Added $SUDO_USER to docker group"
    fi
else
    echo "✓ Docker already installed"
fi

# Install Python and Flask
echo "Installing Python dependencies..."
apt-get update -qq
apt-get install -y python3-flask python3-pip wget curl rtl-sdr

echo "✓ RTL-SDR tools installed"

# Create directories
echo "Creating directories..."
mkdir -p /opt/adsb/{config,scripts,ultrafeeder,web/{templates,static/{css,js}}}

# Download files
echo "Downloading configuration files..."
REPO="https://raw.githubusercontent.com/cfd2474/feeder_test/main"

# Config files
wget -q $REPO/config/docker-compose.yml -O /opt/adsb/config/docker-compose.yml
wget -q $REPO/config/env-template -O /opt/adsb/config/.env
wget -q $REPO/scripts/config_builder.py -O /opt/adsb/scripts/config_builder.py
chmod +x /opt/adsb/scripts/config_builder.py

# Web UI files
echo "Installing Web UI..."
wget -q $REPO/web/app.py -O /opt/adsb/web/app.py
wget -q $REPO/web/templates/setup.html -O /opt/adsb/web/templates/setup.html
wget -q $REPO/web/templates/dashboard.html -O /opt/adsb/web/templates/dashboard.html
wget -q $REPO/web/templates/settings.html -O /opt/adsb/web/templates/settings.html
wget -q $REPO/web/static/css/style.css -O /opt/adsb/web/static/css/style.css
wget -q $REPO/web/static/js/setup.js -O /opt/adsb/web/static/js/setup.js
wget -q $REPO/web/static/js/dashboard.js -O /opt/adsb/web/static/js/dashboard.js
chmod +x /opt/adsb/web/app.py

# Create ultrafeeder systemd service
echo "Creating ultrafeeder service..."
cat > /etc/systemd/system/ultrafeeder.service << 'SVCEOF'
[Unit]
Description=TAKNET-PS-ADSB Ultrafeeder
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

# Create web UI systemd service
echo "Creating web interface service..."
cat > /etc/systemd/system/adsb-web.service << 'WEBSVC'
[Unit]
Description=TAKNET-PS-ADSB Web Interface
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/adsb/web
ExecStart=/usr/bin/python3 /opt/adsb/web/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
WEBSVC

# Enable services
systemctl daemon-reload
systemctl enable ultrafeeder
systemctl enable adsb-web

# Start web UI (but not ultrafeeder - needs config first)
systemctl start adsb-web

# Set permissions
if [ "$SUDO_USER" ]; then
    chown -R $SUDO_USER:$SUDO_USER /opt/adsb
fi

# Get IP address
IP=$(hostname -I | awk '{print $1}')

# Done
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✓ Installation complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 Open your browser and go to:"
echo ""
echo "   http://$IP:5000"
echo ""
echo "   Complete the setup wizard to configure your feeder."
echo ""
echo "After setup, you can access:"
echo "   • Setup/Dashboard: http://$IP:5000"
echo "   • Live Map: http://$IP:8080"
echo ""
echo "Manual commands (if needed):"
echo "   • Start: sudo systemctl start ultrafeeder"
echo "   • Restart: sudo systemctl restart ultrafeeder"
echo "   • Logs: sudo docker logs ultrafeeder"
echo ""
