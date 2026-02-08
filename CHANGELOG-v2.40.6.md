# TAKNET-PS v2.40.6 Release Notes

**Release Date:** February 8, 2026  
**Type:** Critical UX Fix  
**Fixes:** Setup wizard timeout with real-time Docker progress monitoring

---

## 🎯 The Problem

When completing the setup wizard and clicking "Save & Start":

**What users experienced:**
- Click "Save & Start" button
- Loading spinner appears
- Wait 2-3 minutes...
- ❌ **ERROR: "Request timed out after 2 minutes"**
- User thinks setup failed
- **(But actually setup continues in background and completes successfully!)**

**Why it happened:**
- Initial setup pulls 3 Docker images (~500MB each)
- On slow connections, downloads take 5-10 minutes
- Previous code had a 2-3 minute timeout
- Code used `journalctl` which didn't show real Docker progress
- No way to tell if setup was actually working or stuck

**User confusion:**
> "It errored out due to timeout (2min) I now see that its running"

---

## ✨ The Solution

**v2.40.6 completely rewrites the progress monitoring system:**

### 1. **Direct Docker Compose Output Streaming**
   - Instead of watching systemd logs, now monitors `docker-compose` directly
   - Parses real-time output from Docker engine
   - **NO TIMEOUT** - monitors until actually complete!

### 2. **Real Progress Calculation**
   - Tracks which images are being pulled (ultrafeeder, piaware, fr24)
   - Shows actual download amounts (MB downloaded / MB total)
   - Monitors image extraction progress
   - Tracks container creation and startup
   - Updates progress bar based on actual stages

### 3. **Professional User Experience**
   - Shows exactly what's happening at each stage
   - Progress bar fills based on real operations, not time estimates
   - Works on any connection speed (slow or fast)
   - No more timeout errors!

---

## 📊 User Experience Comparison

### Before (v2.40.5):
```
Click "Save & Start"
→ Loading spinner...
→ Wait 2 minutes...
→ ❌ "Request timeout - setup may have failed"
→ User confused, doesn't know if it worked
```

### After (v2.40.6):
```
Click "Save & Start"
→ Progress: 5%  - Starting Docker Compose...
→ Progress: 10% - Pulling ultrafeeder image... (15.2MB / 450MB)
→ Progress: 28% - Downloading ultrafeeder... (120MB / 450MB)
→ Progress: 30% - Pulling piaware image... (5MB / 380MB)
→ Progress: 45% - Extracting piaware...
→ Progress: 50% - Pulling fr24 image... (80MB / 320MB)
→ Progress: 70% - Creating network...
→ Progress: 75% - Creating ultrafeeder...
→ Progress: 80% - Creating piaware...
→ Progress: 90% - Starting ultrafeeder...
→ Progress: 95% - Starting piaware ✓
→ Progress: 100% - Setup complete! All containers running ✓
→ ✅ Automatically redirects to dashboard
```

**Time:** However long it actually takes (5-10 minutes on slow connection)  
**Result:** User sees progress the entire time, knows exactly what's happening

---

## 🔧 Technical Changes

### File Modified: `web/app.py`

#### 1. Updated `monitor_docker_progress()` Function (Lines 255-440)

**Before:**
- Watched `journalctl -u ultrafeeder -f`
- Tried to parse systemd logs
- Had 180-second timeout
- Couldn't see real Docker progress

**After:**
- Runs `docker compose up -d` directly
- Streams stdout in real-time
- Parses actual Docker engine output
- **No timeout - monitors until complete**
- Tracks 5 distinct phases:
  1. Image pulling (0-68%)
  2. Network creation (70%)
  3. Container creation (75-85%)
  4. Container startup (90-99%)
  5. Final verification (100%)

**Key improvements:**
```python
# Old way - buffered, timed out
process = subprocess.Popen(['journalctl', '-u', service_name, '-f'])
# ... timeout after 180s

# New way - real-time streaming, no timeout
process = subprocess.Popen(
    ['docker', 'compose', 'up', '-d'],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1  # Line buffered
)
# Read until process actually completes
for line in process.stdout:
    # Parse each line for progress indicators
    ...
```

#### 2. Updated `restart_service()` Function (Lines 376-404)

**Before:**
- Called `systemctl restart ultrafeeder`
- Started journalctl monitoring in background
- Systemctl has its own timeout

**After:**
- Monitoring thread now runs docker-compose directly
- No systemctl involvement for setup wizard
- Progress monitoring handles the entire operation
- Cleaner, more direct approach

#### 3. Version Update
- Version bumped from 2.39.2 → 2.40.6

---

## 📦 What Gets Monitored

The new system watches for and reports these Docker events:

### Phase 1: Image Pulling (0-68%)
```
 Container ultrafeeder  Pulling
 14324c29e8df Pulling fs layer
 14324c29e8df Downloading  25.5MB/450MB
 14324c29e8df Extracting   120MB/450MB
 Image ghcr.io/sdr-enthusiasts/docker-adsb-ultrafeeder:latest Pulled
```
**Shows:** "Pulling ultrafeeder image... 25.5MB / 450MB"

