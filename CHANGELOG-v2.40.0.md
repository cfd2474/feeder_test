# TAKNET-PS v2.40.0 - FlightAware Integration

## Summary
Complete FlightAware (PiAware) integration with smart Feeder ID detection - matching the elegant FR24 pattern. Users can either provide an existing Feeder ID or generate a new one, then claim it at FlightAware.

---

## What Was Added

### 1. Backend API Endpoints (`web/app.py`)

#### `/api/feeds/piaware/setup` (POST)
**Smart Detection Logic:**
- **IF feeder_id provided:** Validates UUID format, saves to .env, starts container
- **IF feeder_id empty:** Runs temporary PiAware container, extracts new Feeder ID, returns to user for claiming

**Response Modes:**
- `mode: 'existing'` - Used provided Feeder ID
- `mode: 'generated'` - Generated new Feeder ID, requires user to claim at FlightAware

**Feeder ID Generation Process:**
```bash
docker run --rm \
  -e LAT=33.8344 \
  -e LONG=-117.5731 \
  -e RECEIVER_TYPE=none \
  ghcr.io/sdr-enthusiasts/docker-piaware:latest
```

Extracts ID from: `"my feeder ID is xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"`

**UUID Validation:**
- Pattern: `[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}`
- Case insensitive
- Example: `c478b1c9-23d3-4376-1f82-47352a28cg37`

#### `/api/feeds/piaware/toggle` (POST)
**Purpose:** Enable/disable PiAware feed
**Actions:**
- Updates `PIAWARE_ENABLED` in .env
- Starts/stops piaware container via `docker compose`

---

### 2. Frontend UI (`web/templates/feeds-account-required.html`)

#### FlightAware Configuration Card
**Layout:**
```
┌─────────────────────────────────────────────┐
│ FlightAware                    [Active/Inactive]
├─────────────────────────────────────────────┤
│ [✓] Enable FlightAware Feed                 │
│                                              │
│ Feeder ID (UUID format)                     │
│ ┌─────────────────────────────────────────┐ │
│ │ c478b1c9-23d3-4376-1f82-47352a28cg37    │ │
│ └─────────────────────────────────────────┘ │
│ Already have ID? Paste. Need one? Leave    │
│ empty to generate.                           │
│                                              │
│ [Save & Enable FlightAware]                 │
└─────────────────────────────────────────────┘
```

#### JavaScript Functions

**`setupPiaware()` - Smart Setup Handler:**
```javascript
if (input === '') {
    // Generate new Feeder ID
    // Show ID with claim link
    // User claims → comes back → enters ID → saves
} else {
    // Use provided Feeder ID
    // Save and start immediately
}
```

**`togglePiawareEnabled()` - On/Off Toggle:**
- Updates checkbox and status badge
- Calls `/api/feeds/piaware/toggle`
- Shows success/error modal

**`showPiawareResult()` - UI Feedback:**
- Success: Green box with checkmark
- Info: Blue box with instructions and claim link
- Error: Red box with error message

---

### 3. Docker Configuration

#### `config/docker-compose.yml` - PiAware Service
```yaml
piaware:
  image: ghcr.io/sdr-enthusiasts/docker-piaware:latest
  container_name: piaware
  hostname: piaware
  restart: unless-stopped
  networks:
    - adsb_net
  ports:
    - "8081:80"  # PiAware web interface (SkyAware)
  environment:
    - TZ=${FEEDER_TZ}
    - FEEDER_ID=${PIAWARE_FEEDER_ID}
    - RECEIVER_TYPE=relay
    - BEASTHOST=ultrafeeder
    - BEASTPORT=30005
    - ALLOW_MLAT=yes
    - MLAT_RESULTS=yes
  tmpfs:
    - /run:exec,size=64M
    - /var/log
  depends_on:
    - ultrafeeder
```

**Key Configuration:**
- `RECEIVER_TYPE=relay` - Gets data from ultrafeeder, not RTL-SDR
- `BEASTHOST=ultrafeeder` - Connects to Beast output on port 30005
- `ALLOW_MLAT=yes` - Enables multilateration by default
- Port 8081 - PiAware's SkyAware web interface

#### `scripts/config_builder.py` - Auto-Include PiAware
PiAware service always included in generated docker-compose.yml (like FR24).
Can be started/stopped via docker compose without regenerating config.

---

### 4. Dashboard Integration (`web/templates/dashboard.html`)

#### Feed Table Row
```html
{% if config.get('PIAWARE_ENABLED') == 'true' %}
<tr>
    <td>FlightAware</td>
    <td><span id="piaware-check">✓</span></td>
    <td id="piaware-data">.</td>
    <td id="piaware-mlat">.</td>
    <td><a href="#" class="feed-link">🔗</a></td>
</tr>
{% endif %}
```

#### JavaScript Status Updates
```javascript
if (data.service_states && data.service_states.piaware) {
    const state = data.service_states.piaware;
    // Update check column color
    // Update data/MLAT columns with +/. based on state
}
```

