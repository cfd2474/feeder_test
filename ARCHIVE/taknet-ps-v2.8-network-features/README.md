# TAKNET-PS-ADSB-Feeder v2.8

**Complete ADS-B aircraft tracking system with automatic WiFi hotspot fallback and network discovery**

[![Version](https://img.shields.io/badge/version-2.8-blue.svg)](https://github.com/cfd2474/feeder_test)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-red.svg)](https://www.raspberrypi.com/)

---

## ✨ What's New in v2.8

### 🌐 Network Discovery
- Access your device at **`taknet-ps.local`** - no more hunting for IP addresses
- Clean URLs: `taknet-ps.local/web` for UI, `taknet-ps.local/map` for aircraft map
- Professional nginx reverse proxy with WebSocket support

### 🛜 Automatic WiFi Hotspot
- **Zero-touch recovery**: Device creates `TAKNET-PS` hotspot when disconnected
- **Captive portal**: Auto-redirects phones/tablets to WiFi configuration
- **Smart retry**: Automatically reboots and retries connection
- **Field deployment ready**: Perfect for remote installations

---

## 🚀 Quick Start

### One-Line Installation
```bash
curl -fsSL https://raw.githubusercontent.com/cfd2474/feeder_test/main/install/install.sh | sudo bash
```

### What Gets Installed
- ✅ Docker + Docker Compose
- ✅ Ultrafeeder ADS-B container
- ✅ FlightRadar24 container (optional)
- ✅ Web-based configuration interface
- ✅ mDNS for network discovery (`taknet-ps.local`)
- ✅ Nginx reverse proxy
- ✅ WiFi hotspot manager
- ✅ TAK Server integration (hardcoded)
- ✅ Tailscale VPN support
- ✅ Network monitoring (vnstat)
- ✅ Remote SSH access

### First-Time Setup
1. **Boot device** - System automatically starts WiFi hotspot if no network
2. **Join WiFi** - Connect to `TAKNET-PS` (no password)
3. **Configure** - Phone/tablet auto-opens WiFi wizard
4. **Select network** - Choose your WiFi and enter password
5. **Connect** - Device reboots and connects
6. **Access** - Open `http://taknet-ps.local/web` on any browser

---

## 📋 Features

### Core Functionality
- **SDR Auto-Detection** - Automatic RTL-SDR device discovery
- **Web-Based Wizard** - 4-step setup (SDR → Location → VPN → Feeds)
- **TAK Server Integration** - Hardcoded connection to your private TAK server
- **Dual-Server Failover** - Automatic failover between Tailscale and public IPs
- **MLAT Support** - Multilateration for improved accuracy

### Network Features (NEW in v2.8)
- **mDNS Hostname** - `taknet-ps.local` network discovery
- **URL Path Routing** - `/web` for UI, `/map` for aircraft display
- **WiFi Hotspot** - Auto-creates `TAKNET-PS` when disconnected
- **Captive Portal** - WiFi configuration wizard with network scanning
- **Auto-Retry** - Persistent connection attempts with fallback

### Additional Features
- **FlightRadar24** - Optional dedicated container with MLAT
- **Multiple Aggregators** - ADS-B Exchange, Airplanes.Live support
- **Network Monitoring** - 30-day bandwidth tracking with vnstat
- **Remote Access** - Dedicated SSH user with limited sudo
- **Live Dashboard** - Real-time service status monitoring

---

## 🌐 Access Points

### Normal Operation
- **Web Interface**: `http://taknet-ps.local/web`
- **Aircraft Map**: `http://taknet-ps.local/map`
- **SSH Access**: `ssh remote-adsb@taknet-ps.local`

### Hotspot Mode (No WiFi)
- **SSID**: `TAKNET-PS` (no password)
- **Device IP**: `10.42.0.1`
- **WiFi Portal**: `http://10.42.0.1/wifi-portal`
- **Web Interface**: `http://10.42.0.1/web`

---

## 🔧 Configuration

### SDR Configuration (Step 1)
- Auto-detect connected RTL-SDR devices
- Configure frequency (1090 MHz ADS-B or 978 MHz UAT)
- Set gain (auto or manual 0-50)
- Enable/disable bias tee power

### Location Setup (Step 2)
- Latitude, longitude, altitude
- Timezone selection
- Feeder name (auto-prepends ZIP code)

### Tailscale VPN (Step 3)
- Optional secure connection to private network
- Automatically configures hostname
- Enables primary TAK server connection

### Aggregators (Step 4)
- FlightRadar24 (with dedicated MLAT container)
- ADS-B Exchange
- Airplanes.Live
- All optional with individual enable/disable

---

## 🛜 WiFi Hotspot Behavior

### When Hotspot Activates
The device creates a WiFi hotspot named `TAKNET-PS` when:
1. Device boots with no network configured
2. Configured WiFi network is unavailable
3. Internet connectivity check fails

### Connection Flow
```
1. Device boots → No network detected
2. Creates TAKNET-PS hotspot
3. User joins hotspot on phone/tablet
4. Captive portal auto-opens (or browse to 10.42.0.1)
5. User selects WiFi network
6. User enters password
7. 5-second countdown displayed
8. Device reboots
9. Attempts connection
   ├─ Success → Normal operation
   └─ Failure → Recreates hotspot
```

### Manual Control
```bash
# Check current state
cat /opt/adsb/config/.wifi-state

# Manually start hotspot
sudo /opt/adsb/scripts/wifi-manager.sh start-hotspot

# Manually stop hotspot
sudo /opt/adsb/scripts/wifi-manager.sh stop-hotspot

# View WiFi logs
sudo tail -f /var/log/taknet-wifi.log
```

---

## 🏗️ Architecture

### Docker Containers
- **ultrafeeder** - Main ADS-B receiver/aggregator (port 8080)
- **fr24** - FlightRadar24 feeder (port 8754, optional)

### Services
- **adsb-web** - Flask web interface (port 5000)
- **ultrafeeder** - Docker Compose stack manager
- **nginx** - Reverse proxy (port 80)
- **taknet-wifi-manager** - WiFi hotspot manager
- **vnstat** - Network monitoring

### Network Stack
```
Internet → Nginx (port 80)
           ├─ /web → Flask (port 5000)
           ├─ /map → Tar1090 (port 8080)
           └─ /wifi-portal → Flask (port 5000)
```

---

## 📊 TAK Server Integration

### Primary Connection (Tailscale VPN)
- **Host**: `100.117.34.88` (Tailscale IP)
- **Port**: `30004` (Beast)
- **MLAT Port**: `30105`
- **Requires**: Tailscale VPN enabled

### Fallback Connection (Public)
- **Host**: `104.225.219.254` (Public IP)
- **Port**: `30004` (Beast)
- **MLAT Port**: `30105`
- **Requires**: No VPN needed

### Connection Mode
- **Auto** (default): Tries primary, falls back to public
- **Primary**: Forces Tailscale connection only
- **Fallback**: Forces public connection only

### Protected Settings
TAK Server settings are **hardcoded** and cannot be changed through the UI:
```
TAKNET_PS_SERVER_HOST_PRIMARY=100.117.34.88
TAKNET_PS_SERVER_HOST_FALLBACK=104.225.219.254
TAKNET_PS_SERVER_PORT=30004
TAKNET_PS_CONNECTION_MODE=auto
```

---

## 🔍 Monitoring & Diagnostics

### Web Dashboard
Access at `http://taknet-ps.local/web`:
- Service status (Ultrafeeder, FR24, TAK Server)
- Active feed connections
- Docker container health
- Manual service restart

### Command Line
```bash
# Check all services
sudo systemctl status adsb-web ultrafeeder nginx taknet-wifi-manager

# View logs
sudo journalctl -u adsb-web -n 50
sudo journalctl -u ultrafeeder -n 50
sudo journalctl -u taknet-wifi-manager -n 50

# Check Docker containers
sudo docker ps -a
sudo docker logs ultrafeeder
sudo docker logs fr24

# Network monitoring
vnstat
vnstat -d

# WiFi status
sudo systemctl status hostapd
cat /opt/adsb/config/.wifi-state
sudo tail -f /var/log/taknet-wifi.log

# Test mDNS
ping taknet-ps.local
avahi-browse -a -t
```

---

## 🔄 Updates

### Fresh Install (Recommended)
```bash
curl -fsSL https://raw.githubusercontent.com/cfd2474/feeder_test/main/install/install.sh | sudo bash
```

### Manual Update
```bash
# Update web files
cd /opt/adsb/web
sudo wget https://raw.githubusercontent.com/cfd2474/feeder_test/main/web/app.py -O app.py
sudo systemctl restart adsb-web

# Update scripts
cd /opt/adsb/scripts
sudo wget https://raw.githubusercontent.com/cfd2474/feeder_test/main/scripts/config_builder.py -O config_builder.py
sudo wget https://raw.githubusercontent.com/cfd2474/feeder_test/main/scripts/wifi-manager.sh -O wifi-manager.sh
sudo chmod +x wifi-manager.sh

# Update Docker config
cd /opt/adsb/config
sudo wget https://raw.githubusercontent.com/cfd2474/feeder_test/main/config/docker-compose.yml -O docker-compose.yml
sudo systemctl restart ultrafeeder
```

See [UPGRADE_NOTES_v2.8.md](UPGRADE_NOTES_v2.8.md) for detailed upgrade instructions.

---

## 🐛 Troubleshooting

### Can't Access taknet-ps.local
```bash
# Check Avahi daemon
sudo systemctl status avahi-daemon
sudo systemctl restart avahi-daemon

# Verify hostname
hostnamectl

# Test resolution
ping taknet-ps.local
```

### WiFi Hotspot Not Starting
```bash
# Check service status
sudo systemctl status taknet-wifi-manager

# View logs
sudo tail -f /var/log/taknet-wifi.log

# Manually trigger
sudo /opt/adsb/scripts/wifi-manager.sh start-hotspot

# Check if already connected
ip addr show wlan0
```

### Captive Portal Not Appearing
```bash
# Check if hotspot is running
sudo systemctl status hostapd
sudo systemctl status dnsmasq

# Verify device IP
ip addr show wlan0

# Test portal access
curl http://10.42.0.1/wifi-portal
```

### Services Won't Start
```bash
# Check Docker
sudo systemctl status docker
sudo docker ps -a

# Check web interface
sudo systemctl status adsb-web
sudo journalctl -u adsb-web -n 100

# Check ultrafeeder
sudo systemctl status ultrafeeder
sudo docker logs ultrafeeder
```

---

## 📁 File Locations

### Configuration
```
/opt/adsb/config/.env                          # Main configuration
/opt/adsb/config/.wifi-state                   # Current WiFi state
/opt/adsb/config/.wifi-credentials             # Temporary WiFi credentials
```

### Scripts
```
/opt/adsb/scripts/config_builder.py            # Config generator
/opt/adsb/scripts/wifi-manager.sh              # WiFi hotspot manager
```

### Web Application
```
/opt/adsb/web/app.py                           # Flask application
/opt/adsb/web/templates/                       # HTML templates
/opt/adsb/web/static/                          # CSS, JavaScript, images
```

### System Services
```
/etc/systemd/system/adsb-web.service           # Web UI service
/etc/systemd/system/ultrafeeder.service        # ADS-B service
/etc/systemd/system/taknet-wifi-manager.service # WiFi manager
```

### Nginx
```
/etc/nginx/sites-available/taknet-ps           # Site configuration
/etc/nginx/sites-enabled/taknet-ps             # Enabled site link
/var/log/nginx/taknet-ps-access.log            # Access log
/var/log/nginx/taknet-ps-error.log             # Error log
```

### Logs
```
/var/log/taknet-wifi.log                       # WiFi manager log
```

---

## 🤝 Contributing

Issues and pull requests are welcome at:
**https://github.com/cfd2474/feeder_test**

---

## 📄 License

MIT License - see LICENSE file for details

---

## 🙏 Credits

- **SDR Enthusiasts Community** - Docker containers
- **FlightRadar24** - MLAT server infrastructure
- **TAK Server Team** - Situational awareness platform
- **Tailscale** - Zero-config VPN

---

## 📞 Support

### Documentation
- [Installation Guide](INSTALL.md)
- [Upgrade Notes](UPGRADE_NOTES_v2.8.md)
- [Configuration Reference](CONFIG.md)

### Remote Access
- Default SSH user: `remote-adsb`
- Default password: `adsb2024`
- Change password after first login!

### Logs to Check First
```bash
sudo journalctl -u adsb-web -n 100
sudo journalctl -u ultrafeeder -n 100
sudo journalctl -u taknet-wifi-manager -n 100
sudo tail -f /var/log/taknet-wifi.log
```

---

**Version**: 2.8  
**Release**: January 25, 2026  
**Status**: Production Ready  
**Platform**: Raspberry Pi 3/4/5, Linux ARM64/AMD64
