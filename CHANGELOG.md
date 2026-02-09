# TAKNET-PS Complete Changelog

## v2.41.2 - WiFi Configuration (2026-02-09)

### New Features
- **WiFi Configuration in Settings** - Complete WiFi management interface
- **Network Scanning** - Scan for available WiFi networks with signal strength
- **Manual SSID Entry** - Pre-configure networks for remote deployment
- **Saved Networks Management** - View and remove configured WiFi networks
- **Signal Strength Indicators** - Visual indicators for network quality

### API Endpoints
- `GET /api/wifi/scan` - Scan for available networks
- `GET /api/wifi/saved` - List configured networks
- `POST /api/wifi/add` - Add new WiFi configuration
- `POST /api/wifi/remove` - Remove WiFi configuration

### Technical Changes
- Enhanced `web/templates/settings.html` with WiFi configuration section
- Added WiFi management JavaScript functions
- Added WiFi API endpoints to `web/app.py`
- NetworkManager (nmcli) support with wpa_supplicant fallback

---

## v2.41.1 - UI Improvements (2026-02-08)

### New Features
- **"Enable All" button** for accountless feeds
- **Popup feedback for FlightAware setup**
- **Popup feedback for FR24 setup**

---

## v2.41.0 - Installation & Documentation (2026-02-08)

### New Features
- **Docker image pre-download** during GitHub installation
- **FlightAware MLAT timing notice**
- **FlightAware location verification**

---

For complete version history, see individual CHANGELOG files.
