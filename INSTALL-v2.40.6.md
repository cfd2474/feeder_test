# TAKNET-PS v2.40.6 Installation Guide

**Version:** 2.40.6  
**Release Date:** February 8, 2026  
**Key Feature:** Real-time Docker progress monitoring - NO MORE TIMEOUTS! 🎉

---

## 🎯 What This Fixes

**Before:** Setup wizard times out after 2 minutes, showing error even when setup succeeds  
**After:** Real-time progress shows exactly what's happening until complete (no timeout!)

You'll now see:
- "Pulling ultrafeeder image... 120MB / 450MB"
- "Creating containers..."
- "Starting ultrafeeder ✓"
- "Setup complete! All containers running ✓"

---

## ⚡ Quick Install

### From Any Previous Version

```bash
# Download and extract
cd /tmp
tar -xzf taknet-ps-complete-v2.40.6-20260208-realtime-progress.tar.gz
cd taknet-ps-complete-v2.27.2-full

# Run update script
sudo bash update_web.sh

# Verify
systemctl status adsb-web.service
```

**Done!** Your existing config is preserved. Web service automatically restarted.

---

## 📋 What Gets Updated

The update script:
1. ✅ Backs up current `/opt/adsb/web` directory
2. ✅ Installs new `web/app.py` with progress monitoring
3. ✅ Restarts `adsb-web.service`
4. ✅ Preserves all your settings and configurations

**Safe:** If anything goes wrong, your backup is at `/opt/adsb/web.backup.[timestamp]`

---

## 🧪 Testing After Install

### Test the New Progress System

1. **Open TAKNET-PS web interface**
   - Navigate to: `http://your-server:5000`

2. **Go to Settings page**
   - Click "Settings" in navigation

3. **Make a small change and save**
   - Example: Change antenna height
   - Click "Save & Start"

4. **Watch the progress!**
   - You should see real-time updates:
     - "Starting Docker Compose..."
     - "Creating containers..."
     - "Starting ultrafeeder ✓"
   - Progress bar fills based on actual operations
   - **No timeout errors!**

### First-Time Setup Test

If you want to test the full progress system including image downloads:

```bash
# Delete images to force re-download (OPTIONAL - for testing only)
sudo docker rmi ghcr.io/sdr-enthusiasts/docker-adsb-ultrafeeder:latest
sudo docker rmi ghcr.io/sdr-enthusiasts/docker-piaware:latest
sudo docker rmi ghcr.io/sdr-enthusiasts/docker-flightradar24:latest

# Now run setup wizard - you'll see full download progress!
```

---

## 🔍 Verify Installation

### Check Web Service

```bash
# Should show "active (running)"
systemctl status adsb-web.service

# Should show version 2.40.6 in output
journalctl -u adsb-web.service -n 20
```

### Check for Errors

```bash
# Web service logs
journalctl -u adsb-web.service -n 50

# Python syntax check
python3 -m py_compile /opt/adsb/web/app.py
echo $?  # Should output: 0
```

### Verify Progress Endpoint

```bash
# Test progress API (should return JSON)
curl http://localhost:5000/api/service/progress
```

Expected output:
```json
{
  "detail": "",
  "message": "Idle",
  "progress": 0,
  "service": "ultrafeeder",
  "total": 100
}
```

---

## 🔄 Rollback (If Needed)

If you need to go back to previous version:

```bash
# Stop web service
sudo systemctl stop adsb-web.service

# Find your backup
ls -la /opt/adsb/web.backup.*

# Restore backup (use your timestamp)
sudo rm -rf /opt/adsb/web
sudo cp -r /opt/adsb/web.backup.YYYYMMDD-HHMMSS /opt/adsb/web

# Restart service
sudo systemctl restart adsb-web.service
```

---

## ❓ Troubleshooting

### Issue: "Permission denied" during update

```bash
# Ensure you're using sudo
sudo bash update_web.sh
```

### Issue: Web service won't start

```bash
# Check for Python errors
journalctl -u adsb-web.service -n 50

# Verify syntax
python3 -m py_compile /opt/adsb/web/app.py

# Check file ownership
ls -la /opt/adsb/web/
# Should be: adsb:adsb
```

### Issue: Still seeing timeout errors

