# TAKNET-PS Complete Changelog

## v2.41.3 - WiFi UX Improvements (2026-02-09)

### Bug Fixes
- **Manual WiFi entry now works for remote setup** - Saves configuration without requiring network in range
- Fixed error: "No network with SSID found" when pre-configuring for remote sites

### UX Enhancements
- **Custom password modal** - Beautiful styled modal replaces ugly browser prompt
- **Real-time status feedback** - Spinner and clear messages during connection/save
- **Auto-dismiss notifications** - Success/error messages auto-close (no extra clicks)
- **Keyboard support** - Enter key works throughout WiFi forms
- **Password visibility toggle** - Show/hide password in custom modal

### Technical Changes
- Added `saveOnly` parameter to `/api/wifi/add` endpoint
- Manual entry uses `nmcli connection add` (save only)
- Scan selection uses `nmcli dev wifi connect` (immediate connection)
- Added WiFi password modal and status modal with spinner animation

---

## v2.41.2 - WiFi Configuration (2026-02-09)

### New Features
- **WiFi Configuration in Settings** - Complete WiFi management interface
- **Network Scanning** - Scan for available WiFi networks with signal strength
- **Manual SSID Entry** - Pre-configure networks for remote deployment
- **Saved Networks Management** - View and remove configured WiFi networks

---

## v2.41.1 - UI Improvements (2026-02-08)

### New Features
- "Enable All" button for accountless feeds
- Popup feedback for FlightAware setup
- Popup feedback for FR24 setup

---

## v2.41.0 - Installation & Documentation (2026-02-08)

### New Features
- Docker image pre-download during GitHub installation
- FlightAware MLAT timing notice
- FlightAware location verification

---

For complete version history, see individual CHANGELOG files.
