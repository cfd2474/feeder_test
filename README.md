# TAK-ADSB-Feeder v2.1

**adsb.im clone with hardcoded TAK Server priority**

## 🎯 What Makes This Different

- ✅ **TAK Server always enabled** - No configuration needed
- ✅ **Automatic failover** - Primary (Tailscale) → Fallback (Public IP)
- ✅ **Web setup wizard** - Configure location and optional feeds
- ✅ **Production-ready** - Based on adsb.im architecture

## 🚀 Quick Start

```bash
wget -O - https://raw.githubusercontent.com/cfd2474/feeder_test/main/install/install.sh | sudo bash
```

Open browser: **http://your-pi-ip:5000**

## ✨ Features

### TAK Server (Hardcoded Priority)
- Always feeds your TAK aggregator
- Primary IP: 100.117.34.88 (Tailscale)
- Fallback IP: 104.225.219.254 (Public)
- Auto-selects best connection
- Can't be disabled

### Optional Public Aggregators
- FlightRadar24
- ADS-B Exchange
- Airplanes.Live
- RadarBox
- PlaneFinder
- OpenSky Network

## 📖 Documentation

- [Phase 1 Details](PHASE1-README.md) - TAK hardcoded implementation
- [Installation Guide](#installation)
- [Configuration](#configuration)

## 🏗️ Architecture

```
RTL-SDR → readsb → Ultrafeeder
                      ├─→ TAK Server (Priority, Always On)
                      ├─→ FlightRadar24 (Optional)
                      ├─→ ADS-B Exchange (Optional)
                      └─→ Other feeds (Optional)
```

## 📝 Configuration

Only location is required:

```bash
FEEDER_LAT=33.5539
FEEDER_LONG=-117.2139
FEEDER_ALT_M=304
```

TAK Server is pre-configured and always active.

## 🌐 Access Points

- Setup/Dashboard: `http://your-pi:5000`
- Live Map: `http://your-pi:8080`

## 🔮 Roadmap

- **Phase 1** ✅ - TAK Server hardcoded with failover
- **Phase 2** 🚧 - Active connection monitoring
- **Phase 3** 📋 - Auto-update system

## 📜 License

MIT