**Status Mapping:**
- `running` → Check ✓ (green), Data +, MLAT +
- `starting` → Check ✓ (yellow), Data ., MLAT .
- `stopped` → Check ✓ (red), Data ., MLAT .

#### API Endpoint Update (`web/app.py`)
```python
service_states = {
    'ultrafeeder': get_service_state('ultrafeeder'),
    'fr24': get_service_state('fr24') if env.get('FR24_ENABLED') == 'true' else None,
    'piaware': get_service_state('piaware') if env.get('PIAWARE_ENABLED') == 'true' else None,
    # ...
}
```

---

## User Workflow

### Scenario 1: New User (No Feeder ID)
```
1. User → Feeds → FlightAware
2. Leave Feeder ID field EMPTY
3. Click "Save & Enable FlightAware"
4. System generates new UUID: "c478b1c9-23d3-4376-1f82-47352a28cg37"
5. UI shows:
   ✅ New Feeder ID Generated!
   [UUID shown with copy button]
   Next Steps:
   1. The Feeder ID above has been filled in
   2. Click link below to claim at FlightAware
   3. After claiming, click "Save & Enable FlightAware"
   
   → Claim Feeder at FlightAware
6. User clicks link → Opens FlightAware claim page
7. User claims feeder (associates with FA account)
8. User returns, clicks "Save & Enable FlightAware"
9. Container starts, feeding begins
```

### Scenario 2: Existing User (Has Feeder ID)
```
1. User → Feeds → FlightAware
2. Paste Feeder ID: "c478b1c9-23d3-4376-1f82-47352a28cg37"
3. Click "Save & Enable FlightAware"
4. System validates UUID format
5. Saves to .env, starts container immediately
6. Success message: "FlightAware feed enabled successfully!"
```

---

## Technical Implementation Details

### Environment Variables
```bash
# .env file
PIAWARE_FEEDER_ID=c478b1c9-23d3-4376-1f82-47352a28cg37
PIAWARE_ENABLED=true
```

### Docker Container States
**Detected States:**
- `running` - Container is up and feeding
- `starting` - Container launching
- `stopped` - Container stopped
- `not_installed` - Image not pulled

**State Detection:** `docker ps --filter name=piaware --format '{{.Names}}'`

### FlightAware Claim Process
**Claim URL:** `https://flightaware.com/adsb/piaware/claim/{feeder_id}`

**What Happens When User Claims:**
1. FlightAware associates Feeder ID with user account
2. User can view stats at: `https://flightaware.com/adsb/stats/user/{username}`
3. User must set accurate location on FlightAware website (required for MLAT)

**Important:** PiAware v3.8.0+ removed username/password authentication.
Only Feeder ID + web claim is supported.

---

## Key Design Decisions

### Why Option 2 (Hybrid Smart Detection)?
1. **User-Friendly:** Single field handles both new and existing users
2. **Flexible:** Generate if empty, use if provided
3. **Consistent:** Matches FR24's pattern perfectly
4. **Clear:** User knows exactly what to do next

### Why Not Manual Claim Only?
- Requires user to manually get ID from FlightAware first
- More steps, more friction
- Less elegant than smart detection

### Why Not Auto-Claim?
- FlightAware removed programmatic claiming in v3.8.0
- No API for automatic account association
- Web claiming is required by FlightAware

---

## Error Handling

### Feeder ID Generation Failures
**Timeout (60s):**
```json
{
    "success": false,
    "error_type": "timeout",
    "message": "Timeout while generating Feeder ID. Please try again.",
    "url": "https://flightaware.com/adsb/piaware/claim"
}
```

**ID Extraction Failed:**
```json
{
    "success": false,
    "error_type": "id_extraction_failed",
    "message": "Could not generate Feeder ID. Please try again or get one manually from FlightAware.",
    "url": "https://flightaware.com/adsb/piaware/claim",
    "debug_output": "..."
}
```

### Invalid Feeder ID Format
```json
{
    "success": false,
    "message": "Invalid FlightAware Feeder ID format. Should be UUID format like: c478b1c9-23d3-4376-1f82-47352a28cg37"
}
```

---

## Testing Checklist

### Backend Tests
- [ ] Generate new Feeder ID (empty field)
- [ ] Use existing Feeder ID (valid UUID)
- [ ] Reject invalid UUID format
- [ ] Enable/disable toggle works
- [ ] .env variables saved correctly
- [ ] Container starts/stops via docker compose

### Frontend Tests
- [ ] UI shows Feeder ID in field after generation
- [ ] Claim link opens correct FlightAware URL
- [ ] Success/error messages display properly
- [ ] Status badge updates (Active/Inactive)
- [ ] Toggle checkbox works
- [ ] Mobile display looks good

### Dashboard Tests
- [ ] FlightAware row appears when enabled
- [ ] Status check updates (green/yellow/red)
- [ ] Data and MLAT columns show +/. correctly
- [ ] API polling updates every 5 seconds

