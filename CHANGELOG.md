# Changelog

All notable changes to TAKNET-PS ADSB Feeder.

---

## [2.8.4] - 2026-01-26

### Fixed - CRITICAL CONNECTION STATE MACHINE
- **Bug #4: WiFi Retry Logic Missing** (CRITICAL)
  - After captive portal WiFi config and reboot, device would immediately start hotspot again
  - wpa_supplicant was killed before WiFi could connect
  - No distinction between "no config" vs "connecting" states
  - Fixed: Implemented intelligent 3-state connection detection:
    - State 0: Connected (internet working)
    - State 1: WiFi configured, connecting (retry for 5 minutes)
    - State 2: No WiFi config (start hotspot immediately)
- **Improved network-monitor.sh State Machine**
  - Added 5-minute grace period for WiFi connection after reboot
  - Prevents premature hotspot activation while WiFi is connecting
  - State persistence across checks with status file
  - Detailed logging to `/var/log/network-monitor.log`
  - Can detect Ethernet connection while in hotspot mode and auto-stop hotspot

### Changed
- check-connection.sh now returns 3 different exit codes for state detection
- network-monitor.sh implements proper state machine with retry timers
- stop-hotspot.sh properly masks/unmasks services to prevent conflicts
- Enhanced logging with timestamps and state transitions

### Testing Required
- ✅ Ethernet disconnect → hotspot starts
- ✅ Captive portal WiFi config → reboot → WiFi connects (not hotspot)
- ✅ Invalid WiFi password → 5 min timeout → hotspot restarts
- ✅ Ethernet plugged in while hotspot active → hotspot stops

### Platform
- **Tested on:** Raspberry Pi OS Lite 64-bit (Bookworm)
- **Compatible:** Raspberry Pi 3/4/5

---

## [2.8.3] - 2026-01-26

### Fixed - CRITICAL CAPTIVE PORTAL BUGS
- **Bug #1: Wrong Port in iptables Rules** (CRITICAL)
  - iptables redirecting to port 5001 instead of 8888
  - Captive portal would never load on client devices
  - Fixed: Changed all iptables rules in `start-hotspot.sh` to use port 8888
- **Bug #2: Missing iptables Monitoring**
  - network-monitor.sh had no iptables rule checking/re-adding
  - If rules were lost, they would never be restored
  - Fixed: Added `ensure_iptables()` function with 60-second monitoring loop
- **Bug #3: Incomplete DNS Wildcards**
  - Missing specific captive portal detection domains
  - Some devices might not auto-trigger captive portal
  - Fixed: Added all platform-specific captive portal domains (Android, iOS, Windows, Firefox)

### Changed
- network-monitor.sh now logs iptables re-adds to `/var/log/network-monitor.log`
- dnsmasq.conf includes DHCP options and domain filtering for better captive portal detection

### Testing
- Confirmed captive portal now loads immediately on Android devices
- iptables rules persist and auto-restore if missing

### Platform
- **Tested on:** Raspberry Pi OS Lite 64-bit (Bookworm)
- **Compatible:** Raspberry Pi 3/4/5

---

## [2.8] - 2026-01-25

### Added
- **mDNS Support** - Access device via `taknet-ps.local` hostname
- **Nginx Reverse Proxy** - Clean URL paths (`/web`, `/map`, `/fr24`)
- **WiFi Hotspot** - Automatic fallback when no network detected
  - SSID: TAKNET-PS (no password)
  - Auto-activates after 30 seconds without network
  - Auto-deactivates when network restored
- **Captive Portal** - Beautiful WiFi configuration wizard
  - Network scanner with signal strength
  - Manual SSID entry
  - 5-second countdown before reboot
  - Automatic retry on connection failure
- **Network Monitoring Service** - Continuous connectivity checking
- **Avahi mDNS Daemon** - Broadcasts hostname on network

### Changed
- Installer now includes network configuration
- Root URL redirects to `/web`
- Port 80 now default (Nginx proxy)

### Fixed
- Installer here-document terminator (AVAHIEOF)

