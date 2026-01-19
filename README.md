# TAK-ADSB-Feeder

adsb.im clone with TAK Server integration + Web UI

## 🚀 Quick Start

```bash
wget -O - https://raw.githubusercontent.com/cfd2474/feeder_test/main/install/install.sh | sudo bash
```

Then open your browser: **http://your-pi-ip:5000**

## ✨ Features

- ✅ **Web Setup Wizard** - Configure via browser
- ✅ **Live Dashboard** - View feed status
- ✅ **TAK Server Integration** - Built-in support
- ✅ **Multiple Aggregators** - FR24, ADSBX, Airplanes.Live, etc.
- ✅ **One-Line Install** - Flash and go
- ✅ **Ultrafeeder Architecture** - Production-ready

## 📖 Usage

### First Time Setup

1. Flash Raspberry Pi OS Lite (Bookworm) to SD card
2. Boot and SSH in
3. Run installer (one command above)
4. Open browser to http://your-pi-ip:5000
5. Complete 3-step setup wizard
6. Done! 🎉

### Access Points

- **Setup/Dashboard**: http://your-pi-ip:5000
- **Live Map**: http://your-pi-ip:8080
- **Settings**: http://your-pi-ip:5000/settings

### Manual Commands

```bash
# Start/stop services
sudo systemctl start ultrafeeder
sudo systemctl stop ultrafeeder
sudo systemctl restart ultrafeeder

# View logs
sudo docker logs ultrafeeder

# Web UI
sudo systemctl status adsb-web
```

## 🏗️ Architecture

Single ultrafeeder container includes:
- readsb (RTL-SDR receiver)
- tar1090 (live map)
- TAK Server feed (priority)
- All aggregator feeds

## 📝 Configuration

Edit `/opt/adsb/config/.env` or use the web interface.

Required settings:
- `FEEDER_LAT` - Your latitude
- `FEEDER_LONG` - Your longitude  
- `FEEDER_ALT_M` - Altitude in meters
- `FEEDER_TZ` - Timezone

Optional aggregators:
- `TAK_ENABLED=true` + `TAK_SERVER_HOST`
- `FR24_ENABLED=true` + `FR24_SHARING_KEY`
- `ADSBX_ENABLED=true` + `ADSBX_UUID`

## 🐛 Troubleshooting

### Container won't start
```bash
docker logs ultrafeeder
cat /opt/adsb/config/.env
```

### Web UI not accessible
```bash
sudo systemctl status adsb-web
sudo systemctl restart adsb-web
```

### No aircraft showing
- Check RTL-SDR is plugged in: `lsusb | grep RTL`
- Check antenna connection
- Wait 5-10 minutes for initial sync

## 🤝 Contributing

Issues and PRs welcome!

## 📜 License

MIT

## 🙏 Credits

- [adsb.im](https://github.com/dirkhh/adsb-feeder-image) - Inspiration
- [sdr-enthusiasts](https://github.com/sdr-enthusiasts) - Docker images
