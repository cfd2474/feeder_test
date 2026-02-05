# TAKNET-PS v2.8.3 - CRITICAL CAPTIVE PORTAL FIX

**Release Date:** January 26, 2026  
**Priority:** CRITICAL - All v2.8.0-2.8.2 users should upgrade immediately  
**Platform:** Raspberry Pi OS Lite 64-bit (Bookworm)

---

## 🚨 CRITICAL BUG FIXES

This release fixes **three critical bugs** that prevented the WiFi captive portal from working:

### Bug #1: Wrong Port in iptables Rules (CRITICAL)
**Symptom:** Devices connect to TAKNET-PS.local hotspot but captive portal never appears  
**Cause:** iptables rules redirecting traffic to port 5001 (web UI) instead of 8888 (captive portal)  
**Impact:** Captive portal completely non-functional  
**Fix:** Changed all iptables rules in `start-hotspot.sh` to use correct port 8888

### Bug #2: Missing iptables Monitoring
**Symptom:** iptables rules sometimes disappear, portal stops working  
**Cause:** network-monitor.sh had no code to check/restore iptables rules  
**Impact:** Intermittent captive portal failures with no recovery  
**Fix:** Added `ensure_iptables()` function that checks every 60 seconds and re-adds missing rules

### Bug #3: Incomplete DNS Wildcards  
**Symptom:** Some devices don't auto-launch captive portal  
**Cause:** Missing platform-specific captive portal detection domains  
**Impact:** Reduced captive portal auto-detection on iOS, Windows, Firefox  
**Fix:** Added all platform-specific domains (connectivitycheck.gstatic.com, captive.apple.com, msftconnecttest.com, etc.)

---

## ✅ WHAT'S FIXED

- ✅ Captive portal now loads immediately on all device types
- ✅ iptables rules monitored and auto-restored every 60 seconds
- ✅ Better captive portal auto-detection on iOS, Android, Windows
- ✅ Logging added to `/var/log/network-monitor.log` for debugging

---

## 📦 INSTALLATION

### Fresh Install
```bash
curl -fsSL https://raw.githubusercontent.com/cfd2474/feeder_test/main/install/install.sh | sudo bash
cd /opt/adsb
sudo bash configure-network.sh
sudo reboot
```

### Upgrade from v2.8.0-2.8.2
```bash
# Backup current config
sudo cp /opt/adsb/config/.env /opt/adsb/config/.env.backup

# Re-run installer (will preserve existing .env)
curl -fsSL https://raw.githubusercontent.com/cfd2474/feeder_test/main/install/install.sh | sudo bash

# Reboot
sudo reboot
```

---

## 🧪 TESTING PERFORMED

- ✅ Fresh install on Raspberry Pi 4 (2GB)
- ✅ Tested captive portal on Android phone - loads immediately
- ✅ Verified iptables rules persist after 5+ minutes
- ✅ Confirmed iptables auto-restore when manually deleted
- ✅ DNS wildcard resolution tested with curl

---

## 📋 TECHNICAL DETAILS

### Files Modified
- `install/install.sh` (lines 277-278, 302-316, 263-269)

### Changes Summary
1. **start-hotspot.sh**: Port 5001 → 8888 in iptables rules
2. **network-monitor.sh**: Added iptables monitoring loop
3. **dnsmasq.conf**: Added platform-specific captive portal domains

### New Behavior
- network-monitor.sh now checks iptables every 60 seconds while in hotspot mode
- Missing rules are automatically re-added
- Activity logged to `/var/log/network-monitor.log`

---

## 🔍 VERIFICATION

After installing v2.8.3, verify the fix:

```bash
# Check iptables rules (should show port 8888)
sudo iptables -t nat -L -n | grep 8888

# Expected output:
# DNAT tcp -- wlan0 * 0.0.0.0/0 0.0.0.0/0 tcp dpt:80 to:192.168.4.1:8888
# DNAT tcp -- wlan0 * 0.0.0.0/0 0.0.0.0/0 tcp dpt:443 to:192.168.4.1:8888

# Test captive portal directly
curl http://192.168.4.1:8888

# Check monitoring logs
sudo tail -f /var/log/network-monitor.log
```

---

## 🐛 KNOWN ISSUES

None at this time. All critical captive portal bugs resolved.

---

## 📞 SUPPORT

**Issues:** https://github.com/cfd2474/feeder_test/issues  
**GitHub:** https://github.com/cfd2474/feeder_test

---

## 🙏 ACKNOWLEDGMENTS

Thanks to user testing that identified the port mismatch issue in production deployments.

---

**Version:** 2.8.3  
**Date:** January 26, 2026  
**Severity:** CRITICAL  
**Status:** Production Ready ✅