### Phase 2: Network Creation (70%)
```
 Network config_adsb_net Creating
 Network config_adsb_net Created
```
**Shows:** "Creating network... Setting up"

### Phase 3: Container Creation (75-85%)
```
 Container ultrafeeder Creating
 Container ultrafeeder Created
 Container piaware Creating
 Container piaware Created
```
**Shows:** "Creating ultrafeeder... Initializing"

### Phase 4: Container Startup (90-99%)
```
 Container ultrafeeder Starting
 Container ultrafeeder Started
 Container piaware Starting
 Container piaware Started
```
**Shows:** "Starting ultrafeeder... Almost done"

### Phase 5: Verification (100%)
```python
# Final check - is ultrafeeder actually running?
docker ps --filter name=ultrafeeder --filter status=running
```
**Shows:** "Setup complete! All containers running ✓"

---

## 🚀 Benefits

1. **No More Timeouts**
   - Monitors until actually complete
   - Works on any connection speed
   - 5-minute download? Shows progress the whole time

2. **Accurate Progress**
   - Based on real Docker operations
   - Not time-based estimates
   - Shows actual MB downloaded

3. **Better Debugging**
   - If setup actually fails, you'll see where it stopped
   - No more guessing if it's working or broken
   - Console logs show detailed Docker output

4. **Professional Feel**
   - Like npm install, apt-get, or pip install
   - Modern progress indicators
   - Clear status messages

5. **User Confidence**
   - Users know setup is working
   - Can see download progress
   - Understand why it takes time

---

## 🔄 Upgrade Instructions

### Quick Update (From Any Previous Version)

```bash
cd /tmp
tar -xzf taknet-ps-complete-v2.40.6-*.tar.gz
cd taknet-ps-complete-v2.27.2-full
sudo bash update_web.sh
```

**That's it!** The update script:
- Backs up current web directory
- Installs new code
- Restarts web service
- Your existing configuration is preserved

---

## 🧪 Testing

After updating, test the new progress system:

1. **Go to Settings page** in web interface
2. **Click "Save & Start"** button
3. **Watch the progress bar** - you should see:
   - Percentage increasing based on actual operations
   - Status text showing current stage
   - Detail text showing container names, MB amounts
   - No timeout errors!

**First-time setup:** If you delete your config and re-run the wizard, the first "Save & Start" will take 5-10 minutes as it downloads images. But you'll see progress the entire time!

**Subsequent restarts:** Will be fast (~30 seconds) because images are already downloaded.

---

## 🐛 Bug Fixes

### v2.40.6
- ✅ Fixed setup wizard timeout error
- ✅ Added real-time Docker progress monitoring
- ✅ Removed arbitrary timeout limits
- ✅ Improved progress accuracy

### v2.40.5 (Previous)
- Fixed FlightAware Feeder ID generation timeout
- Implemented real-time streaming for piaware container

### v2.40.4 (Previous)
- Fixed RECEIVER_TYPE bug causing indefinite hang

---

## 💡 For Developers

### How the Progress System Works

```python
# Global progress state
service_progress = {
    'service': 'ultrafeeder',
    'progress': 0,      # 0-100
    'total': 100,
    'message': 'Starting...',
    'detail': ''
}

# Frontend polls this endpoint every 2 seconds
@app.route('/api/service/progress')
def api_service_progress():
    return jsonify(service_progress)

# Background thread updates progress based on Docker output
def monitor_docker_progress():
    for line in docker_output:
        if 'Downloading' in line:
            # Parse MB amounts
            # Update progress
            update_progress(service_name, 25, 100, 'Downloading...', '25MB/100MB')
```

### Adding More Progress Stages

To track additional services (like new feeders):

1. Add detection pattern in `monitor_docker_progress()`
2. Assign progress range (e.g., 0-33% for service 1, 34-66% for service 2)
3. Parse Docker output for that service
4. Call `update_progress()` with appropriate values

---

## 📝 Notes

- **No breaking changes** - Existing configurations work as-is
- **Web service restart required** - Run update script or `systemctl restart adsb-web.service`
- **Compatible with all previous versions**
- **Docker Compose required** - Already a dependency, no new requirements

---

## 🙏 User Feedback

This fix was implemented based on direct user feedback:

> "it errored out due to timeout (2min) I now see that its running. when it is downloading/installing/setting up at the end of the wizard, lets make a qualified status, not just one that times out. it should be listening to processes and figuring out a completion rate"

Thank you for the detailed feedback! This is exactly the kind of real-world usage insight that makes TAKNET-PS better.

---

## 📞 Support

If you encounter any issues with v2.40.6:

1. Check systemd logs: `journalctl -u adsb-web.service -n 50`
2. Check Docker logs: `docker compose logs`
3. Verify containers running: `docker ps`
4. Report issues with logs included

---

**Version:** 2.40.6  
**Build Date:** 2026-02-08  
**Status:** Production Ready  
**Tested On:** Rocky Linux 8, Raspberry Pi OS (Debian 12)
