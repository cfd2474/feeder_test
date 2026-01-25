#!/bin/bash
# TAKNET-PS-ADSB-Feeder One-Line Installer v2.8
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
echo "  TAKNET-PS-ADSB-Feeder Installer v2.8"
echo "  Ultrafeeder + TAKNET-PS + Web UI"
echo "  + Network Discovery & WiFi Hotspot"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "Cannot detect OS. This installer supports Debian/Ubuntu/Raspberry Pi OS."
    exit 1
fi

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

# Install system packages
echo "Installing system packages..."
apt-get update
apt-get install -y \
    rtl-sdr \
    python3-pip \
    python3-flask \
    python3-requests \
    python3-dotenv \
    vnstat \
    curl \
    wget \
    git \
    avahi-daemon \
    nginx \
    hostapd \
    dnsmasq \
    dhcpcd5 \
    network-manager

echo "✓ System packages installed"

# Configure mDNS hostname
echo "Configuring mDNS hostname (taknet-ps.local)..."
hostnamectl set-hostname taknet-ps

# Ensure avahi-daemon is enabled and started
systemctl enable avahi-daemon
systemctl start avahi-daemon

echo "✓ mDNS configured - device accessible at taknet-ps.local"

# Create directory structure
echo "Creating directory structure..."
mkdir -p /opt/adsb/{config,scripts,web/{templates,static/{css,js}}}
mkdir -p /opt/adsb/config/ultrafeeder

# Create web directory structure
echo "Setting up web application..."

# Download web files
cd /opt/adsb/web
wget -q https://raw.githubusercontent.com/cfd2474/feeder_test/main/web/app.py -O app.py

mkdir -p templates static/css static/js

cd templates
wget -q https://raw.githubusercontent.com/cfd2474/feeder_test/main/web/templates/setup-sdr.html -O setup-sdr.html
wget -q https://raw.githubusercontent.com/cfd2474/feeder_test/main/web/templates/setup.html -O setup.html
wget -q https://raw.githubusercontent.com/cfd2474/feeder_test/main/web/templates/loading.html -O loading.html
wget -q https://raw.githubusercontent.com/cfd2474/feeder_test/main/web/templates/dashboard.html -O dashboard.html
wget -q https://raw.githubusercontent.com/cfd2474/feeder_test/main/web/templates/settings.html -O settings.html

cd ../static/css
wget -q https://raw.githubusercontent.com/cfd2474/feeder_test/main/web/static/css/style.css -O style.css

cd ../js
wget -q https://raw.githubusercontent.com/cfd2474/feeder_test/main/web/static/js/setup.js -O setup.js
wget -q https://raw.githubusercontent.com/cfd2474/feeder_test/main/web/static/js/dashboard.js -O dashboard.js

echo "✓ Web files downloaded"

# Download config files
cd /opt/adsb/config
wget -q https://raw.githubusercontent.com/cfd2474/feeder_test/main/config/docker-compose.yml -O docker-compose.yml
wget -q https://raw.githubusercontent.com/cfd2474/feeder_test/main/config/env-template -O env-template

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    cp env-template .env
    echo "✓ Created initial .env file"
else
    echo "✓ Existing .env file preserved"
fi

# Download scripts
cd /opt/adsb/scripts
wget -q https://raw.githubusercontent.com/cfd2474/feeder_test/main/scripts/config_builder.py -O config_builder.py
chmod +x config_builder.py

echo "✓ Configuration files downloaded"

# Configure Nginx reverse proxy
echo "Configuring Nginx reverse proxy..."
cat > /etc/nginx/sites-available/taknet-ps << 'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name taknet-ps.local taknet-ps _;

    # Root redirects to /web
    location = / {
        return 301 /web;
    }

    # Web UI (Flask on port 5000)
    location /web {
        rewrite ^/web$ /web/ permanent;
        rewrite ^/web/(.*)$ /$1 break;
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Tar1090 Map (port 8080)
    location /map {
        rewrite ^/map$ /map/ permanent;
        rewrite ^/map/(.*)$ /$1 break;
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "OK";
        add_header Content-Type text/plain;
    }
}
EOF

# Remove default nginx site
rm -f /etc/nginx/sites-enabled/default

# Enable our site
ln -sf /etc/nginx/sites-available/taknet-ps /etc/nginx/sites-enabled/

