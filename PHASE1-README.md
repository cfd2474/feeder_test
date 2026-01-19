# TAK-ADSB-Feeder v2.1 - Phase 1: Hardcoded TAK Priority

## 🎯 Phase 1 Complete: TAK Server as Default Priority Feed

This update makes TAK Server the **hardcoded, always-enabled priority feed** with automatic failover support.

---

## ✨ What's New in Phase 1

### 1. **TAK Server Always Enabled**
- No user configuration needed
- Automatically feeds your TAK aggregator
- Can't be disabled (it's the whole point!)

### 2. **Primary/Fallback Connection Support**
- **Primary IP**: `100.117.34.88` (Tailscale VPN)
- **Fallback IP**: `104.225.219.254` (Public)
- **Auto mode**: Automatically selects best connection
- **Port**: `30004` (Beast protocol)

### 3. **Connection Modes**
```bash
TAK_CONNECTION_MODE=auto      # Auto-select (default, recommended)
TAK_CONNECTION_MODE=primary   # Force Tailscale IP
TAK_CONNECTION_MODE=fallback  # Force public IP
TAK_CONNECTION_MODE=monitor   # Reserved for Phase 2
```

### 4. **Smart Connection Selection**
- Tests primary IP connectivity on startup
- Falls back to public IP if primary unreachable
- Logs connection selection for debugging

---

## 📦 Updated Files

### Config Files
- **`config/env-template`** - TAK hardcoded, connection mode support
- **`scripts/config_builder.py`** - Enhanced with connectivity testing

### Web UI
- **`web/templates/setup.html`** - Shows TAK as always-enabled
- Setup wizard simplified (no TAK toggle)

---

## 🚀 Installation

### Fresh Install
```bash
wget -O - https://raw.githubusercontent.com/cfd2474/feeder_test/main/install/install.sh | sudo bash
```

### Upgrade Existing System
```bash
cd /opt/adsb
sudo wget https://raw.githubusercontent.com/cfd2474/feeder_test/main/config/env-template -O config/.env.new
sudo wget https://raw.githubusercontent.com/cfd2474/feeder_test/main/scripts/config_builder.py -O scripts/config_builder.py

# Merge your settings into .env.new, then:
sudo mv config/.env.new config/.env
sudo python3 scripts/config_builder.py
sudo systemctl restart ultrafeeder
```

---

## 🔧 Configuration

### Location (Required)
```bash
FEEDER_LAT=33.5539
FEEDER_LONG=-117.2139
FEEDER_ALT_M=304
FEEDER_TZ=America/Los_Angeles
```

### TAK Server (Hardcoded)
```bash
TAK_ENABLED=true                              # Always true
TAK_SERVER_HOST_PRIMARY=100.117.34.88        # Tailscale VPN
TAK_SERVER_HOST_FALLBACK=104.225.219.254     # Public IP
TAK_SERVER_PORT=30004                         # Beast port
TAK_CONNECTION_MODE=auto                      # Auto-select
```

### Optional Aggregators
```bash
FR24_ENABLED=false
FR24_SHARING_KEY=

ADSBX_ENABLED=false
ADSBX_UUID=
```

---

## 📊 How It Works

### Startup Sequence
1. **Config builder runs** (`config_builder.py`)
2. **Tests primary IP** (100.117.34.88:30004)
3. **Selects connection**:
   - ✅ Primary reachable → Use Tailscale
   - ⚠️ Primary unreachable → Use fallback public IP
   - ℹ️ Neither reachable → Try primary anyway
4. **Builds ULTRAFEEDER_CONFIG** with TAK as first feed
5. **Starts ultrafeeder** with TAK priority

### Connection Output Examples
```bash
✓ TAK Server: 100.117.34.88:30004 (primary-auto)
⚠ TAK Server: Primary unreachable, using fallback: 104.225.219.254
ℹ TAK: Forced to primary: 100.117.34.88
```

---

## 🔍 Verification

### Check Config
```bash
sudo python3 /opt/adsb/scripts/config_builder.py
```

Should show:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TAK-ADSB-Feeder Config Builder v2.1
Building ULTRAFEEDER_CONFIG...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ TAK Server: 100.117.34.88:30004 (primary-auto)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Configuration built: 1 active feeds
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Check Container Logs
```bash
sudo docker logs ultrafeeder | grep "100.117\|104.225"
```

Should show:
```
BeastReduce TCP output: Connection established: 100.117.34.88 port 30004
```

### Check Web UI
Open: `http://your-pi:5000`
- Dashboard should show "TAK Server" as active feed
- Setup wizard shows TAK as always-enabled

---

## 🛠️ Troubleshooting

### TAK Server not connecting

**Check connectivity:**
```bash
nc -zv 100.117.34.88 30004
nc -zv 104.225.219.254 30004
```

**Force fallback:**
```bash
sudo nano /opt/adsb/config/.env
# Change: TAK_CONNECTION_MODE=fallback
sudo python3 /opt/adsb/scripts/config_builder.py
sudo systemctl restart ultrafeeder
```

### Web UI shows wrong info

**Restart web service:**
```bash
sudo systemctl restart adsb-web
```

---

## 🔮 Future Phases

### Phase 2: Active Connection Monitoring (Coming Soon)
- Continuous Tailscale connectivity monitoring
- Automatic failover on connection loss
- Automatic failback when Tailscale restored
- Integration of your `adsb_connection_monitor.sh`

### Phase 3: Auto-Update System (Planned)
- Check GitHub for config updates
- Pull new TAK IPs automatically
- Version-controlled updates
- Rollback support

---

## 📝 Notes

- **TAK Server cannot be disabled** - It's hardcoded as the primary purpose
- **Connection testing has 2-second timeout** - Won't delay startup significantly
- **Failover is one-time on startup** - Phase 2 adds continuous monitoring
- **Web UI is informational only** - TAK config not editable by users

---

## ✅ Success Criteria

Phase 1 is successful when:
- [x] TAK Server feeds automatically without user config
- [x] Primary/Fallback IPs work correctly
- [x] Auto-selection chooses best available connection
- [x] Web UI reflects TAK as always-enabled
- [x] Existing optional aggregators still work

---

**Version**: 2.1.0  
**Status**: Production Ready  
**Next**: Phase 2 - Connection Monitoring
