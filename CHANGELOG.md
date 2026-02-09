# TAKNET-PS Complete Changelog

## v2.41.1 - UI Improvements (2026-02-08)

### New Features
- **"Enable All" button** for accountless feeds - enable all 5 feeds with one click
- **Popup feedback for FlightAware setup** - shows spinner during generation, success confirmation
- **Popup feedback for FR24 setup** - shows registration/configuration progress with auto-dismiss

### Technical Changes
- Enhanced `web/templates/feeds.html` with `enableAllAccountless()` function
- Modified `web/templates/feeds-account-required.html` to use status modals for both FR24 and FlightAware
- Consistent popup UX across all feed operations

---

## v2.41.0 - Installation & Documentation (2026-02-08)

### New Features
- **Docker image pre-download** during GitHub installation - setup wizard now takes 30-40 seconds instead of 5-10 minutes
- **FlightAware MLAT timing notice** - warns users that MLAT takes up to 10 minutes to show "live"
- **FlightAware location verification** - step-by-step instructions for verifying coordinates on flightaware.com

### Technical Changes
- Modified `install/install.sh` to pre-download Docker images in parallel
- Added informational section to `web/templates/feeds-account-required.html`
- Updated to v2.41.0

---

## v2.40.6 - FlightRadar24 Timeout & Performance (2026-02-08)

### Bug Fixes
- Increased FR24 registration timeout from 60s to 180s for slow connections
- Fixed streaming response handling to show real-time progress
- Added detailed performance logging with `verbose_timing` parameter

### Technical Changes
- Modified registration timeout in `web/app.py`
- Enhanced subprocess streaming in FR24 registration endpoint

---

For complete version history, see individual CHANGELOG files.
