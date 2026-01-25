# TAKNET-PS-ADSB-Feeder v2.8 Release Notes

## 🎉 What's New in v2.8

### Network Discovery & Access
- **mDNS Hostname**: Device now accessible at `taknet-ps.local` on your network
- **Clean URL Paths**: 
  - Web UI: `http://taknet-ps.local/web`
  - Aircraft Map: `http://taknet-ps.local/map`
- **Nginx Reverse Proxy**: Professional URL routing with automatic redirects

### WiFi Hotspot Fallback
- **Automatic Hotspot Mode**: Device creates WiFi hotspot when no network detected
- **Captive Portal**: Auto-redirects to WiFi configuration wizard
- **Network Selection**: Scan and select from available WiFi networks
- **Manual Entry**: Option to manually enter hidden network details
- **Auto-Retry Logic**: Reboots and retries connection, falls back to hotspot if failed
- **Zero Configuration**: Works out of the box without user intervention

### Hotspot Details
- **SSID**: `TAKNET-PS` (no password required)
- **IP Address**: Device accessible at `10.42.0.1` when in hotspot mode
- **Auto-Detection**: iOS and Android automatically detect captive portal

---

## 🔄 Upgrade from v2.7 to v2.8

### Fresh Install (Recommended)
```bash
curl -fsSL https://raw.githubusercontent.com/cfd2474/feeder_test/main/install/install.sh | sudo bash
```

### Manual Upgrade (Existing Installation)

#### 1. Update System Packages
```bash
sudo apt-get update
sudo apt-get install -y avahi-daemon nginx hostapd dnsmasq dhcpcd5 network-manager
```

#### 2. Configure mDNS Hostname
```bash
# Set hostname
sudo hostnamectl set-hostname taknet-ps

# Enable and start Avahi
sudo systemctl enable avahi-daemon
sudo systemctl start avahi-daemon
```

#### 3. Install Nginx Configuration
```bash
# Download nginx site config
sudo wget https://raw.githubusercontent.com/cfd2474/feeder_test/main/config/nginx-taknet-ps -O /etc/nginx/sites-available/taknet-ps

# Remove default site
sudo rm -f /etc/nginx/sites-enabled/default

# Enable new site
sudo ln -sf /etc/nginx/sites-available/taknet-ps /etc/nginx/sites-enabled/

# Test and restart nginx
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx
```

#### 4. Install WiFi Manager
```bash
# Download WiFi manager script
sudo wget https://raw.githubusercontent.com/cfd2474/feeder_test/main/scripts/wifi-manager.sh -O /opt/adsb/scripts/wifi-manager.sh
sudo chmod +x /opt/adsb/scripts/wifi-manager.sh

# Download systemd service
sudo wget https://raw.githubusercontent.com/cfd2474/feeder_test/main/systemd/taknet-wifi-manager.service -O /etc/systemd/system/taknet-wifi-manager.service

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable taknet-wifi-manager
sudo systemctl start taknet-wifi-manager
```

#### 5. Update Web Application
```bash
# Download new app.py with WiFi portal support
cd /opt/adsb/web
sudo wget https://raw.githubusercontent.com/cfd2474/feeder_test/main/web/app.py -O app.py

# Download WiFi portal template
cd templates
sudo wget https://raw.githubusercontent.com/cfd2474/feeder_test/main/web/templates/wifi-portal.html -O wifi-portal.html

# Restart web service
sudo systemctl restart adsb-web
```

#### 6. Verify Installation
```bash
# Check mDNS
ping taknet-ps.local

# Check nginx
curl http://taknet-ps.local/health

# Check WiFi manager
sudo systemctl status taknet-wifi-manager

# View WiFi logs
sudo tail -f /var/log/taknet-wifi.log
```

---

## 🌐 New URL Structure

### Before v2.8
- Web UI: `http://192.168.1.100:5000`
- Map: `http://192.168.1.100:8080`

### After v2.8
- Web UI: `http://taknet-ps.local/web`
- Map: `http://taknet-ps.local/map`
- Root: `http://taknet-ps.local` (redirects to `/web`)
- Health: `http://taknet-ps.local/health` (nginx health check)

**Note**: Old IP-based URLs still work! This is additive, not breaking.

---

## 🛜 WiFi Hotspot Behavior

### When Hotspot Activates
The device automatically creates a WiFi hotspot named `TAKNET-PS` when:
1. No WiFi connection is detected on boot
2. Existing WiFi connection is lost
3. Network connectivity check fails

### User Experience
1. **Device boots with no WiFi** → Creates `TAKNET-PS` hotspot
2. **User joins hotspot** → Device IP is `10.42.0.1`
3. **Phone/tablet auto-redirects** → WiFi configuration wizard appears
4. **User selects network** → Enters password
5. **User clicks "Connect"** → 5-second countdown displays
6. **Device reboots** → Attempts connection
7. **Success** → Normal operation resumes
8. **Failure** → Hotspot recreates, wizard available again

