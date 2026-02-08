# TAKNET-PS v2.40.2 - Airplanes.Live Critical Fix

## 🚨 **CRITICAL BUG FIX: Airplanes.Live Feed**

This release fixes **two major issues** that prevented Airplanes.Live feeds from working properly.

---

## 🐛 **Issues Fixed**

### **Issue #1: UUID Requirement (Blocking Feed)**
**Problem:** Airplanes.Live feed required a `AIRPLANESLIVE_UUID` environment variable that was never generated or prompted for.

**Result:** Feed configuration was silently skipped even when enabled.

**Fix:** Removed UUID requirement entirely. Airplanes.Live identifies feeders by **IP address**, not UUID.

**Before (v2.40.0-v2.40.1):**
```python
if env_vars.get('AIRPLANESLIVE_ENABLED', '').lower() == 'true':
    if env_vars.get('AIRPLANESLIVE_UUID', '').strip():  # ❌ UUID never existed!
        config_parts.append("adsb,feed.airplanes.live,30004,beast_reduce_plus_out")
        config_parts.append("mlat,mlat.airplanes.live,31090,39002")
```

**After (v2.40.2):**
```python
if env_vars.get('AIRPLANESLIVE_ENABLED', '').lower() == 'true':
    # No UUID check - Airplanes.Live uses IP identification
    config_parts.append("adsb,feed.airplanes.live,30004,beast_reduce_plus_out")
    config_parts.append("mlat,feed.airplanes.live,31090,39002")  # ✅ Fixed server name
```

---

### **Issue #2: Wrong MLAT Server**
**Problem:** MLAT feed was connecting to `mlat.airplanes.live` instead of `feed.airplanes.live`.

**Result:** MLAT connection failed silently.

**Fix:** Changed MLAT server from `mlat.airplanes.live` → `feed.airplanes.live` to match official documentation.

**Before (v2.40.0-v2.40.1):**
```python
config_parts.append("mlat,mlat.airplanes.live,31090,39002")  # ❌ Wrong server!
```

**After (v2.40.2):**
```python
config_parts.append("mlat,feed.airplanes.live,31090,39002")  # ✅ Correct server!
```