### Docker Tests
- [ ] PiAware container starts
- [ ] Connects to ultrafeeder on port 30005
- [ ] Web interface accessible on port 8081
- [ ] Container stops when toggle disabled
- [ ] Survives system reboot (restart: unless-stopped)

---

## Known Limitations

1. **Location Required:** Users MUST set accurate lat/lon/alt on FlightAware website for MLAT to work
2. **Web Claim Only:** No API for automatic claiming (FlightAware policy)
3. **60-Second Timeout:** ID generation times out after 60s (usually takes 10-20s)
4. **No Validation:** Cannot verify if Feeder ID is claimed/active until container runs

---

## Future Enhancements

1. **Stats Integration:** Show FlightAware stats on dashboard (would require FA API key)
2. **MLAT Status:** Detect if MLAT is working (check for port 30105 output)
3. **Link to SkyAware:** Add button to open PiAware web interface (port 8081)
4. **Diagnostic Tool:** Similar to FR24 diagnostic script

---

## Comparison: FR24 vs FlightAware

| Feature | FlightRadar24 | FlightAware |
|---------|---------------|-------------|
| **Auth Method** | Sharing key (email) | Feeder ID (UUID) |
| **Registration** | Auto-register with email | Generate ID → Claim on web |
| **ID Format** | Short hex (16 chars) | UUID (36 chars) |
| **ID Example** | `2b691fe15baf7ad1` | `c478b1c9-23d3-4376-1f82-47352a28cg37` |
| **Smart Field** | Key or Email | Feeder ID or Empty |
| **Container** | `ghcr.io/sdr-enthusiasts/docker-flightradar24` | `ghcr.io/sdr-enthusiasts/docker-piaware` |
| **Web UI Port** | 8754 | 8081 |
| **MLAT Default** | Enabled | Enabled |
| **Reward** | Free Business plan | Free Enterprise access |

---

## Files Modified

| File | Changes | Lines |
|------|---------|-------|
| `web/app.py` | Added 2 endpoints, updated status route | +183 |
| `web/templates/feeds-account-required.html` | Added PiAware card + JavaScript | +188 |
| `web/templates/dashboard.html` | Added PiAware row + JS updates | +44 |
| `config/docker-compose.yml` | Added piaware service | +20 |
| `scripts/config_builder.py` | Added piaware to compose builder | +20 |
| `VERSION` | Updated to 2.40.0 | 1 |

**Total:** 6 files, ~456 lines added

---

## Version History

- **v2.39.0-v2.39.2:** FR24 integration (smart registration, MLAT, dashboard fixes)
- **v2.40.0:** FlightAware integration (smart Feeder ID detection)

---

## Package Contents

```
taknet-ps-complete-v2.40.0-20260208-HHMMSS.tar.gz
├── config/
│   └── docker-compose.yml          (includes piaware service)
├── scripts/
│   ├── config_builder.py           (generates piaware in compose)
│   └── fr24-diagnostic.sh
├── web/
│   ├── app.py                      (piaware setup/toggle endpoints)
│   ├── static/
│   └── templates/
│       ├── dashboard.html          (piaware status display)
│       └── feeds-account-required.html (piaware config UI)
├── update_web.sh
├── VERSION                         (2.40.0)
└── CHANGELOG-v2.40.0.md           (this file)
```

---

## Quick Start Commands

### Install Web Files Only
```bash
cd /tmp
tar -xzf taknet-ps-complete-v2.40.0-*.tar.gz
cd taknet-ps-complete-v2.27.2-full
sudo bash update_web.sh
sudo systemctl restart taknet-ps-web
```

### Regenerate Docker Compose
```bash
cd /opt/adsb/config
python3 /opt/adsb/scripts/config_builder.py
```

### Manual PiAware Operations
```bash
# Start PiAware
cd /opt/adsb/config
docker compose up -d piaware

# Check status
docker logs piaware --tail 50

# View web interface
open http://$(hostname -I | awk '{print $1}'):8081

# Stop PiAware
docker compose stop piaware
```

---

## Support & Documentation

**FlightAware Resources:**
- PiAware GitHub: https://github.com/sdr-enthusiasts/docker-piaware
- Claim Feeder: https://flightaware.com/adsb/piaware/claim
- My ADS-B Stats: https://flightaware.com/adsb/stats/user/{username}
- Support Forum: https://discussions.flightaware.com

**TAKNET-PS Resources:**
- GitHub Issues: Report bugs and request features
- Discord: Real-time support and community help

---

## Credits

**Implementation:**
- FlightAware integration follows FR24 pattern from v2.39.x
- Docker containers by sdr-enthusiasts organization
- PiAware software by FlightAware Inc.

**Testing:**
- Corona, CA test site (33.8344°N, -117.5731°W)
- Raspberry Pi 3B hardware
- FlightAware USB SDR dongle

---

**End of CHANGELOG-v2.40.0**
