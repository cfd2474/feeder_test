# TAKNET-PS ADS-B Feeder

**Version:** 2.41.0  
**Status:** Production Ready ✅

Complete ADS-B aircraft tracking system with web-based configuration, multiple feed support, and professional dashboard. Built for Raspberry Pi and compatible single-board computers.

---

## 🚀 Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/install/install.sh | sudo bash
```

Then open browser to: **http://taknet-ps.local**

**Time:** 10-15 minutes  
**Includes:** Docker images pre-downloaded, setup wizard ~30 seconds

---

## 📡 Features

- **Live Aircraft Tracking** - 1090 MHz ADS-B reception via RTL-SDR
- **Web Dashboard** - Complete configuration through browser
- **Multi-Feed Support** - Share data with multiple networks simultaneously
- **MLAT** - Multilateration for aircraft without GPS
- **Zero Config** - Automated setup wizard handles everything

**Supported Networks:**
- TAKNET-PS (default)
- FlightAware
- FlightRadar24
- adsb.fi
- adsb.lol
- airplanes.live

---

## 📋 Requirements

- **Hardware:** Raspberry Pi 3/4/5 or compatible SBC
- **SDR:** RTL-SDR USB dongle (FlightAware Pro Stick or generic)
- **Antenna:** 1090 MHz antenna
- **Internet:** Ethernet or WiFi
- **OS:** Raspberry Pi OS, Ubuntu 20.04+

---

## 🎯 Setup

1. **Install:**
   ```bash
   curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/install/install.sh | sudo bash
   ```

2. **Access:** http://taknet-ps.local

3. **Configure:** Complete setup wizard
   - Enter coordinates
   - Specify antenna height
   - Select feeds to enable

4. **View Map:** http://taknet-ps.local:8080

**Done!** Aircraft appear within minutes.

---

## 📚 Documentation

- **[CHANGELOG-v2.41.0.md](CHANGELOG-v2.41.0.md)** - Latest changes
- **[Troubleshooting](#troubleshooting)** - Common issues
- **[FlightAware Setup](#flightaware-mlat--location)** - MLAT & location verification

---

## 🔧 Troubleshooting

### No Aircraft?

```bash
# Check SDR connected
lsusb | grep RTL

# Check containers running  
docker ps

# View logs
docker logs ultrafeeder --tail 50
```

**Common fixes:**
- Unplug/replug SDR
- Restart: `sudo systemctl restart ultrafeeder`
- Check antenna connected
- Verify coordinates correct

### Web Interface Not Loading?

```bash
# Check service
systemctl status adsb-web.service

# Restart
sudo systemctl restart adsb-web.service
```

---

## 📡 FlightAware MLAT & Location

**MLAT Timing:**
- MLAT takes up to **10 minutes** to show "live" status
- This is normal - be patient!

**Location Verification (Required for MLAT):**
1. Go to https://flightaware.com/adsb/stats/user/
2. Click **gear icon ⚙️** next to feeder name
3. Enter exact coordinates (same as TAKNET-PS)
4. Save changes

**Why?** Incorrect location = MLAT positioning errors!

---

## 🔄 Updates

```bash
# Update Docker images
cd /opt/adsb/config
sudo docker compose pull
sudo systemctl restart ultrafeeder
```

---

## 📊 Performance

**Typical (Raspberry Pi 4):**
- CPU: 5-15%
- RAM: 300-500 MB
- Network: 5-10 Mbps upload

**Aircraft Tracked:**
- Urban: 50-150 aircraft
- Suburban: 20-80 aircraft  
- Rural: 5-30 aircraft
- Good elevation: 200-400+ aircraft

---

## 📞 Support

- **Issues:** GitHub Issues
- **Questions:** GitHub Discussions
- **Latest:** [CHANGELOG-v2.41.0.md](CHANGELOG-v2.41.0.md)

---

## 🙏 Credits

Built with:
- [sdr-enthusiasts](https://github.com/sdr-enthusiasts) Docker containers
- [readsb](https://github.com/wiedehopf/readsb) decoder
- [tar1090](https://github.com/wiedehopf/tar1090) web interface
- Flask + Docker

---

## 📄 License

Educational and hobbyist use. Docker images used under MIT License.

---

**Built with ❤️ for the ADS-B community**
