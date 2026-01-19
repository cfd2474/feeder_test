# Quick Start Guide

## One-Line Install

```bash
wget -O - https://raw.githubusercontent.com/cfd2474/feeder_test/main/install/install-tak-adsb-feeder.sh | sudo bash
```

## Manual Install

```bash
# Clone repository
git clone https://github.com/cfd2474/feeder_test.git
cd feeder_test

# Run installer
chmod +x install/install-tak-adsb-feeder.sh
sudo ./install/install-tak-adsb-feeder.sh
```

## Configure

```bash
# Edit configuration
sudo nano /opt/TAK_ADSB/config/.env

# Set location
FEEDER_LAT=33.5539
FEEDER_LONG=-117.2139
FEEDER_ALT_M=304
FEEDER_TZ=America/Los_Angeles
MLAT_SITE_NAME=YourFeederName

# Enable aggregators
AF_IS_FR24_ENABLED=true
AF_IS_ADSBX_ENABLED=true

# Add credentials
FEEDER_FR24_SHARING_KEY=your_key
FEEDER_ADSBX_UUID=your_uuid
```

## Start Services

```bash
sudo systemctl start tak-adsb-docker
```

## Check Status

```bash
# Docker containers
docker ps

# Container logs
docker logs fr24

# API status
curl http://localhost:5000/api/aggregators/status
```

## Common Commands

```bash
# Start
sudo systemctl start tak-adsb-docker

# Stop
sudo systemctl stop tak-adsb-docker

# Restart
sudo systemctl restart tak-adsb-docker

# Update images
sudo /opt/TAK_ADSB/scripts/docker-compose-adsb pull
sudo systemctl restart tak-adsb-docker
```

## Troubleshooting

### Containers won't start

```bash
docker logs <container_name>
cat /opt/TAK_ADSB/config/.env
```

### Python packages missing

```bash
sudo apt-get install -y python3-flask python3-psutil
```

### Permission denied

```bash
sudo chown -R $USER:$USER /opt/TAK_ADSB
```
