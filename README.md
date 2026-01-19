# TAK-ADSB-Feeder

adsb.im clone with TAK Server integration built-in.

## Quick Start

```bash
wget -O - https://raw.githubusercontent.com/cfd2474/feeder_test/main/install/install.sh | sudo bash
```

## Configure

```bash
sudo nano /opt/adsb/config/.env
```

Set location:
- `FEEDER_LAT=33.5539`
- `FEEDER_LONG=-117.2139`
- `FEEDER_ALT_M=304`
- `FEEDER_TZ=America/Los_Angeles`

Enable TAK Server:
- `TAK_ENABLED=true`
- `TAK_SERVER_HOST=your-tak-ip`

Enable aggregators:
- `FR24_ENABLED=true`
- `FR24_SHARING_KEY=your_key`

## Start

```bash
sudo systemctl start ultrafeeder
```

## Access

Map: `http://your-pi:8080`

## Architecture

Single ultrafeeder container includes:
- readsb (RTL-SDR)
- tar1090 (map)
- TAK Server feed
- All aggregators

## Commands

```bash
sudo systemctl start ultrafeeder
sudo systemctl stop ultrafeeder
docker logs ultrafeeder
```
