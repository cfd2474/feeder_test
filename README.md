# TAKNET-PS-ADSB-Feeder v2.1

**Tactical Awareness Kit Network for Enhanced Tracking – Public Safety**

## Features

- 🎯 **TAKNET-PS Server Priority Feed** - Hardcoded as primary aggregator
- 📡 **Beast & MLAT Feeds** - Dual data streams for maximum accuracy  
- 🔐 **Tailscale VPN** - Secure encrypted connection with auto-failover
- 🌐 **Web UI** - Complete setup wizard and settings management
- 🔄 **Auto-Configuration** - Missing settings automatically repaired
- ⚠️ **Disable Protection** - Confirmation modals prevent accidental disabling

## Quick Install

```bash
curl -sSL https://raw.githubusercontent.com/cfd2474/feeder_test/main/install/install.sh | bash
```

## What's TAKNET-PS?

TAKNET-PS (Tactical Awareness Kit Network for Enhanced Tracking – Public Safety) is an aircraft tracking aggregation network designed for:
- Emergency response coordination
- Public safety operations
- Enhanced situational awareness
- Multilateration tracking accuracy

While compatible with TAK (Team Awareness Kit), TAKNET-PS provides broader capabilities for public safety and tracking applications beyond traditional tactical operations.

## Configuration

TAKNET-PS settings are **hardcoded and auto-configured**:

```ini
TAKNET_PS_ENABLED=true
TAKNET_PS_SERVER_HOST_PRIMARY=100.117.34.88
TAKNET_PS_SERVER_HOST_FALLBACK=104.225.219.254
TAKNET_PS_SERVER_PORT=30004
TAKNET_PS_MLAT_ENABLED=true
TAKNET_PS_MLAT_PORT=30105
```

Missing settings are **automatically repaired** on every config rebuild!