### Manual Access
Even without captive portal redirect, you can access:
- `http://10.42.0.1/wifi-portal` - WiFi configuration wizard
- `http://10.42.0.1/web` - Main web interface (limited functionality)

---

## 🐛 Bug Fixes from v2.7

All v2.7 fixes are retained:
- ✅ SDR configuration save (useFor property consistency)
- ✅ Wizard flow (SDR first, proper redirects)
- ✅ Tailscale installation (visible in loading screen)
- ✅ URL overflow (no config in parameters)
- ✅ Service timing (proper Docker pull waits)

---

## 📊 Technical Details

### mDNS Implementation
- **Service**: Avahi daemon
- **Protocol**: Multicast DNS (RFC 6762)
- **TLD**: `.local` domain
- **Discovery**: Zero-configuration networking

### Nginx Configuration
- **Reverse Proxy**: Routes paths to backend services
- **URL Rewriting**: Clean paths without port numbers
- **Health Checks**: `/health` endpoint for monitoring
- **WebSocket Support**: Upgrades for real-time features

### WiFi Management
- **Detection**: Ping-based connectivity checks (8.8.8.8, 1.1.1.1)
- **Hotspot**: hostapd + dnsmasq DHCP server
- **Scanning**: NetworkManager nmcli for WiFi discovery
- **Connection**: Automatic NetworkManager profile creation
- **Persistence**: Survives reboots until successful connection

### Captive Portal Detection
Supports detection endpoints for:
- **Android**: `/generate_204`, `/gen_204`
- **iOS**: `/hotspot-detect.html`
- **Windows**: `/ncsi.txt`, `/connecttest.txt`

---

## 🔍 Troubleshooting

### mDNS Not Working
```bash
# Check Avahi status
sudo systemctl status avahi-daemon

# Restart Avahi
sudo systemctl restart avahi-daemon

# Verify hostname
hostnamectl

# Test resolution
ping taknet-ps.local
```

### Nginx Errors
```bash
# Check nginx status
sudo systemctl status nginx

# Test configuration
sudo nginx -t

# View error logs
sudo tail -f /var/log/nginx/error.log
```

### WiFi Hotspot Issues
```bash
# Check WiFi manager status
sudo systemctl status taknet-wifi-manager

# View WiFi logs
sudo tail -f /var/log/taknet-wifi.log

# Check current state
cat /opt/adsb/config/.wifi-state

# Manually start hotspot
sudo /opt/adsb/scripts/wifi-manager.sh start-hotspot

# Manually stop hotspot
sudo /opt/adsb/scripts/wifi-manager.sh stop-hotspot
```

### Can't Access WiFi Portal
```bash
# Check if in hotspot mode
sudo systemctl status hostapd
sudo systemctl status dnsmasq

# Verify IP address
ip addr show wlan0

# Test web service
curl http://10.42.0.1/wifi-portal
```

---

## ⚙️ Configuration Files

### New Files in v2.8
```
/etc/nginx/sites-available/taknet-ps          # Nginx site config
/etc/systemd/system/taknet-wifi-manager.service   # WiFi manager service
/opt/adsb/scripts/wifi-manager.sh              # WiFi management script
/opt/adsb/config/.wifi-state                   # Current WiFi state
/opt/adsb/config/.wifi-credentials             # Temporary credentials file
/var/log/taknet-wifi.log                       # WiFi manager log
```

### Modified Files
```
/opt/adsb/web/app.py                           # Added WiFi portal routes
```

### New Templates
```
/opt/adsb/web/templates/wifi-portal.html       # WiFi configuration wizard
```

---

## 🎯 What's Next (v2.9 Ideas)

Potential features for future releases:
- **Bluetooth Configuration**: Configure via Bluetooth on first boot
- **Multiple WiFi Profiles**: Save and auto-switch between networks
- **VPN Failover**: Automatic Tailscale retry logic
- **Push Notifications**: Alert when device goes offline
- **OTA Updates**: Self-update mechanism
- **Backup/Restore**: Configuration backup to USB/cloud

---

## 📞 Getting Help

### Logs to Check
```bash
# WiFi manager
sudo journalctl -u taknet-wifi-manager -n 100

# Web interface
sudo journalctl -u adsb-web -n 100

# Nginx
sudo journalctl -u nginx -n 50

# Network
sudo journalctl -u NetworkManager -n 50

# Hostapd (when in hotspot mode)
sudo journalctl -u hostapd -n 50
```

### Quick Diagnostics
```bash
# All-in-one status check
sudo systemctl status taknet-wifi-manager adsb-web nginx ultrafeeder

# Network connectivity
ping -c 3 8.8.8.8

# mDNS resolution
avahi-browse -a -t

# Current WiFi state
cat /opt/adsb/config/.wifi-state
```

---

**Version**: 2.8  
**Release Date**: January 25, 2026  
**Status**: Production Ready  
**Upgrade**: Recommended for all users