**Source:** [sdr-enthusiasts/docker-adsb-ultrafeeder documentation](https://github.com/sdr-enthusiasts/docker-adsb-ultrafeeder/blob/main/docker-compose.yml)

```yaml
# Official example from ultrafeeder:
- ULTRAFEEDER_CONFIG=
    adsb,feed.airplanes.live,30004,beast_reduce_plus_out;
    mlat,feed.airplanes.live,31090,39002;
```

---

### **Issue #3: Config Not Regenerated on Toggle**
**Problem:** When feeds were toggled on/off, only the `.env` file was updated. The `docker-compose.yml` was **not regenerated**, so ultrafeeder never got the updated `READSB_NET_CONNECTOR` environment variable.

**Result:** Feed toggles appeared to work in the UI, but ultrafeeder kept using old configuration.

**Fix:** Added automatic config regeneration when feeds are toggled.

**Before (v2.40.0-v2.40.1):**
```python
# Update .env file
update_env_var(env_var, value)

# Restart ultrafeeder to apply changes
subprocess.run(['docker', 'restart', 'ultrafeeder'], timeout=30, check=True)
```

**After (v2.40.2):**
```python
# Update .env file
update_env_var(env_var, value)

# Regenerate docker-compose.yml with updated feed configuration
subprocess.run(
    ['python3', '/opt/adsb/scripts/config_builder.py'],
    cwd='/opt/adsb/config',
    timeout=30,
    check=True
)

# Restart ultrafeeder with updated configuration
subprocess.run(['docker', 'compose', 'up', '-d', 'ultrafeeder'], 
             cwd='/opt/adsb/config',
             timeout=30, 
             check=True)
```

---

## 🔍 **How Airplanes.Live Actually Works**

According to [airplanes.live/how-to-feed/](https://airplanes.live/how-to-feed/):

### **Identification Method**
- **IP-based identification** (no UUID/sharing key required)
- Feed server: `78.46.234.18` (resolves from `feed.airplanes.live`)
- Check your feed status at: https://airplanes.live/myfeed/

### **Connection Ports**
- **ADS-B Data:** Port `30004` (BEAST format)
- **MLAT Data:** Port `31090`

### **Expected netstat Output**
```bash
$ netstat -t -n | grep -E '30004|31090'
tcp 0 182 localhost:43530 78.46.234.18:31090 ESTABLISHED  # MLAT
tcp 0 410 localhost:47332 78.46.234.18:30004 ESTABLISHED  # ADS-B
```

---

## ✅ **Verification Steps**

### **1. Check Feed Configuration**
```bash
# View generated ultrafeeder config
docker exec ultrafeeder cat /run/readsb/net-connector.txt

# Should show:
# adsb,feed.airplanes.live,30004,beast_reduce_plus_out
# mlat,feed.airplanes.live,31090,39002
```

### **2. Check Docker Logs**
```bash
docker logs ultrafeeder 2>&1 | grep -i "airplanes"

# Should see connection attempts/successes
```

### **3. Check netstat (if available)**
```bash
docker exec ultrafeeder netstat -tn | grep "30004\|31090"

# Look for connections to feed.airplanes.live
```

### **4. Check Feed Status**
Visit: https://airplanes.live/myfeed/
- Should show your feeder as **active**
- Shows aircraft count and message rates
- Map displays your coverage area

---

## 📋 **Files Modified**

| File | Changes | Impact |
|------|---------|--------|
| `scripts/config_builder.py` | Fixed Airplanes.Live config | Removes UUID requirement, fixes MLAT server |
| `web/app.py` | Added config regeneration | Ensures docker-compose.yml updates on feed toggle |
| `VERSION` | → 2.40.2 | Version bump |

---

## 🚀 **Upgrade Instructions**

### **Critical Upgrade - All Users Should Update!**

```bash
# Extract v2.40.2 package
cd /tmp
tar -xzf taknet-ps-complete-v2.40.2-*.tar.gz
cd taknet-ps-complete-v2.27.2-full

# Update web interface
sudo bash update_web.sh
sudo systemctl restart taknet-ps-web

# Regenerate docker-compose.yml with correct Airplanes.Live config
cd /opt/adsb/config
python3 /opt/adsb/scripts/config_builder.py

# Restart ultrafeeder to apply fixes
docker compose up -d ultrafeeder

# Verify Airplanes.Live is now connecting
docker logs ultrafeeder 2>&1 | grep -i "airplanes"
```

### **For New Installations**
No special steps needed - Airplanes.Live will work correctly out of the box.

---

## 🔄 **Comparison: Before vs After**

### **v2.40.0 - v2.40.1 (BROKEN)**
```python
# Airplanes.Live
if env_vars.get('AIRPLANESLIVE_ENABLED', '').lower() == 'true':
    if env_vars.get('AIRPLANESLIVE_UUID', '').strip():  # ❌ Never true!
        config_parts.append("adsb,feed.airplanes.live,30004,beast_reduce_plus_out")
        config_parts.append("mlat,mlat.airplanes.live,31090,39002")  # ❌ Wrong server!
        print("✓ Airplanes.Live")
```

**Result:** Feed silently skipped, never configured!

### **v2.40.2 (FIXED)**
```python
# Airplanes.Live (no UUID required - they identify by IP address)
if env_vars.get('AIRPLANESLIVE_ENABLED', '').lower() == 'true':
    config_parts.append("adsb,feed.airplanes.live,30004,beast_reduce_plus_out")
    config_parts.append("mlat,feed.airplanes.live,31090,39002")  # ✅ Correct!
    print("✓ Airplanes.Live")
```

**Result:** Feed configured correctly, connects immediately!

---

## 📊 **Other Feeds - UUID Requirements**

For reference, here's how different feeds handle identification:

| Feed | ID Method | Requirement |
|------|-----------|-------------|
| **Airplanes.Live** | IP address | None (auto-detected) |
| **adsb.fi** | IP address | None (auto-detected) |
| **adsb.lol** | UUID | Requires FEEDER_UUID |
| **ADSBexchange** | UUID | Requires FEEDER_UUID |
| **FlightRadar24** | Sharing key | Requires FR24_SHARING_KEY |
| **FlightAware** | Feeder ID | Requires PIAWARE_FEEDER_ID |

**Note:** `FEEDER_UUID` is automatically generated when adsb.lol or ADSBexchange are enabled.

---

## 🎯 **Testing Your Airplanes.Live Feed**

### **Method 1: Web Dashboard**
1. Visit: https://airplanes.live/myfeed/
2. Should show:
   - ✅ **Status:** Active/Connected
   - 📊 **Aircraft Count:** Current aircraft being tracked
   - 📈 **Message Rate:** Messages per second
   - 🗺️ **Coverage Map:** Your reception area

### **Method 2: Docker Logs**
```bash
docker logs ultrafeeder 2>&1 | tail -100 | grep -i "airplanes"

# Good output examples:
# "Connected to feed.airplanes.live:30004"
# "MLAT: connected to feed.airplanes.live:31090"
```

### **Method 3: Container Inspection**
```bash
# Check ultrafeeder environment
docker inspect ultrafeeder | grep -A 20 "Env"

# Should see READSB_NET_CONNECTOR with feed.airplanes.live
```

---

## ⚠️ **Important Notes**

### **Why IP-Based Identification?**
Airplanes.Live (like adsb.fi) uses your **public IP address** to identify your feeder. This means:
- ✅ No registration required
- ✅ No sharing keys to manage
- ✅ Instant feed activation
- ⚠️ Dynamic IP changes might temporarily lose feed history
- ⚠️ Multiple feeders behind same IP need separate instances

### **MLAT Synchronization**
MLAT (Multilateration) requires:
1. Accurate feeder location (LAT/LON/ALT)
2. Stable connection to MLAT server
3. Multiple feeders in the area
4. Aircraft with Mode S transponders

**Check MLAT status:**
```bash
docker logs ultrafeeder 2>&1 | grep -i "mlat"
```

---

## 🎉 **Benefits of Airplanes.Live**

According to their website:
- ✈️ **Unfiltered Data:** All aircraft visible (no filtering like some aggregators)
- 🌍 **Community-Driven:** Run by volunteers, no commercial interests
- 📊 **Full MLAT Support:** Multilateration for aircraft without ADS-B position
- 🗺️ **Coverage Maps:** See your reception area
- 📈 **Statistics:** Real-time feed performance metrics
- 🆓 **Free Access:** No premium tiers, full access for all feeders

---

## 🔗 **Resources**

- **Airplanes.Live Homepage:** https://airplanes.live
- **How to Feed Guide:** https://airplanes.live/how-to-feed/
- **Check Your Feed:** https://airplanes.live/myfeed/
- **Tracking Map:** https://globe.airplanes.live
- **Discord Community:** https://discord.gg/jfVRF2XRwF
- **GitHub (Feed Scripts):** https://github.com/airplanes-live/feed

---

**TAKNET-PS v2.40.2** - Airplanes.Live Feed Now Working! ✈️✨

**Critical Fixes:**
- ✅ Removed broken UUID requirement
- ✅ Fixed MLAT server address
- ✅ Added auto-config regeneration on feed toggle

**All users should upgrade immediately!**
