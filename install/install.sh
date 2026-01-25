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
apt-get install -y python3-flask python3-pip wget curl rtl-sdr vnstat nginx avahi-daemon avahi-utils libnss-mdns hostapd dnsmasq iptables wireless-tools rfkill

echo "✓ All packages installed"

# Configure mDNS (taknet-ps.local)
echo "Configuring mDNS hostname..."
hostnamectl set-hostname taknet-ps
sed -i '/127.0.1.1/d' /etc/hosts
echo "127.0.1.1    taknet-ps" >> /etc/hosts

cat > /etc/avahi/avahi-daemon.conf << 'AVAHIEOF'
[server]
host-name=taknet-ps
domain-name=local
use-ipv4=yes
use-ipv6=no
allow-interfaces=wlan0,eth0
deny-interfaces=ap0

[publish]
publish-addresses=yes
publish-hinfo=yes
publish-workstation=yes
publish-domain=yes
AVAHIEOF

systemctl enable avahi-daemon
systemctl restart avahi-daemon

echo "✓ mDNS configured (taknet-ps.local)"

# Configure vnstat for 30-day retention
echo "Configuring vnstat for network monitoring..."
systemctl enable vnstat
systemctl start vnstat

# Set vnstat to 30-day retention
if [ -f /etc/vnstat.conf ]; then
    sed -i 's/MonthRotate 12/MonthRotate 1/' /etc/vnstat.conf
    sed -i 's/DayGraphDays 7/DayGraphDays 30/' /etc/vnstat.conf
fi

echo "✓ vnstat configured (30-day retention)"

# Create remote user with sudo privileges (Tailscale-only access)
echo "Creating remote user..."
if ! id "remote" &>/dev/null; then
    useradd -m -s /bin/bash remote
    echo "remote:adsb" | chpasswd
    
    # Add to sudo group
    usermod -aG sudo remote
    
    # Create sudoers file for adsb project commands
    cat > /etc/sudoers.d/remote-adsb << 'SUDOEOF'
# Remote user sudo privileges for ADSB project
remote ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart ultrafeeder
remote ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart adsb-web
remote ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop ultrafeeder
remote ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop adsb-web
remote ALL=(ALL) NOPASSWD: /usr/bin/systemctl start ultrafeeder
remote ALL=(ALL) NOPASSWD: /usr/bin/systemctl start adsb-web
remote ALL=(ALL) NOPASSWD: /usr/bin/systemctl status ultrafeeder
remote ALL=(ALL) NOPASSWD: /usr/bin/systemctl status adsb-web
remote ALL=(ALL) NOPASSWD: /usr/bin/docker ps
remote ALL=(ALL) NOPASSWD: /usr/bin/docker logs *
remote ALL=(ALL) NOPASSWD: /usr/bin/docker compose -f /opt/adsb/config/docker-compose.yml *
remote ALL=(ALL) NOPASSWD: /usr/bin/docker restart ultrafeeder
remote ALL=(ALL) NOPASSWD: /usr/bin/docker restart fr24
remote ALL=(ALL) NOPASSWD: /usr/bin/journalctl -u ultrafeeder *
remote ALL=(ALL) NOPASSWD: /usr/bin/journalctl -u adsb-web *
remote ALL=(ALL) NOPASSWD: /usr/bin/vnstat *
remote ALL=(ALL) NOPASSWD: /usr/bin/python3 /opt/adsb/scripts/config_builder.py
SUDOEOF
    
    chmod 0440 /etc/sudoers.d/remote-adsb
    
    echo "✓ User 'remote' created with password 'adsb'"
    echo "  Tailscale-only access recommended (configure SSH to allow)"
else
    echo "✓ User 'remote' already exists"
fi

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
wget -q $REPO/web/templates/setup-sdr.html -O /opt/adsb/web/templates/setup-sdr.html
wget -q $REPO/web/templates/dashboard.html -O /opt/adsb/web/templates/dashboard.html
wget -q $REPO/web/templates/settings.html -O /opt/adsb/web/templates/settings.html
wget -q $REPO/web/templates/loading.html -O /opt/adsb/web/templates/loading.html
wget -q $REPO/web/static/css/style.css -O /opt/adsb/web/static/css/style.css
wget -q $REPO/web/static/js/setup.js -O /opt/adsb/web/static/js/setup.js
wget -q $REPO/web/static/js/dashboard.js -O /opt/adsb/web/static/js/dashboard.js
chmod +x /opt/adsb/web/app.py

# Configure Nginx reverse proxy
echo "Configuring Nginx reverse proxy..."
cat > /etc/nginx/sites-available/taknet-ps << 'NGINXEOF'
server {
    listen 80 default_server;
    server_name taknet-ps.local taknet-ps _;
    
    client_max_body_size 10M;
    
    # Root and /web -> Flask (port 5000)
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_connect_timeout 300;
        proxy_read_timeout 300;
    }
    
    location /web {
        rewrite ^/web(/.*)$ $1 break;
        rewrite ^/web$ / break;
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }
    
    # /map -> tar1090 (port 8080)
    location /map {
        rewrite ^/map(/.*)$ $1 break;
        rewrite ^/map$ / break;
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_buffering off;
    }
}
NGINXEOF

rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/taknet-ps /etc/nginx/sites-enabled/
systemctl enable nginx
systemctl restart nginx

