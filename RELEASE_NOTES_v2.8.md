# TAKNET-PS v2.8 Release Notes
## Major Network Features Update

---

## 🌟 NEW FEATURES

### 1. ✅ mDNS Hostname (taknet-ps.local)

**No more IP addresses!**

Your device is now accessible via:
- **http://taknet-ps.local/web** - Web UI
- **http://taknet-ps.local/map** - Live aircraft map
- **http://taknet-ps.local/fr24** - FlightRadar24 interface

**How it works:**
- Uses Avahi mDNS daemon
- Broadcasts hostname on local network
- Works on:
  * ✅ Linux (built-in)
  * ✅ macOS (Bonjour)
  * ✅ iOS/Android (native support)
  * ✅ Windows (install Bonjour Print Services)

**Benefits:**
- ✅ No need to find IP address
- ✅ Survives DHCP changes
- ✅ Easy to remember
- ✅ Professional appearance

---

### 2. ✅ Nginx Reverse Proxy

**Clean URLs with path mapping!**

Old way:
```
http://192.168.1.50:5000  → Web UI
http://192.168.1.50:8080  → Map
http://192.168.1.50:8754  → FR24
```

New way:
```
http://taknet-ps.local/web  → Web UI
http://taknet-ps.local/map  → Map
http://taknet-ps.local/fr24 → FR24
```

**How it works:**
- Nginx listens on port 80
- Proxies requests to backend services
- Root URL redirects to /web

**Benefits:**
- ✅ No port numbers needed
- ✅ Standard HTTP port (80)
- ✅ Path-based routing
- ✅ Can add SSL later (HTTPS)

**Direct port access still works:**
- http://taknet-ps.local:5000
- http://taknet-ps.local:8080
- http://taknet-ps.local:8754

---

### 3. ✅ WiFi Hotspot with Captive Portal

**Automatic fallback when no network!**

#### How It Works

**Scenario: Fresh Device, No WiFi**

1. Device boots
2. Network monitor checks connectivity
3. No network found → **Start hotspot**
4. WiFi hotspot appears: **TAKNET-PS** (no password)
5. User connects to TAKNET-PS
6. **Captive portal opens automatically**
7. Portal shows WiFi wizard

**Wizard Flow:**

```
┌─────────────────────────────┐
│   🛩️ TAKNET-PS              │
│   WiFi Configuration Wizard │
├─────────────────────────────┤
│                             │
│  [🔍 Scan for Networks]     │
│                             │
│  📶📶📶 Home-WiFi     🔒     │
│  📶📶 Guest-Network   🔓     │
│  📶📶📶📶 Office-5G     🔒    │
│                             │
│  Network: Home-WiFi         │
│  Password: [________]       │
│                             │
│  [🔗 Connect to Network]    │
└─────────────────────────────┘
```

**After clicking "Connect":**

```
┌─────────────────────────────┐
│   ✓ Configuration Saved!    │
│                             │
│  Device will reboot in:     │
│                             │
│         5                   │
│                             │
│  Attempting to connect to:  │
│      Home-WiFi              │
│                             │
│  If connection fails,       │
│  hotspot will restart.      │
└─────────────────────────────┘
```

**After reboot:**

1. Device attempts to connect to configured WiFi
2. **Success?** → Normal operation, hotspot stays off
3. **Failure?** → Hotspot restarts automatically

**Retry Logic:**
```
Boot → Try WiFi → Failed? → Start Hotspot → User configures → Reboot → Repeat
```

#### Features

**Captive Portal:**
- ✅ Auto-opens when joining TAKNET-PS network
- ✅ Beautiful responsive design
- ✅ Network scanner with signal strength
- ✅ Shows secured/open networks
- ✅ Manual SSID entry option
- ✅ 5-second countdown before reboot

**Hotspot Specs:**
- **SSID:** TAKNET-PS
- **Password:** None (open network)
- **IP Range:** 192.168.4.1 - 192.168.4.20
- **Portal IP:** 192.168.4.1:8888
- **DHCP:** 24-hour leases

**Network Monitor:**
- Checks connectivity every 30 seconds
- Pings 8.8.8.8 and 1.1.1.1
- 30-second grace period before hotspot activation
- Automatically stops hotspot when network restored

---

## 🔧 INSTALLATION

### New Installation

**One Command:**
```bash
curl -fsSL https://raw.githubusercontent.com/cfd2474/feeder_test/main/install/install.sh | sudo bash
```

**Then run network configuration:**
```bash
cd /opt/adsb
sudo ./configure-network.sh
```

### Existing Installation Update

**If you have v2.7 installed:**

