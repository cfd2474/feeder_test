# TAKNET-PS-ADSB-Feeder v2.3 - Clean Install Guide

## ✅ All Features Included in Clean Install

When you run the installer, you will get **ALL** of these features automatically:

### 📡 Core Features
- ✅ Ultrafeeder with TAK Server integration
- ✅ Web-based setup wizard
- ✅ Dashboard with live updates
- ✅ Settings management
- ✅ FlightRadar24 dedicated container
- ✅ Auto-start on boot

### 🆕 New Features (v2.3)
- ✅ **SDR Configuration Wizard** - Auto-detect and configure RTL-SDR devices
- ✅ **vnstat Network Monitoring** - 30-day traffic statistics
- ✅ **Remote SSH User** - Dedicated `remote` user with limited sudo
- ✅ **RTL-SDR Tools** - Pre-installed drivers

---

## 🚀 One-Line Installation

```bash
curl -fsSL https://raw.githubusercontent.com/cfd2474/feeder_test/main/install/install.sh | sudo bash
```

### What Gets Installed:

**System Packages:**
- Docker + Docker Compose
- Python 3 + Flask
- rtl-sdr (SDR drivers and tools)
- vnstat (network monitoring)
- wget, curl

**ADSB Components:**
- Ultrafeeder container
- FR24 container
- TAK integration
- Web UI (Flask app)

**User Accounts:**
- `remote` user created
- Password: `adsb`
- Limited sudo privileges

**Services:**
- `ultrafeeder.service` (Docker containers)
- `adsb-web.service` (Web UI)
- `vnstat.service` (Network monitoring)

**Files & Directories:**
```
/opt/adsb/
├── config/
│   ├── docker-compose.yml
│   ├── .env (environment variables)
│   └── ultrafeeder/
├── scripts/
│   └── config_builder.py
├── web/
│   ├── app.py
│   ├── templates/
│   │   ├── setup-sdr.html (NEW!)
│   │   ├── setup.html
│   │   ├── dashboard.html
│   │   ├── settings.html
│   │   └── loading.html
│   └── static/
└── configure-ssh-tailscale.sh (NEW!)

/etc/sudoers.d/
└── remote-adsb (NEW!)
```

---

## 📋 Installation Process

### Step 1: Run Installer

```bash
curl -fsSL https://raw.githubusercontent.com/cfd2474/feeder_test/main/install/install.sh | sudo bash
```

**What happens:**
1. ✅ Checks for root privileges
2. ✅ Installs Docker
3. ✅ Installs Python + Flask
4. ✅ Installs rtl-sdr tools
5. ✅ Installs vnstat
6. ✅ Configures vnstat (30-day retention)
7. ✅ Creates `remote` user with sudo
8. ✅ Creates directories
9. ✅ Downloads all files from GitHub
10. ✅ Creates systemd services
11. ✅ Starts web UI
12. ✅ Shows completion message

**Time:** ~5-10 minutes

---

### Step 2: Access Web UI

After installation completes, you'll see:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Installation complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌐 Open your browser and go to:

   http://192.168.1.100:5000

   Complete the setup wizard to configure your feeder.
```

Navigate to the URL shown.

---

### Step 3: Setup Wizard

The wizard has **4 steps**:

#### **Step 1: SDR Configuration** (NEW!)

```
┌────────────────────────────────────────┐
│ 📡 SDR Configuration                    │
│ Configure Software Defined Radio        │
│ receivers                                │
│                                          │
│ 🔍 Detecting SDR devices...             │
└────────────────────────────────────────┘
```

**What happens:**
1. Auto-detects connected RTL-SDR devices
2. Shows table with detected devices
3. Click any device to configure
4. Set frequency (1090 MHz or 978 MHz)
5. Set gain (autogain recommended)
6. Enable/disable bias tee
7. Click "Apply Settings & Continue"

**If no SDR detected:**
- Shows warning message
- Option to retry
- Option to skip (can configure later in Settings)

---

#### **Step 2: Location**

Enter your receiver coordinates:
- Latitude
- Longitude
- Altitude (meters)
- Timezone
- Feeder name

---

#### **Step 3: Tailscale VPN**

Configure Tailscale for TAKNET-PS:
- Enter Tailscale auth key
- System connects to VPN
- Gets assigned Tailscale IP

---

#### **Step 4: Aggregators**

Configure additional feed destinations:
- ADS-B Exchange
- FlightAware
- FlightRadar24
- etc.

---

### Step 4: Services Start

After completing wizard:
1. Configuration saved to `.env`
2. Config builder generates ultrafeeder config
3. Docker containers start
4. Redirects to dashboard
5. ✅ System is running!

---

## 🔒 Optional: Configure Tailscale-Only SSH

**After completing setup wizard**, you can restrict the `remote` user to Tailscale network only:

```bash
cd /opt/adsb
sudo ./configure-ssh-tailscale.sh
```

**What it does:**
1. Detects your Tailscale subnet
2. Backs up SSH config
3. Adds Match block for `remote` user
4. Restricts SSH to Tailscale IPs only
5. Restarts SSH service

**Result:**
- `remote` can SSH from Tailscale: ✅
- `remote` can SSH from internet: ❌
- Other users unaffected

---

## 📊 What You Get

### Web UI Access

**Main Interface:**
- http://your-ip:5000

**Pages:**
- `/` - Redirects to dashboard or setup
- `/setup/sdr` - SDR configuration
- `/setup` - Location setup
- `/dashboard` - Live status
- `/settings` - All settings

**Live Map:**
- http://your-ip:8080 (tar1090)

### Remote User Access

**SSH Login:**
```bash
ssh remote@your-ip
# Password: adsb
```

**Allowed Commands:**
```bash
sudo systemctl restart ultrafeeder
sudo systemctl restart adsb-web
sudo docker ps
sudo docker logs ultrafeeder
sudo journalctl -u ultrafeeder
sudo vnstat
```

### Network Monitoring

**vnstat Commands:**
```bash
vnstat              # Current stats
vnstat -d           # Daily (30 days)
vnstat -m           # Monthly
vnstat -l           # Live monitoring
vnstat --json       # JSON output
```

### SDR Configuration

**Locations:**
1. Setup Wizard - `/setup/sdr`
2. Settings Page - SDR Devices section

**Both locations:**
- Auto-detect devices
- Interactive configuration
- Click-to-configure interface
- Settings persist in `.env`

---

## 🧪 Post-Install Testing

### Test 1: Web UI

```bash
# Check service
sudo systemctl status adsb-web