echo "✓ Nginx configured (taknet-ps.local/, /web, /map)"

# Install WiFi Hotspot Manager
echo "Installing WiFi hotspot manager..."
mkdir -p /opt/adsb/wifi-manager/templates

# WiFi check script
cat > /opt/adsb/wifi-manager/check-connection.sh << 'CHECKEOF'
#!/bin/bash
for i in {1..3}; do
    if ip addr show | grep -q "inet.*brd.*scope global"; then
        if ping -c 1 -W 3 8.8.8.8 >/dev/null 2>&1 || ping -c 1 -W 3 1.1.1.1 >/dev/null 2>&1; then
            exit 0
        fi
    fi
    [ $i -lt 3 ] && sleep 2
done
exit 1
CHECKEOF

chmod +x /opt/adsb/wifi-manager/check-connection.sh

# Hotspot start script
cat > /opt/adsb/wifi-manager/start-hotspot.sh << 'STARTEOF'
#!/bin/bash
systemctl stop wpa_supplicant 2>/dev/null || true
rfkill unblock wifi
ip link set wlan0 down
ip addr flush dev wlan0
ip addr add 192.168.4.1/24 dev wlan0
ip link set wlan0 up

cat > /etc/hostapd/hostapd.conf << EOF
interface=wlan0
driver=nl80211
ssid=TAKNET-PS
hw_mode=g
channel=6
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
EOF

cat > /etc/dnsmasq.conf << EOF
interface=wlan0
bind-interfaces
server=8.8.8.8
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
address=/#/192.168.4.1
EOF

systemctl unmask hostapd dnsmasq
systemctl enable hostapd dnsmasq
systemctl restart hostapd dnsmasq

iptables -t nat -F
iptables -F
iptables -t nat -A PREROUTING -i wlan0 -p tcp --dport 80 -j DNAT --to-destination 192.168.4.1:5001
iptables -t nat -A PREROUTING -i wlan0 -p tcp --dport 443 -j DNAT --to-destination 192.168.4.1:5001
STARTEOF

chmod +x /opt/adsb/wifi-manager/start-hotspot.sh

# Hotspot stop script
cat > /opt/adsb/wifi-manager/stop-hotspot.sh << 'STOPEOF'
#!/bin/bash
systemctl stop hostapd dnsmasq 2>/dev/null || true
systemctl disable hostapd dnsmasq 2>/dev/null || true
iptables -t nat -F
iptables -F
ip addr flush dev wlan0 2>/dev/null || true
systemctl restart wpa_supplicant 2>/dev/null || true
STOPEOF

chmod +x /opt/adsb/wifi-manager/stop-hotspot.sh

# Download captive portal files from GitHub
wget -q $REPO/wifi-manager/captive-portal.py -O /opt/adsb/wifi-manager/captive-portal.py || echo "Note: Captive portal will use built-in version"
wget -q $REPO/wifi-manager/templates/wifi-setup.html -O /opt/adsb/wifi-manager/templates/wifi-setup.html || echo "Note: WiFi template will use built-in version"
chmod +x /opt/adsb/wifi-manager/captive-portal.py

# Network monitor script
cat > /opt/adsb/wifi-manager/network-monitor.sh << 'MONITOREOF'
#!/bin/bash
sleep 60  # Wait for boot
while true; do
    if ! /opt/adsb/wifi-manager/check-connection.sh; then
        systemctl stop wpa_supplicant 2>/dev/null || true
        /opt/adsb/wifi-manager/start-hotspot.sh
        systemctl start captive-portal
        while true; do
            sleep 300
        done
    fi
    sleep 30
done
MONITOREOF

chmod +x /opt/adsb/wifi-manager/network-monitor.sh

# Create systemd services
cat > /etc/systemd/system/captive-portal.service << 'PORTALEOF'
[Unit]
Description=TAKNET-PS WiFi Captive Portal
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/adsb/wifi-manager
ExecStart=/usr/bin/python3 /opt/adsb/wifi-manager/captive-portal.py
Restart=always

[Install]
WantedBy=multi-user.target
PORTALEOF

cat > /etc/systemd/system/network-monitor.service << 'MONITOREOF'
[Unit]
Description=TAKNET-PS Network Monitor
After=network.target

[Service]
Type=simple
ExecStart=/opt/adsb/wifi-manager/network-monitor.sh
Restart=always

[Install]
WantedBy=multi-user.target
MONITOREOF

systemctl daemon-reload
systemctl enable network-monitor captive-portal

echo "✓ WiFi hotspot manager installed"

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

# Download SSH Tailscale configuration script
echo "Downloading SSH configuration script..."
wget -q $REPO/configure-ssh-tailscale.sh -O /opt/adsb/configure-ssh-tailscale.sh
chmod +x /opt/adsb/configure-ssh-tailscale.sh

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
echo "📡 Remote Access:"
echo "   • User: remote"
echo "   • Password: adsb"
echo "   • Limited sudo privileges for ADSB commands"
echo ""
echo "🔒 To restrict 'remote' user to Tailscale network only:"
echo "   cd /opt/adsb"
echo "   sudo ./configure-ssh-tailscale.sh"
echo ""
echo "📊 Network Monitoring:"
echo "   • vnstat configured (30-day retention)"
echo "   • Usage: vnstat -d (daily stats)"
echo ""
