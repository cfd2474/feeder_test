# TAKNET-PS ADSB Feeder

**Complete ADS-B Aircraft Tracking System for Raspberry Pi**

[![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-red)](https://www.raspberrypi.org/)
[![OS](https://img.shields.io/badge/OS-Raspberry%20Pi%20OS%20Bookworm-blue)](https://www.raspberrypi.com/software/)
[![Version](https://img.shields.io/badge/version-2.8.4-orange)](CHANGELOG.md)

Feed aircraft data to TAKNET-PS aggregator while optionally sharing with public services like FlightRadar24, ADS-B Exchange, and more.

---

## ✨ Features

### Core Features
- 🛩️ **Ultrafeeder** - Advanced ADS-B receiver and aggregator
- 📡 **RTL-SDR Support** - Auto-detection and configuration
- 🗺️ **Live Map** - Real-time aircraft tracking (tar1090)
- 🌐 **Web Configuration** - Complete setup wizard
- 📊 **Network Monitoring** - 30-day bandwidth tracking (vnstat)

### Network Features (v2.8)
- 🏠 **mDNS Hostname** - Access via `taknet-ps.local`
- 🔀 **Nginx Reverse Proxy** - Clean URLs (`/web`, `/map`, `/fr24`)
- 📶 **WiFi Hotspot** - Automatic fallback with captive portal
- 🔌 **Auto-Recovery** - Restarts hotspot if network fails

### Feed Destinations
- 🎯 **TAKNET-PS** - Primary aggregator (hardcoded, always enabled)
- ✈️ **FlightRadar24** - Dedicated container with MLAT
- 🌍 **ADS-B Exchange** - Public aggregator
- 🛫 **Airplanes.Live** - Community aggregator

### Security & Access
- 🔐 **Tailscale VPN** - Secure connection to TAKNET-PS network
- 👤 **Remote User** - Limited sudo access for remote management
- 🔒 **SSH Restrictions** - Optional Tailscale-only access

---

## 🚀 Quick Start

### Prerequisites

**Hardware:**
- Raspberry Pi 3/4/5
- RTL-SDR USB dongle
- MicroSD card (16GB+)
- Stable power supply (2.5A+)

**Software:**
- **Raspberry Pi OS Lite 64-bit (Bookworm)**
- Fresh installation recommended

### Installation

```bash
curl -fsSL https://raw.githubusercontent.com/cfd2474/feeder_test/main/install/install.sh | sudo bash
cd /opt/adsb
sudo bash configure-network.sh
sudo reboot
```

After reboot: **http://taknet-ps.local/web**

---

## 📋 Documentation

- **[Installation Guide](docs/INSTALLATION.md)** - Detailed setup
- **[Configuration Guide](docs/CONFIGURATION.md)** - All settings
- **[Network Guide](docs/NETWORK.md)** - mDNS & hotspot
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues
- **[Changelog](CHANGELOG.md)** - Version history

---

## 🌐 Access URLs

```
http://taknet-ps.local/web   → Web UI
http://taknet-ps.local/map   → Aircraft Map  
http://taknet-ps.local/fr24  → FlightRadar24 Stats
```

---

## 📶 WiFi Hotspot

No network? No problem!

1. Device starts hotspot: **TAKNET-PS** (no password)
2. Connect with phone/laptop
3. Captive portal opens automatically
4. Select WiFi & enter password
5. Device reboots and connects
6. If fails: Hotspot restarts

---

## 📧 Support

- **Issues:** [GitHub Issues](https://github.com/cfd2474/feeder_test/issues)

---

**Made for Raspberry Pi OS Bookworm 64-bit**

Version 2.8.4 | January 26, 2026