### Platform
- **Tested on:** Raspberry Pi OS Lite 64-bit (Bookworm)
- **Compatible:** Raspberry Pi 3/4/5

---

## [2.7] - 2026-01-24

### Fixed
- **Critical:** SDR configuration save bug
  - Property name mismatch (`use_for` vs `useFor`)
  - Configuration now saves to table properly
  - Can proceed past SDR wizard step

### Changed
- Consistent property naming in JavaScript (`useFor` everywhere)

### Files Modified
- `web/templates/setup-sdr.html` (line 367)
- `web/templates/settings.html` (line 798)

---

## [2.6] - 2026-01-24

### Fixed
- Wizard now starts with SDR configuration (not skipped)
- Tailscale installation moved to loading screen (not footer)
- Location fields use placeholders (not pre-filled with defaults)
- Feeder name not pre-filled on fresh install

### Changed
- `env-template`: Removed `READSB_DEVICE=0` default
- Improved home route redirect logic
- setup.js: Removed Tailscale install (moved to loading.html)
- setup.html: Added Jinja conditionals for default values

### Files Modified
- `config/env-template`
- `web/app.py`
- `web/static/js/setup.js`
- `web/templates/loading.html`
- `web/templates/setup.html`

---

## [2.5] - 2026-01-24

### Fixed
- Loading screen timing issues
- False "service failed to start" errors
- Tailscale progress now visible in loading window

### Changed
- Increased Docker pull wait time (2s → 15s)
- Added informational messages about timing
- Better error handling in loading screen

### Added
- Tailscale progress step in loading screen
- Status messages for Docker image download
- Note about full synchronization time

### Files Modified
- `web/templates/loading.html`

---

## [2.4] - 2026-01-23

### Fixed
- Setup wizard redirect URL overflow
- Loading screen not appearing after "Save & Start"

### Changed
- Config saved to backend before redirect
- Loading page reads config from API (not URL params)
- Clean redirect to `/loading` without parameters

### Files Modified
- `web/static/js/setup.js`
- `web/templates/loading.html`

---

## [2.3] - 2026-01-22

### Added
- SDR configuration wizard (`/setup/sdr`)
- Auto-detection of RTL-SDR devices
- Interactive device configuration
- vnstat network monitoring (30-day retention)
- Remote user (`remote` / `adsb`)
- Limited sudo privileges for remote user
- Optional SSH restriction script

### Files Added
- `web/templates/setup-sdr.html`
- `configure-ssh-tailscale.sh`

### Changed
- Wizard flow now includes SDR setup
- Home route checks SDR configuration first

---

## [2.2] - 2026-01-20

### Added
- FlightRadar24 dedicated container
- MLAT support for FR24
- Auto-start services on boot

### Changed
- Separate FR24 from main ultrafeeder
- Improved service dependencies

---

## [2.1] - 2026-01-18

### Added
- Initial web UI release
- Flask-based configuration interface
- Setup wizard (Location, Tailscale, Aggregators)
- Dashboard with service status
- Settings page
- Loading screen with progress
- systemd services

### Features
- Docker Compose setup
- Ultrafeeder container
- TAKNET-PS integration (primary + fallback)
- MLAT support
- Tailscale VPN support
- Multiple aggregator support

### Files
- Complete web application
- Docker configuration
- Config builder script
- Systemd services

---

## [2.0] - 2026-01-15

### Added
- Docker-based deployment
- Automated installer
- Environment-based configuration
- TAKNET-PS aggregator integration

---

## [1.0] - 2025-12-01

### Initial Release
- Basic ADS-B feeder
- Manual configuration
- Single aggregator support

---

## Version Format

Format: `[MAJOR.MINOR]` - `YYYY-MM-DD`

- **MAJOR**: Breaking changes or major features
- **MINOR**: New features, bug fixes, improvements

### Categories
- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security-related changes
- **Platform**: Target platform information

---

**Current Version:** 2.8.4
**Last Updated:** January 26, 2026
**Maintained by:** cfd2474