```bash
# Download network configuration script
cd /opt/adsb
sudo wget https://raw.githubusercontent.com/cfd2474/feeder_test/main/configure-network.sh
sudo chmod +x configure-network.sh

# Run configuration
sudo ./configure-network.sh

# Reboot to activate all features
sudo reboot
```

---

## 📱 USER EXPERIENCE

### Scenario 1: Home Network

```
User: *Plugs in Raspberry Pi*
Device: *Boots, connects to home WiFi*
User: Opens browser → http://taknet-ps.local/web
Result: ✅ Configuration wizard appears
```

### Scenario 2: New Location (No Known WiFi)

```
User: *Takes device to friend's house*
Device: *Boots, no known network*
Device: *Starts hotspot "TAKNET-PS" after 30 seconds*
User's Phone: *Sees "TAKNET-PS" network*
User: *Connects to TAKNET-PS*
Phone: *Captive portal opens automatically*
User: *Selects friend's WiFi, enters password*
Portal: *5 second countdown*
Device: *Reboots*
Device: *Connects to friend's WiFi*
User: Opens browser → http://taknet-ps.local/web
Result: ✅ Dashboard appears
```

### Scenario 3: Bad WiFi Password

```
User: *Configures WiFi in captive portal*
User: *Types wrong password*
User: *Clicks Connect*
Device: *Reboots*
Device: *Tries to connect... fails*
Device: *Starts hotspot again after 30 seconds*
User: *Sees TAKNET-PS reappear*
User: *Connects again, fixes password*
Result: ✅ Device connects successfully
```

---

## 🛠️ TECHNICAL DETAILS

### Services Added

**network-check.service:**
- Monitors connectivity continuously
- Starts/stops hotspot as needed
- Manages wpa_supplicant state

**captive-portal.service:**
- Flask web app on port 8888
- Serves WiFi configuration wizard
- Handles network scanning
- Writes wpa_supplicant configuration

**Nginx:**
- Reverse proxy on port 80
- Routes /web → 5000
- Routes /map → 8080
- Routes /fr24 → 8754

**Avahi-daemon:**
- mDNS responder
- Broadcasts taknet-ps.local
- Handles .local domain queries

### Files Added

```
/opt/adsb/
├── configure-network.sh          # Setup script
└── captive-portal/
    ├── portal.py                 # Flask app
    └── templates/
        └── portal.html           # Wizard UI

/etc/nginx/
└── sites-available/
    └── taknet-ps                 # Reverse proxy config

/etc/avahi/
└── avahi-daemon.conf             # mDNS config

/usr/local/bin/
└── check-network.sh              # Network monitor script

/etc/systemd/system/
├── network-check.service
├── captive-portal.service
└── taknet-ps-reboot.service
```

### Network Flow

**Normal Operation:**
```
Internet → Router → Device (wlan0 or eth0)
                    ↓
                 Services running
                    ↓
        http://taknet-ps.local/web
```

**Hotspot Mode:**
```
Phone/Laptop → TAKNET-PS WiFi → Device (wlan0 = AP)
                                  ↓
                            Captive Portal
                                  ↓
                     http://192.168.4.1:8888
```

---

## 🧪 TESTING

### Test 1: mDNS Resolution

```bash
# From another device on same network:
ping taknet-ps.local

# Should respond with device IP
```

### Test 2: Nginx Paths

```bash
# Try each URL:
http://taknet-ps.local/web     # Should show Web UI
http://taknet-ps.local/map     # Should show tar1090
http://taknet-ps.local/fr24    # Should show FR24
```

### Test 3: Hotspot Activation

```bash
# On device:
sudo systemctl stop wpa_supplicant

# Wait 30 seconds
# Look for "TAKNET-PS" WiFi network on phone

# Connect to TAKNET-PS
# Portal should auto-open

# If doesn't auto-open, manually visit:
http://192.168.4.1:8888
```

### Test 4: WiFi Configuration

1. Connect to TAKNET-PS hotspot
2. Portal opens automatically
3. Click "Scan for Networks"
4. Select your WiFi network
5. Enter password
6. Click "Connect"
7. Watch 5-second countdown
8. Device reboots
9. Check if connected:
```bash
iwconfig wlan0 | grep ESSID
# Should show your network name
```

---

## 🆘 TROUBLESHOOTING

### mDNS Not Working

**Symptom:** Cannot access taknet-ps.local

**Fix:**
```bash
# Check Avahi status
sudo systemctl status avahi-daemon

# Restart Avahi
sudo systemctl restart avahi-daemon

# Check hostname
hostname
# Should show: taknet-ps

# Test from device
avahi-browse -a

# Windows users: Install Bonjour Print Services
```

