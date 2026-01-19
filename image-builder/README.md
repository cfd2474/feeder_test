# Image Builder

**Status**: Coming Soon

This directory will contain scripts to build a custom Raspberry Pi image with TAK-ADSB-Feeder pre-installed, similar to adsb.im's approach.

## Planned Features

- Pre-configured system image
- All dependencies pre-installed
- Ready to configure and run
- Flash and go approach

## Current Approach

For now, use the installer script on a fresh Raspberry Pi OS installation:

```bash
wget -O - https://raw.githubusercontent.com/cfd2474/feeder_test/main/install/install-tak-adsb-feeder.sh | sudo bash
```

## Future Implementation

Will use pi-gen or similar tool to create custom images.
