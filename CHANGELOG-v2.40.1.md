# TAKNET-PS v2.40.1 - Feed Links & UI Improvements

## Changes from v2.40.0

### 🔗 **Feed Status Links** (Dashboard)
All feed status links are now functional and open their respective stats pages:

#### **Account-Required Feeds** (Local Pages)
- **FlightRadar24** → `http://[FEEDER_IP]:8754/` (Local FR24 stats page)
- **FlightAware** → `http://[FEEDER_IP]:8082/` (Local PiAware SkyAware page)

#### **Accountless Feeds** (API Endpoints)
- **adsb.fi** → `https://api.adsb.fi/v1/myip` (Your feed stats)
- **adsb.lol** → `https://api.adsb.lol/0/me` (Your feed stats)
- **ADSBexchange** → `https://www.adsbexchange.com/myip/` (Your feed stats)
- **Airplanes.Live** → `https://airplanes.live/myfeed/` (Your feed stats)

#### **TAKNET-PS Server**
- No external link (internal TAKNET-PS network)
- Link icon shown as grayed out (non-clickable)

### 📝 **FlightAware Setup Instructions** (Clearer UX)

**OLD Instructions (v2.40.0):**
```
Already have a Feeder ID? Paste it here. Need one? Leave empty and click below to generate.

How It Works:
- Leave Feeder ID blank → We generate one for you
- Click the claim link → Link to your FlightAware account
- Enter the ID above → Save and start feeding
```

**NEW Instructions (v2.40.1):**
```
You need a FlightAware / Piaware feeder ID. If you already have one, 
please enter it below. Otherwise, leave the field empty and click on 
the button and we will try to get one for you. Once this process completes 
and the feeder ID has been filled in, open the local Piaware page (this 
should open in a new tab) and click on the "Claim this feeder on FlightAware" button.

Quick Start: New to FlightAware? Just click "Save & Enable FlightAware" 
with an empty field and we'll handle the setup!

- System generates a unique Feeder ID
- Opens local PiAware page in new tab
- Click "Claim this feeder" button on that page
- Done! Your feeder is now linked to your FlightAware account
```

### 🎯 **Auto-Open Local PiAware Page**
When generating a new FlightAware Feeder ID, the system now:
1. Generates the UUID
2. **Automatically opens** `http://[FEEDER_IP]:8082/` in a new tab
3. Shows instructions to click "Claim this feeder on FlightAware" button
4. Provides "Open Local PiAware Page Again" link if tab was closed

### 🔧 **Port Correction**
- **PiAware Web Interface:** Changed from port `8081` to `8082`
- Updated in: `docker-compose.yml`, `config_builder.py`, JavaScript functions

---

## Technical Details

### Modified Files

| File | Changes |
|------|---------|
| `web/templates/dashboard.html` | +20 lines (openFeedLink function, updated all link URLs) |
| `web/templates/feeds-account-required.html` | Modified (clearer instructions, auto-open local page) |
| `config/docker-compose.yml` | Port 8081 → 8082 |
| `scripts/config_builder.py` | Port 8081 → 8082 |
| `VERSION` | → 2.40.1 |

### JavaScript Function Added

```javascript
function openFeedLink(feedType) {
    const hostname = window.location.hostname;
    let url;
    
    switch(feedType) {
        case 'fr24':
            url = `http://${hostname}:8754/`;
            break;
        case 'piaware':
            url = `http://${hostname}:8082/`;
            break;
        default:
            console.error('Unknown feed type:', feedType);
            return;
    }
    
    window.open(url, '_blank');
}
```

### Auto-Open on ID Generation

```javascript
// Open local PiAware page in new tab
const localPiawareUrl = `http://${window.location.hostname}:8082`;
window.open(localPiawareUrl, '_blank');
```

---

## User Experience Improvements

### Before (v2.40.0)
1. User generates Feeder ID
2. Sees claim URL: `https://flightaware.com/adsb/piaware/claim/{uuid}`
3. Clicks external FlightAware link
4. Claims on FlightAware website
5. Returns to enable

