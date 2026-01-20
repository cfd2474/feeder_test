# SDR Configuration Feature

## Overview

New comprehensive SDR device detection and configuration system integrated into setup wizard and settings.

## Setup Wizard Changes

### New Page 1: SDR Configuration

**Location:** `/setup/sdr` (setup-sdr.html)

**Features:**
- **Auto-Detection:** Automatically detects all connected RTL-SDR devices
- **Interactive Table:** Shows device type, serial, configuration status
- **Click-to-Configure:** Click any row to open configuration modal
- **Real-Time Updates:** Table updates immediately after configuration

**Detection Display:**
```
┌─────────────────────────────────────────────────────┐
│ 🔍 Detecting SDR devices...                          │
│ Please wait while we scan for connected receivers   │
└─────────────────────────────────────────────────────┘
```

**Device Table:**
```
Type    | Serial | Use For  | Gain      | Bias Tee
--------|--------|----------|-----------|----------
RTLSDR  | 1      | 1090 MHz | autogain  | -
RTLSDR  | 2      | 978 MHz  | 49.6      | ✓ Enabled
```

### Configuration Modal

When user clicks a device row:

```
┌────────────────────────────────────────┐
│ Configure SDR Device                    │
│ Device: RTLSDR - Serial: 00000001      │
│                                         │
│ Use For *                               │
│ [1090 MHz (ADS-B)          ▼]          │
│ Select the frequency this device will   │
│ monitor                                 │
│                                         │
│ Gain                                    │
│ [autogain                  ]            │
│ Enter a value between 0 and 50, or     │
│ use 'autogain' (recommended)           │
│                                         │
│ [✓] Enable Bias Tee                    │
│ Only enable if you have an LNA that    │
│ requires bias tee power                │
│                                         │
│ [💾 Save Configuration] [Cancel]        │
└────────────────────────────────────────┘
```

**Fields:**
- **Use For:** Dropdown with 1090 MHz or 978 MHz
- **Gain:** Text input, accepts 0-50 or "autogain"
- **Bias Tee:** Checkbox

### Page Flow

```
Old Flow:
/setup (Location) → Step 2 (Tailscale) → Step 3 (Aggregators)

New Flow:
/setup → /setup/sdr (SDR Config) → /setup/location → Step 2 → Step 3
```

---

## API Endpoints

### GET /api/sdr/detect

Detects connected RTL-SDR devices.

**Response:**
```json
{
  "success": true,
  "devices": [
    {
      "index": 0,
      "type": "rtlsdr",
      "manufacturer": "Realtek",
      "product": "RTL2832U",
      "serial": "00000001",
      "useFor": "1090",
      "gain": "autogain",
      "biastee": false
    }
  ]
}
```

**Detection Method:**
```bash
rtl_test -t
```

Parses output for device information.

### POST /api/sdr/configure

Saves SDR configuration.

**Request:**
```json
{
  "devices": [
    {
      "index": 0,
      "useFor": "1090",
      "gain": "autogain",
      "biastee": false
    }
  ]
}
```

**Response:**
```json
{
  "success": true
}
```

**Storage Format (.env):**
```ini
SDR_0=1090,autogain,false
SDR_1=978,49.6,true
READSB_DEVICE=0
READSB_GAIN=autogain
```

---

## Settings Page Integration

### SDR Configuration Section

**To be added to settings.html:**

```html
<!-- SDR Configuration Section -->
<div class="card">
    <h3>SDR Devices</h3>
    
    <button class="btn btn-secondary" onclick="detectSDRDevices()">
        🔍 Detect Devices
    </button>
    
    <div id="sdrDevicesTable" style="margin-top: 20px;">
        <!-- Same table as setup wizard -->
    </div>
</div>
```

**Behavior:**
- Shows same detection and configuration interface as setup wizard
- Users can reconfigure devices at any time
- Changes require service restart to apply

---

## Configuration Details

### Gain Settings

**Options:**
- `autogain` - Automatic gain adjustment (recommended)
- `0` - Minimum gain
- `49.6` - Maximum gain (typical)
- `0-50` - Any value in between

**Validation:**
- Must be "autogain" or a number 0-50
- Alert shown if invalid

### Bias Tee

**Purpose:** Provides power to external LNA

**Warning:** Only enable if you have an LNA that requires it!

**Technical:**
- Sets `READSB_ENABLE_BIASTEE=ON` in config
- Passes to ultrafeeder container

### Frequency Options

**1090 MHz (ADS-B):**
- Standard commercial aircraft tracking
- Most common use case
- Mode S / ADS-B