```bash
# Check version actually updated
grep "VERSION =" /opt/adsb/web/app.py
# Should show: VERSION = "2.40.6"

# Restart web service
sudo systemctl restart adsb-web.service

# Clear browser cache and reload
```

### Issue: Progress not updating

```bash
# Check if progress monitoring thread started
journalctl -u adsb-web.service -f

# Click "Save & Start" and watch logs
# Should see: "✓ Docker Compose starting with real-time progress monitoring"
```

---

## 📊 What You'll See

### Example Progress Sequence

**On fast connection (images cached):**
```
0%   - Initializing...
5%   - Starting Docker Compose...
70%  - Creating network...
75%  - Creating ultrafeeder...
80%  - Creating piaware...
90%  - Starting ultrafeeder...
95%  - Starting piaware ✓
100% - Setup complete! All containers running ✓
```
**Time:** ~30 seconds

**On slow connection (first-time image download):**
```
0%   - Initializing...
5%   - Starting Docker Compose...
10%  - Pulling ultrafeeder image...
12%  - Downloading ultrafeeder... 15.2MB / 450MB
18%  - Downloading ultrafeeder... 75MB / 450MB
25%  - Downloading ultrafeeder... 200MB / 450MB
28%  - Extracting ultrafeeder...
30%  - Pulling piaware image...
32%  - Downloading piaware... 20MB / 380MB
45%  - Extracting piaware...
50%  - Pulling fr24 image...
52%  - Downloading fr24... 50MB / 320MB
65%  - Extracting fr24...
70%  - Creating network...
75%  - Creating ultrafeeder...
80%  - Creating piaware...
85%  - Creating fr24...
90%  - Starting ultrafeeder...
93%  - Starting piaware ✓
96%  - Starting fr24 ✓
100% - Setup complete! All containers running ✓
```
**Time:** 5-10 minutes (depending on connection)

**You see progress the entire time - no timeout!**

---

## 🎁 Bonus: Debug Mode

Want to see detailed Docker output?

```bash
# Watch web service logs in real-time
journalctl -u adsb-web.service -f

# In another terminal, trigger setup
# (Go to web interface, click "Save & Start")

# You'll see detailed Docker compose output!
```

---

## 📦 Package Contents

```
taknet-ps-complete-v2.40.6-20260208-realtime-progress.tar.gz
├── web/
│   └── app.py (v2.40.6 with real-time progress)
├── update_web.sh (update script)
├── CHANGELOG-v2.40.6.md (this document)
└── INSTALL-v2.40.6.md (detailed install guide)
```

---

## 🔗 Related Changes

**v2.40.6:** Real-time Docker progress monitoring (this release)  
**v2.40.5:** FlightAware Feeder ID real-time streaming  
**v2.40.4:** Fixed RECEIVER_TYPE bug  

All three versions work together to provide a smooth, timeout-free setup experience!

---

## 💡 Pro Tips

1. **First-time setup takes longer** - Docker needs to download images (~1.5GB total). But you'll see progress!

2. **Subsequent setups are fast** - Images are cached, so restarts take ~30 seconds

3. **Pre-download images** (optional):
   ```bash
   sudo docker pull ghcr.io/sdr-enthusiasts/docker-adsb-ultrafeeder:latest
   sudo docker pull ghcr.io/sdr-enthusiasts/docker-piaware:latest
   sudo docker pull ghcr.io/sdr-enthusiasts/docker-flightradar24:latest
   ```

4. **Watch it work** - Keep the browser window open during setup to see the progress bar update in real-time!

---

## ✅ Installation Checklist

- [ ] Downloaded v2.40.6 package
- [ ] Extracted to `/tmp`
- [ ] Ran `sudo bash update_web.sh`
- [ ] Verified web service running: `systemctl status adsb-web.service`
- [ ] Checked version: `grep VERSION /opt/adsb/web/app.py` → Shows "2.40.6"
- [ ] Tested progress: Click "Save & Start" in Settings
- [ ] Verified no timeout errors
- [ ] Confirmed containers running: `docker ps`

---

**Installation Time:** 2-3 minutes  
**Downtime:** ~10 seconds (web service restart)  
**Difficulty:** Easy (just run one script)  

Happy tracking! 📡✈️
