# TAKNET-PS v2.8.4 - CRITICAL CONNECTION STATE MACHINE FIX

**Release Date:** January 26, 2026  
**Priority:** CRITICAL - All v2.8.0-2.8.3 users MUST upgrade  
**Platform:** Raspberry Pi OS Lite 64-bit (Bookworm)

---

## 🚨 CRITICAL BUG FIX

This release fixes **two showstopper bugs**: one that prevented WiFi configuration from working, and one that caused false "service failed" errors.

### Bug #4: Missing WiFi Retry Logic (CRITICAL)

**Symptom:** After configuring WiFi in captive portal and rebooting, device immediately starts hotspot again instead of connecting to WiFi

**Root Cause:** 
- network-monitor.sh waited 60 seconds after boot, then checked connectivity
- If WiFi wasn't connected within 60 seconds, it immediately:
  - Killed wpa_supplicant (stopping WiFi connection attempt)
  - Started hotspot mode
  - Entered infinite hotspot loop
- No distinction between "no WiFi configured" vs "WiFi connecting"
- No retry mechanism for WiFi connections

**Impact:** 
- WiFi captive portal configuration completely non-functional
- Device stuck in hotspot mode forever
- **Makes the entire captive portal feature useless**

**The Flow That Was Broken:**
```
1. User configures WiFi in captive portal ✅
2. Device reboots ✅
3. wpa_supplicant starts connecting to WiFi ✅
4. network-monitor.sh wakes up after 60s ⏰
5. WiFi not connected yet (needs 90 seconds) ❌
6. network-monitor KILLS wpa_supplicant ☠️
7. Starts hotspot mode 📶
8. WiFi connection never completes ❌
9. STUCK IN HOTSPOT FOREVER 🔁
```

### Bug #5: Ultrafeeder Premature Start Detection

**Symptom:** Web UI status page shows "ultrafeeder failed to start" even though container starts successfully moments later

**Root Cause:**
- systemd service `Type=oneshot` with `docker compose up -d` 
- The `-d` flag returns immediately (detached mode)
- systemd reports "started" before Docker finishes pulling image
- Web UI checks status too early, sees container doesn't exist yet
- Reports false failure even though container starts 10-30 seconds later

**Impact:**
- Confusing error messages for users
- Makes fresh installs look broken
- Requires manual refresh to see actual status

**The Flow That Was Broken:**
```
1. User clicks "Save & Start" ✅
2. systemd runs: docker compose up -d
3. Command returns immediately (detached) ✅
4. systemd reports: "Service started" ✅
5. Web UI checks status 2 seconds later ⏰
6. Docker still pulling image... ❌
7. Container doesn't exist yet ❌
8. Web UI shows: "FAILED TO START" ☠️
9. 20 seconds later, container actually starts ✅
10. User sees error, gets confused 😕
```

---

## ✅ THE FIX: Wait for Container Running State

### ExecStartPost Wait Loop

Added intelligent wait loop to ultrafeeder.service:

```bash
ExecStartPost=/bin/bash -c '\
    for i in {1..60}; do \
        if docker inspect ultrafeeder >/dev/null 2>&1; then \
            if [ "$(docker inspect -f {{.State.Running}} ultrafeeder)" = "true" ]; then \
                echo "Ultrafeeder container is running"; \
                exit 0; \
            fi; \
        fi; \
        echo "Waiting for container... attempt $i/60"; \
        sleep 2; \
    done'
```

**How it works:**
1. `docker compose up -d` starts the pull/create/start process
2. ExecStartPost runs immediately after
3. Checks every 2 seconds for container existence
4. Verifies container is in "Running" state (not just "Created")
5. Only reports "started" when container is actually running
6. Timeout: 2 minutes (60 attempts × 2 seconds)
7. Works regardless of network speed or image size

---

## 📋 WHAT'S FIXED