# Test nginx config
nginx -t

# Enable and start nginx
systemctl enable nginx
systemctl restart nginx

echo "✓ Nginx configured - taknet-ps.local/web and taknet-ps.local/map"

# Create systemd service for web UI
cat > /etc/systemd/system/adsb-web.service << 'EOF'
[Unit]
Description=TAKNET-PS ADS-B Web Configuration Interface
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/adsb/web
Environment="FLASK_APP=app.py"
ExecStart=/usr/bin/python3 /opt/adsb/web/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create systemd service for ultrafeeder with config builder
cat > /etc/systemd/system/ultrafeeder.service << 'EOF'
[Unit]
Description=TAKNET-PS Ultrafeeder ADS-B Service
After=network.target docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/adsb/config
ExecStartPre=/usr/bin/python3 /opt/adsb/scripts/config_builder.py
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

# Enable services
systemctl enable adsb-web
systemctl enable ultrafeeder

# Start web UI immediately
systemctl start adsb-web

echo "✓ Systemd services configured"

# Enable vnstat monitoring
echo "Configuring network monitoring..."
systemctl enable vnstat
systemctl start vnstat

# Create remote-adsb user for SSH access
if ! id -u remote-adsb &>/dev/null; then
    echo "Creating remote-adsb user..."
    useradd -m -s /bin/bash remote-adsb
    
    # Set password
    echo "remote-adsb:adsb2024" | chpasswd
    
    # Create sudoers file for limited privileges
    cat > /etc/sudoers.d/remote-adsb << 'EOSUDO'
# Allow remote-adsb user to manage ADS-B services
remote-adsb ALL=(ALL) NOPASSWD: /bin/systemctl restart ultrafeeder
remote-adsb ALL=(ALL) NOPASSWD: /bin/systemctl restart adsb-web
remote-adsb ALL=(ALL) NOPASSWD: /bin/systemctl status ultrafeeder
remote-adsb ALL=(ALL) NOPASSWD: /bin/systemctl status adsb-web
remote-adsb ALL=(ALL) NOPASSWD: /bin/journalctl -u ultrafeeder *
remote-adsb ALL=(ALL) NOPASSWD: /bin/journalctl -u adsb-web *
remote-adsb ALL=(ALL) NOPASSWD: /usr/bin/docker ps *
remote-adsb ALL=(ALL) NOPASSWD: /usr/bin/docker logs *
remote-adsb ALL=(ALL) NOPASSWD: /usr/bin/docker compose *
remote-adsb ALL=(ALL) NOPASSWD: /usr/bin/vnstat *
EOSUDO
    
    chmod 440 /etc/sudoers.d/remote-adsb
    echo "✓ Created remote-adsb user (password: adsb2024)"
else
    echo "✓ remote-adsb user already exists"
fi

# Install WiFi hotspot components
echo "Installing WiFi hotspot components..."

# Download WiFi management scripts
cd /opt/adsb/scripts
wget -q https://raw.githubusercontent.com/cfd2474/feeder_test/main/scripts/wifi-manager.sh -O wifi-manager.sh
chmod +x wifi-manager.sh

# Create WiFi hotspot systemd service
cat > /etc/systemd/system/taknet-wifi-manager.service << 'EOF'
[Unit]
Description=TAKNET-PS WiFi Connection Manager
After=network.target
Before=ultrafeeder.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/opt/adsb/scripts/wifi-manager.sh check
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable taknet-wifi-manager

echo "✓ WiFi hotspot manager installed"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Installation Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next steps:"
echo ""
echo "  1. Access web interface:"
echo "     http://taknet-ps.local/web"
echo "     (or http://$(hostname -I | awk '{print $1}')/web)"
echo ""
echo "  2. Configure your ADS-B receiver through the wizard"
echo ""
echo "  3. Access tar1090 map:"
echo "     http://taknet-ps.local/map"
echo ""
echo "  4. SSH access (optional):"
echo "     ssh remote-adsb@taknet-ps.local"
echo "     Password: adsb2024"
echo ""
echo "  5. Monitor network usage:"
echo "     vnstat"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "NOTE: If device loses network connectivity, it will"
echo "automatically create a WiFi hotspot named 'TAKNET-PS'"
echo "with a captive portal for network configuration."
echo ""