---

### Nginx Not Routing

**Symptom:** taknet-ps.local/web shows error

**Fix:**
```bash
# Check Nginx status
sudo systemctl status nginx

# Test config
sudo nginx -t

# Check if services are running
curl http://localhost:5000  # Web UI
curl http://localhost:8080  # Map

# Restart Nginx
sudo systemctl restart nginx
```

---

### Hotspot Not Starting

**Symptom:** No TAKNET-PS network appears

**Fix:**
```bash
# Check network monitor
sudo systemctl status network-check

# Check logs
sudo journalctl -u network-check -n 50

# Manually start hotspot
sudo /usr/local/bin/check-network.sh &

# Check WiFi interface
iwconfig wlan0
# Should show Mode:Master when hotspot active

# Check hostapd
sudo systemctl status hostapd
```

---

### Captive Portal Not Opening

**Symptom:** Connected to TAKNET-PS but no portal

**Fix:**
```bash
# Check captive portal service
sudo systemctl status captive-portal

# Check if listening
sudo netstat -tulpn | grep 8888

# Manually visit portal
http://192.168.4.1:8888

# Check iptables rules
sudo iptables -t nat -L -n -v
# Should show DNAT rules for port 80/443
```

---

### WiFi Configuration Not Saving

**Symptom:** Reboot loops back to hotspot

**Fix:**
```bash
# Check wpa_supplicant config
sudo cat /etc/wpa_supplicant/wpa_supplicant.conf

# Manual test connection
sudo wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant/wpa_supplicant.conf

# Check for errors
sudo journalctl -u wpa_supplicant -n 50

# Verify password is correct
# Reconfigure via captive portal
```

---

## 📋 CONFIGURATION FILES

### /etc/nginx/sites-available/taknet-ps

```nginx
server {
    listen 80 default_server;
    server_name taknet-ps.local _;

    location = / {
        return 301 http://$host/web;
    }

    location /web/ {
        proxy_pass http://127.0.0.1:5000/;
        # ... proxy headers ...
    }

    location /map/ {
        proxy_pass http://127.0.0.1:8080/;
    }

    location /fr24/ {
        proxy_pass http://127.0.0.1:8754/;
    }
}
```

### /etc/hostapd/hostapd.conf

```
interface=wlan0
driver=nl80211
ssid=TAKNET-PS
hw_mode=g
channel=7
wmm_enabled=0
auth_algs=1
wpa=0
```

### /etc/avahi/avahi-daemon.conf

```
[server]
host-name=taknet-ps
domain-name=local
use-ipv4=yes
use-ipv6=no

[publish]
publish-addresses=yes
publish-workstation=yes
```

---

## 🔐 SECURITY NOTES

### Open WiFi Hotspot

**Why no password?**
- Intended for initial setup only
- Temporary until configured
- Captive portal is for configuration, not Internet access
- No sensitive data exposed

**Best practices:**
- Configure WiFi as soon as possible
- Hotspot auto-stops when network connected
- Change default 'remote' user password
- Use Tailscale for remote access

### Nginx Security

**Current setup:**
- HTTP only (port 80)
- Local network only
- No authentication on proxy

**Future enhancements:**
- Add HTTPS (Let's Encrypt)
- HTTP authentication
- Rate limiting
- Fail2ban integration

---

## 📝 CHANGELOG

### v2.8 (Current)
- ✅ Added mDNS support (taknet-ps.local)
- ✅ Added Nginx reverse proxy
- ✅ Added WiFi hotspot with captive portal
- ✅ Added network connectivity monitor
- ✅ Added automatic fallback behavior

### v2.7
- Fixed SDR configuration save bug

### v2.6
- Fixed wizard flow
- Fixed Tailscale in loading screen
- Fixed placeholder text

### v2.5
- Fixed loading screen timing

### v2.4
- Fixed URL overflow

### v2.3
- Added SDR wizard
- Added vnstat
- Added remote user

---

## ✨ SUMMARY

**v2.8 brings professional networking features!**

**Before v2.8:**
```
1. Find IP address
2. Remember port numbers
3. No WiFi recovery
```

**After v2.8:**
```
1. Visit taknet-ps.local/web
2. No ports to remember
3. Auto-recovery with hotspot
```

**Perfect for:**
- ✅ Portable deployments
- ✅ Multiple locations
- ✅ Non-technical users
- ✅ Field operations
- ✅ Demo setups

**One command installs everything!** 🚀

```bash
curl -fsSL https://raw.githubusercontent.com/cfd2474/feeder_test/main/install/install.sh | sudo bash
cd /opt/adsb && sudo ./configure-network.sh
```