### Core Fixes
- ✅ WiFi connections now have 5 minutes to establish (Bug #4)
- ✅ wpa_supplicant no longer killed prematurely (Bug #4)
- ✅ Proper state detection (no config vs connecting vs connected) (Bug #4)
- ✅ Ultrafeeder wait loop prevents false start failures (Bug #5)
- ✅ systemd only reports "started" when container is actually running (Bug #5)

### Additional Improvements
- ✅ Detailed logging with timestamps and state transitions

**check-connection.sh** now returns different exit codes:

- **Exit 0:** Connected to internet (all good, keep monitoring)
- **Exit 1:** WiFi configured but not connected yet (RETRY, don't kill it!)
- **Exit 2:** No WiFi configured (safe to start hotspot)

### WiFi Retry Logic

When WiFi is configured but not connected:
- Starts 5-minute retry timer
- Checks every 10 seconds (not killing wpa_supplicant)
- Logs progress: "WiFi connecting... 30s elapsed (timeout: 300s)"
- Only starts hotspot after 5 minutes of failed attempts

### State Persistence

State stored in `/var/run/network-monitor-state`:
- `checking` - Initial state
- `connected` - Internet working
- `wifi_retry` - WiFi connecting, retry in progress
- `hotspot` - Hotspot mode active

### Intelligent Transitions

```
Boot → Wait 60s → Check State
                    ↓
        ┌───────────┼───────────┐
        ↓           ↓           ↓
   Connected   WiFi Config   No Config
        ↓           ↓           ↓
   Monitor     Retry 5min   Hotspot
        ↓           ↓           ↓
   Every 30s   Every 10s   Monitor+iptables
        ↓           ↓           ↓
        └──────> Success <─────┘
```

---

## 📋 WHAT'S FIXED

### Core Fix
- ✅ WiFi connections now have 5 minutes to establish
- ✅ wpa_supplicant no longer killed prematurely
- ✅ Proper state detection (no config vs connecting vs connected)
- ✅ Detailed logging with timestamps and state transitions

### Additional Improvements
- ✅ Ethernet detection while in hotspot mode (auto-stops hotspot)
- ✅ State file tracks connection status across checks
- ✅ Enhanced stop-hotspot.sh properly masks/unmasks services
- ✅ Better logging format with timestamps

---

## 🧪 EXPECTED BEHAVIOR (NOW WORKING)

### Scenario 1: Fresh Install (No WiFi Config)
```
1. Boot → No internet detected
2. After 60s → No WiFi config found
3. Immediately start hotspot ✅
4. User configures WiFi in portal
5. Device reboots
```

### Scenario 2: After WiFi Configuration (THE FIX)
```
1. Boot → wpa_supplicant starts connecting
2. After 60s → WiFi config detected, not connected yet
3. Start 5-minute retry timer ✅
4. Check every 10s (keeping wpa_supplicant alive) ✅
5. WiFi connects at ~90 seconds ✅
6. Internet detected, continue monitoring ✅
```

### Scenario 3: WiFi Password Wrong
```
1. Boot → wpa_supplicant tries to connect
2. After 60s → WiFi config detected, not connected
3. Retry for 5 minutes
4. 5 minutes elapsed, connection failed
5. Start hotspot for reconfiguration ✅
```

### Scenario 4: Ethernet While in Hotspot
```
1. Device in hotspot mode
2. User plugs in Ethernet
3. Internet detected
4. Auto-stop hotspot ✅
5. Resume normal monitoring
```

---

## 📦 INSTALLATION

### Fresh Install
```bash
curl -fsSL https://raw.githubusercontent.com/cfd2474/feeder_test/main/install/install.sh | sudo bash
cd /opt/adsb
sudo bash configure-network.sh
sudo reboot
```

### Upgrade from v2.8.0-2.8.3
```bash
# Backup config
sudo cp /opt/adsb/config/.env /opt/adsb/config/.env.backup

# Re-run installer
curl -fsSL https://raw.githubusercontent.com/cfd2474/feeder_test/main/install/install.sh | sudo bash

# Reboot
sudo reboot
```

---

## 🔍 VERIFICATION & DEBUGGING

### Check State File
```bash
cat /var/run/network-monitor-state
# Should show: checking, connected, wifi_retry, or hotspot
```

### Monitor Logs (Real-time)
```bash
sudo tail -f /var/log/network-monitor.log
```

### Example Log Output
```
2026-01-26 12:00:00 - Network monitor started, waiting 60 seconds...
2026-01-26 12:01:00 - WiFi configured but not connected, starting 5-minute retry timer...
2026-01-26 12:01:10 - WiFi connecting... 10s elapsed (timeout: 300s)
2026-01-26 12:01:20 - WiFi connecting... 20s elapsed (timeout: 300s)
2026-01-26 12:01:30 - WiFi connecting... 30s elapsed (timeout: 300s)
2026-01-26 12:01:40 - Internet connection established
```

### Test Captive Portal Flow
```bash
# 1. Disconnect Ethernet (if connected)
sudo ip link set eth0 down

# 2. Remove WiFi config to force hotspot
sudo rm /etc/wpa_supplicant/wpa_supplicant.conf
sudo systemctl restart network-monitor

# 3. Wait for hotspot (check logs)
sudo tail -f /var/log/network-monitor.log

# 4. Connect to TAKNET-PS.local with phone
# 5. Configure WiFi in portal
# 6. Device reboots
# 7. Watch logs - should show 5-minute retry
# 8. WiFi should connect within retry period
```

---

## 📊 TECHNICAL DETAILS

### Files Modified

**install/install.sh:**
- Lines 219-251: check-connection.sh (3-state detection)
- Lines 331-420: network-monitor.sh (state machine)
- Lines 312-321: stop-hotspot.sh (proper service masking)

### Key Algorithm Changes

**Old Logic (v2.8.3):**
```bash
if ! ping; then
    kill wpa_supplicant  # ← PROBLEM!
    start hotspot
    infinite loop
fi
```

**New Logic (v2.8.4):**
```bash
check_connection
case $? in
    0) connected -> monitor
    1) wifi_retry -> wait 5 min, keep checking
    2) no_config -> start hotspot
esac
```

### State Transition Table

| Current State | Check Result | Action | New State |
|--------------|--------------|--------|-----------|
| checking | 0 (connected) | Monitor every 30s | connected |
| checking | 1 (wifi_config) | Start 5-min timer | wifi_retry |
| checking | 2 (no_config) | Start hotspot | hotspot |
| wifi_retry | 0 (connected) | Success! | connected |
| wifi_retry | 1 (still trying) | Continue if <5min | wifi_retry |
| wifi_retry | 1 (timeout) | Start hotspot | hotspot |
| hotspot | 0 (connected) | Stop hotspot | connected |
| connected | !0 (lost conn) | Check if config exists | wifi_retry or hotspot |

---

## 🐛 BUGS FIXED SUMMARY

### v2.8.0-2.8.3 Critical Issues

1. ✅ **Bug #1 (v2.8.3):** Port 5001→8888 iptables mismatch
2. ✅ **Bug #2 (v2.8.3):** Missing iptables monitoring
3. ✅ **Bug #3 (v2.8.3):** Incomplete DNS wildcards
4. ✅ **Bug #4 (v2.8.4):** Missing WiFi retry logic (SHOWSTOPPER)

### v2.8.4 Status
**All critical bugs resolved. Captive portal fully functional end-to-end. Docker startup reliable.**

---

## ⚠️ KNOWN LIMITATIONS

1. **5-minute timeout:** If WiFi takes >5 minutes to connect (very slow router), will fall back to hotspot
   - *Mitigation:* User can reconfigure in portal or wait for next retry
   
2. **No WPA Enterprise:** Only supports WPA/WPA2 PSK (password-based)
   - *Expected:* Most home/small business networks

3. **Single WiFi config:** Overwrites previous WiFi config when using portal
   - *Expected:* Designed for single-location feeders

---

## 🙏 ACKNOWLEDGMENTS

Critical bug discovered during production testing. Root cause identified through log analysis showing wpa_supplicant being killed before connection could establish.

---

## 📞 SUPPORT

**GitHub:** https://github.com/cfd2474/feeder_test  
**Issues:** https://github.com/cfd2474/feeder_test/issues

---

**Version:** 2.8.4  
**Date:** January 26, 2026  
**Severity:** CRITICAL  
**Status:** Production Ready ✅

**This release makes WiFi captive portal actually work. v2.8.0-2.8.3 captive portal was non-functional for WiFi configuration.**