# Should show: Active (running)

# Access in browser
http://your-ip:5000
```

### Test 2: SDR Detection

```bash
# Test rtl_test
rtl_test -t

# Should show: Found X device(s)

# Check saved config
cat /opt/adsb/config/.env | grep SDR_

# Should show: SDR_0=1090,autogain,false
```

### Test 3: Docker Containers

```bash
# Check containers
sudo docker ps

# Should show:
# - ultrafeeder
# - fr24
```

### Test 4: Remote User

```bash
# Test local
su - remote
# Password: adsb

# Test sudo
sudo systemctl status ultrafeeder
sudo docker ps

exit
```

### Test 5: vnstat

```bash
# Check status
sudo systemctl status vnstat

# View stats (may be empty initially)
vnstat

# View config
cat /etc/vnstat.conf | grep -E "MonthRotate|DayGraphDays"
# Should show:
# MonthRotate 1
# DayGraphDays 30
```

---

## 🔧 Configuration Files

### Environment File
**Location:** `/opt/adsb/config/.env`

**Contains:**
```ini
# Location
FEEDER_LAT=33.5539
FEEDER_LONG=-117.2139
FEEDER_ALT_M=304
TZ=America/Los_Angeles

# SDR (NEW!)
SDR_0=1090,autogain,false
READSB_DEVICE=0
READSB_GAIN=autogain

# Tailscale
TAILSCALE_AUTH_KEY=tskey-xxx

# Feeds
ULTRAFEEDER_CONFIG=adsb,feed.adsb.one,30004,beast_reduce_plus_out
```

### Sudoers File
**Location:** `/etc/sudoers.d/remote-adsb`

**Permissions:** `0440` (read-only)

**Contents:** Limited sudo commands for `remote` user

### vnstat Config
**Location:** `/etc/vnstat.conf`

**Modified settings:**
```ini
MonthRotate 1      # 1 month retention
DayGraphDays 30    # 30 days of daily data
```

---

## 📁 Directory Structure

```
/opt/adsb/
├── config/
│   ├── docker-compose.yml        # Container definitions
│   ├── .env                       # Environment variables (YOUR CONFIG)
│   └── ultrafeeder/              # Generated config files
├── scripts/
│   └── config_builder.py         # Generates ultrafeeder config from .env
├── web/
│   ├── app.py                     # Flask web application
│   ├── templates/
│   │   ├── setup-sdr.html        # SDR wizard (Step 1)
│   │   ├── setup.html            # Location wizard (Step 2)
│   │   ├── dashboard.html        # Status dashboard
│   │   ├── settings.html         # Settings page
│   │   └── loading.html          # Loading screen
│   └── static/
│       ├── css/style.css         # Styles
│       └── js/*.js               # JavaScript
└── configure-ssh-tailscale.sh    # SSH restriction script
```

---

## 🚨 Important Notes

### Default Credentials
- Remote user: `remote`
- Password: `adsb`
- **Change if needed:** `sudo passwd remote`

### Tailscale SSH Restriction
- **Optional** - only run if you want Tailscale-only access
- Script: `/opt/adsb/configure-ssh-tailscale.sh`
- Run AFTER Tailscale is configured
- Creates SSH config backup automatically

### SDR Configuration
- Automatically loads saved config on detection
- Persists across reboots
- Stored in `/opt/adsb/config/.env`

### vnstat Data
- Takes a few minutes to collect initial data
- Data stored in `/var/lib/vnstat/`
- Automatically rotates old data (30 days)

---

## 🆘 Troubleshooting

### Web UI won't start

```bash
# Check logs
sudo journalctl -u adsb-web -n 50

# Restart
sudo systemctl restart adsb-web
```

### SDR not detected

```bash
# Check USB
lsusb | grep RTL

# Test manually
rtl_test -t

# Check permissions
sudo usermod -aG plugdev $USER
# Logout and login
```

### Docker containers won't start

```bash
# Check Docker
sudo systemctl status docker

# Check logs
sudo journalctl -u ultrafeeder -n 50

# Manual start
cd /opt/adsb/config
sudo docker compose up -d
```

### Remote user can't sudo

```bash
# Validate sudoers
sudo visudo -c

# Check file exists
ls -l /etc/sudoers.d/remote-adsb

# Should show: -r--r----- 1 root root
```

---

## ✅ Summary

**Clean install includes:**
- ✅ RTL-SDR tools (rtl_test, etc.)
- ✅ SDR configuration wizard
- ✅ vnstat (30-day monitoring)
- ✅ Remote user with limited sudo
- ✅ All previous features
- ✅ Optional Tailscale-only SSH

**Just run:**
```bash
curl -fsSL https://raw.githubusercontent.com/cfd2474/feeder_test/main/install/install.sh | sudo bash
```

**Then:**
1. Open web browser
2. Complete 4-step wizard
3. (Optional) Configure Tailscale SSH
4. ✅ Done!

Everything works out of the box! 🚀