**978 MHz (UAT):**
- US-specific
- General aviation
- Weather information
- Requires separate container/config

---

## Error Handling

### No Devices Found

Display:
```
⚠️ No SDR Devices Detected

No RTL-SDR devices were found connected to this system.

Please check:
• RTL-SDR dongle is plugged in
• USB connection is secure
• RTL-SDR drivers are installed

[🔄 Retry Detection] [Skip for Now →]
```

**Actions:**
- **Retry:** Re-runs detection
- **Skip:** Continues to location config (can configure SDR later)

### Detection Timeout

If `rtl_test` times out (>5 seconds):
```json
{
  "success": false,
  "error": "Detection timed out"
}
```

### Missing Drivers

If `rtl_test` not found:
```json
{
  "success": false,
  "error": "rtl_test not found"
}
```

---

## Multiple Device Support

System supports multiple SDR devices:

**Example Configuration:**
```
Device 0: 1090 MHz → Primary ADS-B receiver
Device 1: 978 MHz → UAT receiver
```

**Environment:**
```ini
SDR_0=1090,autogain,false
SDR_1=978,49.6,true
READSB_DEVICE=0
```

**Future Enhancement:**
Could run multiple ultrafeeder instances for multi-frequency monitoring.

---

## Visual Design

### Table Styling

**Unconfigured Row:**
```
Type    | Serial | Use For
RTLSDR  | 1      | [Not Configured] ← Gray badge
```

**Configured Row (1090):**
```
Type    | Serial | Use For
RTLSDR  | 1      | [1090 MHz] ← Blue badge, green background
```

**Configured Row (978):**
```
Type    | Serial | Use For
RTLSDR  | 2      | [978 MHz] ← Yellow badge, green background
```

### Hover Effect

Rows highlight on hover to indicate clickability.

### Badge Colors

- **Unconfigured:** Gray (#f3f4f6)
- **1090 MHz:** Blue (#dbeafe / #1e40af)
- **978 MHz:** Yellow (#fef3c7 / #92400e)

---

## Installation

### Add to Existing System

```bash
cd /opt/adsb/web

# Download new files
sudo wget https://raw.githubusercontent.com/cfd2474/feeder_test/main/web/templates/setup-sdr.html -O templates/setup-sdr.html
sudo wget https://raw.githubusercontent.com/cfd2474/feeder_test/main/web/app.py -O app.py

# Restart web service
sudo systemctl restart adsb-web
```

### Test

```bash
# Test SDR detection
curl http://localhost:5000/api/sdr/detect

# Should return device list
```

---

## Dependencies

### Required:
- `rtl_test` - RTL-SDR command-line tool
- `python3` - Flask backend
- RTL-SDR drivers installed

### Check Installation:
```bash
rtl_test -t
```

Should show connected devices.

---

## Future Enhancements

### Planned Features:
1. **Antenna Configuration** - Cable loss, antenna type
2. **PPM Correction** - Frequency correction settings
3. **Filter Configuration** - Blacklisting/whitelisting
4. **Performance Metrics** - Signal strength, message rate
5. **Multi-Frequency Support** - Run both 1090 and 978 simultaneously
6. **Device Health Monitoring** - Temperature, errors

### Settings Page SDR Section:
- Full device reconfiguration
- Performance metrics display
- Quick enable/disable without full config

---

## Troubleshooting

### Device Not Detected

**Check USB:**
```bash
lsusb | grep RTL
```

**Check Drivers:**
```bash
rtl_test -t
```

**Check Permissions:**
```bash
sudo usermod -aG plugdev $USER
```

### Configuration Not Applying

**Rebuild Config:**
```bash
cd /opt/adsb
sudo python3 scripts/config_builder.py
```

**Restart Services:**
```bash
sudo systemctl restart ultrafeeder
```

### Gain Issues

**Too High:** Causes overload, reduced performance
**Too Low:** Weak signals, reduced range
**Recommended:** Start with `autogain`, adjust if needed

---

## Summary

**New Features:**
✅ SDR device auto-detection
✅ Interactive configuration table
✅ Click-to-configure interface
✅ Gain and bias tee settings
✅ Multiple device support
✅ Integration with setup wizard
✅ API endpoints for detection/config

**User Experience:**
✅ Visual device status
✅ One-click configuration
✅ Clear validation messages
✅ Skip option if no devices

**Technical:**
✅ Stores config in .env
✅ Passes to ultrafeeder
✅ Supports multiple frequencies
✅ Validates input

Ready for deployment! 🚀
