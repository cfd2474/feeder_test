# TAKNET-PS v2.41.7 Release Notes

**Release Date:** February 9, 2026  
**Type:** Critical Installer Fix  
**Focus:** env-template Missing Variables

---

## 🐛 Critical Bug Fix

### Installer Missing PiAware and ADSBHub Variables

**Issue:** The `config/env-template` file was missing critical variables for account-required feeders:
- ❌ PIAWARE_FEEDER_ID
- ❌ PIAWARE_ENABLED
- ❌ ADSBHUB_STATION_KEY
- ❌ ADSBHUB_ENABLED

**Result:**
- Fresh installations had docker-compose.yml with containers ✓
- But .env file was missing the environment variables ✗
- Caused "no such service" errors or container start failures

**Fixed:** Added all missing variables to `config/env-template`

---

## 🔧 What Was Fixed

### config/env-template

**Added FlightAware Variables:**
```bash
# FlightAware / PiAware
PIAWARE_ENABLED=false
PIAWARE_FEEDER_ID=
```

**Added ADSBHub Variables:**
```bash
# ADSBHub
ADSBHUB_ENABLED=false
ADSBHUB_STATION_KEY=
```

**Now Complete:**
All three account-required feeders have proper variables:
1. ✅ FlightRadar24 (FR24_KEY, FR24_ENABLED)
2. ✅ FlightAware (PIAWARE_FEEDER_ID, PIAWARE_ENABLED)
3. ✅ ADSBHub (ADSBHUB_STATION_KEY, ADSBHUB_ENABLED)

---

## 🎯 Impact

### Before v2.41.7

**Fresh installation:**
```
1. Installer downloads docker-compose.yml ✓
   - Has ultrafeeder, piaware, fr24, adsbhub containers
2. Installer downloads env-template as .env ✗
   - Missing PIAWARE_FEEDER_ID
   - Missing PIAWARE_ENABLED
   - Missing ADSBHUB_STATION_KEY
   - Missing ADSBHUB_ENABLED
3. User tries to enable FlightAware or ADSBHub ✗
   - Error: "no such service: adsbhub"
   - Or container fails to start properly
```

### After v2.41.7

**Fresh installation:**
```
1. Installer downloads docker-compose.yml ✓
   - Has ultrafeeder, piaware, fr24, adsbhub containers
2. Installer downloads env-template as .env ✓
   - Has FR24_KEY, FR24_ENABLED
   - Has PIAWARE_FEEDER_ID, PIAWARE_ENABLED
   - Has ADSBHUB_STATION_KEY, ADSBHUB_ENABLED
3. User enables any feeder ✓
   - All containers start properly
   - No errors
```

---

## ✨ What's Included from Previous Versions

### From v2.41.6
- ✅ FlightAware modal auto-dismiss

### From v2.41.5
- ✅ ADSBHub button disabled until key entered
- ✅ ADSBHub Docker pre-download
- ✅ Updated user note with 🛡️

### From v2.41.4
- ✅ ADSBHub feed support
- ✅ docker-compose.yml with ADSBHub container

---

## 📦 Files Modified

```
config/env-template
  → Added PIAWARE_FEEDER_ID
  → Added PIAWARE_ENABLED
  → Added ADSBHUB_STATION_KEY
  → Added ADSBHUB_ENABLED

VERSION
  → Updated to 2.41.7

web/app.py
  → VERSION = "2.41.7"
```

---

## ✅ Verification

After fresh install with v2.41.7:

**1. Check .env has all variables:**
```bash
grep PIAWARE /opt/adsb/config/.env
# Should show:
# PIAWARE_ENABLED=false
# PIAWARE_FEEDER_ID=

grep ADSBHUB /opt/adsb/config/.env
# Should show:
# ADSBHUB_ENABLED=false
# ADSBHUB_STATION_KEY=
```

**2. Configure feeders:**
```
1. FlightRadar24: Enter email or key → Works ✓
2. FlightAware: Generate or enter feeder ID → Works ✓
3. ADSBHub: Enter station key → Works ✓
```

**3. All containers start:**
```bash
docker compose -f /opt/adsb/config/docker-compose.yml up -d piaware
docker compose -f /opt/adsb/config/docker-compose.yml up -d adsbhub
# Both should start without errors
```

---

## 🚨 Critical for Fresh Installations

**This fix is ESSENTIAL for anyone doing a fresh install!**

**Previous versions (2.41.4-2.41.6):**
- Had ADSBHub and FlightAware in docker-compose.yml ✓
- But installer's env-template was incomplete ✗
- Required manual fixes after installation

**Version 2.41.7:**
- Complete installer ✓
- All variables included ✓
- No manual fixes needed ✓

---

## 🔄 Migration

**If you already installed v2.41.4-2.41.6:**

You likely had to manually add ADSBHub to docker-compose.yml. Those manual fixes are fine.

**If you're doing a FRESH install:**

Use v2.41.7 - it has everything needed from the start.

---

## 📞 Summary

**Problem:** env-template missing PIAWARE and ADSBHUB variables  
**Impact:** Fresh installs couldn't use FlightAware or ADSBHub properly  
**Fix:** Added all missing variables to env-template  
**Result:** Clean fresh installations with all feeders working  

---

**Version:** 2.41.7  
**Build Date:** 2026-02-09  
**Status:** Production Ready  
**Breaking Changes:** None  
**Critical Fix:** env-template complete ✅

**This is the installer fix you needed!** 🚀