**Problem:** External claim page requires FlightAware account login first

### After (v2.40.1)
1. User generates Feeder ID
2. **Local PiAware page auto-opens in new tab**
3. User clicks "Claim this feeder on FlightAware" button on local page
4. That button opens FlightAware claim page with proper context
5. Returns to enable

**Benefit:** Local PiAware page provides better UX and context

---

## Feed Status Pages

### What You'll See

#### **FlightRadar24** (Port 8754)
```
FR24 Feeder Status
- Sharing Key: 2b691fe15baf7ad1
- Aircraft Tracked: 47
- Connection: Connected
- MLAT: Active
- Uptime: 2d 4h 32m
```

#### **FlightAware / PiAware** (Port 8082)
```
PiAware SkyAware
- Feeder ID: c478b1c9-23d3-4376-1f82-47352a28cg37
- Aircraft Map (live view)
- Messages Received: 12,847
- Position Messages: 8,234
- Connection Status: Connected
- MLAT: Synchronized
```

#### **adsb.fi API**
```json
{
  "ip": "YOUR_IP",
  "feed_status": "active",
  "aircraft_count": 52,
  "messages_per_second": 124.5,
  "mlat_enabled": true
}
```

#### **adsb.lol API**
```json
{
  "feeder": "YOUR_IP",
  "status": "connected",
  "aircraft": 48,
  "rate": 132.1
}
```

#### **ADSBexchange API**
```
ADSBexchange Feeder Stats
Your IP: YOUR_IP
Status: Connected
Aircraft: 51
Position Rate: 128/s
MLAT: Active
```

#### **Airplanes.Live**
```
Your Feed Statistics
Feeder IP: YOUR_IP
Status: Online
Aircraft Tracked: 49
Message Rate: 119/s
Coverage Map: [Shows your coverage area]
```

---

## Testing Checklist

### Feed Links
- [ ] FR24 link opens `http://[IP]:8754/` in new tab
- [ ] PiAware link opens `http://[IP]:8082/` in new tab
- [ ] adsb.fi link opens API endpoint in new tab
- [ ] adsb.lol link opens API endpoint in new tab
- [ ] ADSBexchange link opens stats page in new tab
- [ ] Airplanes.Live link opens feed stats in new tab
- [ ] TAKNET-PS link is grayed out (non-clickable)

### FlightAware Setup
- [ ] Generate ID auto-opens local PiAware page (8082)
- [ ] Instructions clearly explain the process
- [ ] "Open Local PiAware Page Again" link works
- [ ] Existing Feeder ID entry works as before

### Port Changes
- [ ] PiAware container accessible on port 8082
- [ ] Old port 8081 no longer in use
- [ ] Config builder generates correct port

---

## Upgrade Instructions

### Quick Upgrade (Web Only)
```bash
cd /tmp
tar -xzf taknet-ps-complete-v2.40.1-*.tar.gz
cd taknet-ps-complete-v2.27.2-full
sudo bash update_web.sh
sudo systemctl restart taknet-ps-web
```

### Full Upgrade (Web + Docker)
```bash
# Same as above, then:

# Update docker-compose.yml
cd /opt/adsb/config
python3 /opt/adsb/scripts/config_builder.py

# Recreate PiAware container with new port
docker compose up -d piaware
```

**Note:** If PiAware was already running on 8081, you'll need to recreate the container to pick up the new 8082 port mapping.

---

## Benefits

✅ **One-Click Feed Status** - All feeds have working status links  
✅ **Better FlightAware UX** - Local page auto-opens with clear instructions  
✅ **Consistent Port** - PiAware on 8082 as specified  
✅ **External API Links** - Direct links to feed stats for accountless feeds  
✅ **Clearer Instructions** - Step-by-step FlightAware setup guidance  

---

**TAKNET-PS v2.40.1** - Feed Links & UI Polish Complete! 🔗✨
