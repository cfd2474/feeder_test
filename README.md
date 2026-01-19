# TAK-ADSB-Feeder

Production-ready ADS-B feeder system using Docker containers for multiple aggregators.

Based on [adsb.im](https://github.com/dirkhh/adsb-feeder-image) production patterns, designed specifically for TAK Server integration.

## 🚀 Quick Start

```bash
wget -O - https://raw.githubusercontent.com/cfd2474/feeder_test/main/install/install-tak-adsb-feeder.sh | sudo bash
```

See [QUICKSTART.md](QUICKSTART.md) for detailed instructions.

## ✨ Features

- **Docker-based aggregators** - FR24, ADSBX, Airplanes.Live, RadarBox, PlaneFinder, OpenSky
- **Dynamic compose selection** - Enable/disable via environment variables  
- **Smart caching** - 10-second container/status cache
- **Real feed monitoring** - Beast + MLAT connection tracking
- **Flask REST API** - Complete management interface
- **Production patterns** - Based on adsb.im's battle-tested code

## 📖 Documentation

- [Quick Start](QUICKSTART.md)
- [Production Implementation](docs/PRODUCTION-IMPLEMENTATION.md)

## 🏗️ Architecture

```
Native: readsb (RTL-SDR) → port 30005 Beast

Docker Aggregators:
  ├─ FR24, ADSBX, Airplanes.Live
  ├─ RadarBox, PlaneFinder, OpenSky
  └─ All connect via host.docker.internal:30005
```

## 🔧 Configuration

```bash
sudo nano /opt/TAK_ADSB/config/.env

# Location
FEEDER_LAT=33.5539
FEEDER_LONG=-117.2139  
FEEDER_ALT_M=304

# Enable feeds
AF_IS_FR24_ENABLED=true
FEEDER_FR24_SHARING_KEY=your_key
```

## 📦 What's Included

- Installer script with dependency management
- Production Docker Compose configurations
- Flask web API (Python 3)
- Smart caching and status monitoring
- Systemd service for auto-start
- Complete aggregator templates

## 🤝 Contributing

Issues and PRs welcome!

## 🙏 Acknowledgments

- [adsb.im](https://github.com/dirkhh/adsb-feeder-image) - Production patterns
- [sdr-enthusiasts](https://github.com/sdr-enthusiasts) - Docker images

Built with ❤️ for the ADS-B community
