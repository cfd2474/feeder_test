// Offline mode detection
let isOnline = true; // Will be checked on page load

// Check internet connectivity
async function checkInternetConnection() {
    try {
        const response = await fetch('/api/network-status', {
            method: 'GET',
            cache: 'no-cache'
        });
        const data = await response.json();
        return data.internet || false;
    } catch (error) {
        console.error('Failed to check internet:', error);
        return false;
    }
}

// Initialize offline mode detection
async function initializeOfflineMode() {
    isOnline = await checkInternetConnection();
    console.log('Internet connection status:', isOnline ? 'ONLINE' : 'OFFLINE');
    
    if (!isOnline) {
        // Show offline warning
        const warningEl = document.getElementById('offlineWarning');
        if (warningEl) {
            warningEl.style.display = 'block';
        }
        
        // Change Step 1 button to "Save & Start" instead of "Next"
        const step1Button = document.querySelector('#step1 .btn-primary');
        if (step1Button) {
            step1Button.textContent = 'Save & Start 🚀';
            step1Button.onclick = function() {
                // Validate Step 1 first
                const lat = document.getElementById('lat').value.trim();
                const lon = document.getElementById('lon').value.trim();
                const alt = document.getElementById('alt').value.trim();
                const tz = document.getElementById('tz').value;
                const siteName = document.getElementById('site_name').value.trim();
                
                if (!lat || !lon || !alt || !tz) {
                    showStatus('Please fill in all required location fields', 'error');
                    return;
                }
                
                if (!siteName) {
                    showStatus('Please enter a feeder name', 'error');
                    return;
                }
                
                // Validate formats
                const latPattern = /^-?\d+\.\d+$/;
                const lonPattern = /^-?\d+\.\d+$/;
                const altPattern = /^\d+$/;
                
                if (!latPattern.test(lat)) {
                    showStatus('Latitude must be in decimal format (e.g., 33.55390)', 'error');
                    return;
                }
                
                if (!lonPattern.test(lon)) {
                    showStatus('Longitude must be in decimal format (e.g., -117.21390)', 'error');
                    return;
                }
                
                if (!altPattern.test(alt)) {
                    showStatus('Altitude must be a whole number (e.g., 304)', 'error');
                    return;
                }
                
                // Validation passed - go directly to save (skip Tailscale and aggregators)
                saveAndStart();
            };
        }
        
        console.log('Offline mode: Steps 2 and 3 will be skipped');
    }
}

// Setup wizard navigation
function nextStep(step) {
    console.log("=== nextStep called, step:", step);
    // Validate step 1 (location AND feeder name) before allowing navigation to step 2
    if (step === 2) {
        console.log("Validating for step 2...");
        const lat = document.getElementById('lat').value.trim();
        const lon = document.getElementById('lon').value.trim();
        const alt = document.getElementById('alt').value.trim();
        const tz = document.getElementById('tz').value;
        const siteName = document.getElementById('site_name').value.trim();
        
        console.log("Field values:", {lat, lon, alt, tz, siteName});
        // Check required fields (including site_name!)
        if (!lat || !lon || !alt || !tz) {
            showStatus('Please fill in all required location fields', 'error');
            return;
        }
        
        if (!siteName) {
            showStatus('Please enter a feeder name', 'error');
            return;
        }
        
        // Validate coordinate format
        const latPattern = /^-?\d+\.\d+$/;
        const lonPattern = /^-?\d+\.\d+$/;
        const altPattern = /^\d+$/;
        
        if (!latPattern.test(lat)) {
            showStatus('Latitude must be in decimal format (e.g., 33.55390)', 'error');
            return;
        }
        
        if (!lonPattern.test(lon)) {
            showStatus('Longitude must be in decimal format (e.g., -117.21390)', 'error');
            return;
        }
        
        if (!altPattern.test(alt)) {
            showStatus('Altitude must be a whole number (e.g., 304)', 'error');
            return;
        }
    }
    
    // Navigation approved - show next step
    document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
    document.getElementById('step' + step).classList.add('active');
}

function prevStep(step) {
    nextStep(step);
}

// Get zip code from coordinates using reverse geocoding
async function getZipCodeFromCoords(lat, lon) {
    try {
        // Use Nominatim (OpenStreetMap) reverse geocoding - free, no API key needed
        const response = await fetch(
            `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&zoom=18&addressdetails=1`,
            {
                headers: {
                    'User-Agent': 'TAKNET-PS-ADSB-Feeder/2.1'
                }
            }
        );
        
        if (!response.ok) throw new Error('Geocoding failed');
        
        const data = await response.json();
        
        // Try to extract postal code from address
        if (data.address) {
            return data.address.postcode || data.address.postal_code || null;
        }
        
        return null;
    } catch (error) {
        console.error('Failed to get zip code:', error);
        return null;
    }
}

// Install Tailscale with auth key
async function installTailscale(authKey) {
    try {
        const response = await fetch('/api/tailscale/install', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ auth_key: authKey })
        });
        
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('Failed to install Tailscale:', error);
        return { success: false, message: 'Failed to communicate with server' };
    }
}

// Save configuration and start service
async function saveAndStart() {
    const lat = document.getElementById('lat').value;
    const lon = document.getElementById('lon').value;
    const alt = document.getElementById('alt').value;
    const tz = document.getElementById('tz').value;
    const siteName = document.getElementById('site_name').value.trim();
    const userZipCode = document.getElementById('zip_code').value.trim();
    
    // Validate required fields
    if (!lat || !lon || !alt) {
        showStatus('Please enter latitude, longitude, and altitude', 'error');
        nextStep(1);
        return;
    }
    
    // Validate coordinate format
    const latPattern = /^-?\d+\.\d+$/;
    const lonPattern = /^-?\d+\.\d+$/;
    
    if (!latPattern.test(lat)) {
        showStatus('Latitude must be in decimal format (e.g., 33.55390)', 'error');
        nextStep(1);
        return;
    }
    
    if (!lonPattern.test(lon)) {
        showStatus('Longitude must be in decimal format (e.g., -117.21390)', 'error');
        nextStep(1);
        return;
    }
    
    if (!tz) {
        showStatus('Please select a timezone', 'error');
        nextStep(1);
        return;
    }
    
    if (!siteName) {
        showStatus('Please enter a feeder name', 'error');
        nextStep(1);
        return;
    }
    
    let finalSiteName;
    let zipCode;
    
    if (userZipCode) {
        // User provided zip code - use it directly
        zipCode = userZipCode;
        finalSiteName = `${zipCode}-${siteName}`;
        showStatus(`Using your zip code: ${zipCode}. Processing configuration...`, 'success');
    } else {
        // No user zip code - estimate from coordinates
        showStatus('Looking up location information...', 'info');
        zipCode = await getZipCodeFromCoords(lat, lon);
        
        if (zipCode) {
            finalSiteName = `${zipCode}-${siteName}`;
            showStatus(`Location found: ${zipCode}. Processing configuration...`, 'success');
        } else {
            // If zip code lookup fails, use default prefix
            finalSiteName = `00000-${siteName}`;
            showStatus('Could not determine zip code, using default. Processing configuration...', 'info');
        }
    }

    console.log("Zip code processing complete. finalSiteName:", finalSiteName);
    
    // Declare variables for Tailscale and aggregators
    let tailscaleEnabled, tailscaleKey;
    let fr24Enabled, fr24Key;
    let adsbxEnabled, adsbxUuid;
    let airplanesLiveEnabled, airplanesLiveUuid;
    
    // Check if we're online or offline
    if (isOnline) {
        // ONLINE MODE: Read from DOM elements
        console.log("Online mode: Reading Tailscale fields...");
        tailscaleEnabled = document.getElementById('tailscale_enabled').checked;
        tailscaleKey = document.getElementById('tailscale_key').value.trim();
        console.log("Tailscale:", {enabled: tailscaleEnabled, hasKey: tailscaleKey.length > 0});
        
        // Validate Tailscale
        if (tailscaleEnabled && !tailscaleKey) {
            showStatus('Tailscale enabled but no key provided. You can configure it later in Settings.', 'info');
        }
        
        console.log("Online mode: Reading aggregator fields...");
        fr24Enabled = document.getElementById('fr24_enabled').checked;
        fr24Key = document.getElementById('fr24_key').value;
        adsbxEnabled = document.getElementById('adsbx_enabled').checked;
        adsbxUuid = document.getElementById('adsbx_uuid').value;
        airplanesLiveEnabled = document.getElementById('airplaneslive_enabled').checked;
        airplanesLiveUuid = document.getElementById('airplaneslive_uuid').value;
        
        console.log("Aggregators:", {
            fr24: fr24Enabled,
            adsbx: adsbxEnabled,
            airplanesLive: airplanesLiveEnabled
        });
    } else {
        // OFFLINE MODE: Disable all internet-dependent services
        console.log("Offline mode: Disabling all internet-dependent services");
        tailscaleEnabled = false;
        tailscaleKey = '';
        fr24Enabled = false;
        fr24Key = '';
        adsbxEnabled = false;
        adsbxUuid = '';
        airplanesLiveEnabled = false;
        airplanesLiveUuid = '';
    }
    
    const config = {
        // Location settings
        FEEDER_LAT: lat,
        FEEDER_LONG: lon,
        FEEDER_ALT_M: alt,
        FEEDER_TZ: tz,
        MLAT_SITE_NAME: finalSiteName,
        ZIP_CODE: userZipCode || zipCode || '',
        
        // Tailscale settings
        TAILSCALE_ENABLED: tailscaleEnabled ? 'true' : 'false',
        TAILSCALE_AUTH_KEY: tailscaleKey || '',
        
        // TAKNET-PS Server is hardcoded - DO NOT send these parameters
        // TAKNET_PS_ENABLED, TAKNET_PS_SERVER_HOST_*, TAKNET_PS_SERVER_PORT will use defaults from env-template
        
        // Optional aggregators only
        FR24_ENABLED: fr24Enabled ? 'true' : 'false',
        FR24_SHARING_KEY: fr24Key || '',
        
        ADSBX_ENABLED: adsbxEnabled ? 'true' : 'false',
        ADSBX_UUID: adsbxUuid || '',
        
        AIRPLANESLIVE_ENABLED: airplanesLiveEnabled ? 'true' : 'false',
        AIRPLANESLIVE_UUID: airplanesLiveUuid || ''
    };
    
    console.log("Config object built:", config);
    
    console.log("Config object built:", config);
    
    showStatus('Saving configuration...', 'info');
    console.log("Showing status overlay...");
    showStatusOverlay('Saving Configuration...', 'Building docker-compose and updating services');
    console.log("Status overlay shown, starting fetch...");
    
    try {
        // Save config
        console.log("Fetching /api/config...");
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        
        if (!response.ok) throw new Error('Failed to save configuration');
        
        showSuccessOverlay('Configuration Saved!', 'Starting services...');
        
        // Brief delay to show success message
        setTimeout(() => {
            window.location.href = '/loading';
        }, 1500);
        
    } catch (error) {
        hideStatusOverlay();
        showStatus('Error: ' + error.message, 'error');
    }
}

function showStatus(message, type) {
    const status = document.getElementById('status');
    status.textContent = message;
    status.className = type;
    status.style.display = 'block';
}

// Status overlay functions
function showStatusOverlay(message, detail) {
    let overlay = document.getElementById('status-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'status-overlay';
        overlay.className = 'status-overlay';
        overlay.innerHTML = `
            <div class="status-content">
                <div class="spinner"></div>
                <h2 id="overlay-message">${message}</h2>
                <p id="overlay-detail">${detail || 'Please wait...'}</p>
            </div>
        `;
        document.body.appendChild(overlay);
    } else {
        document.getElementById('overlay-message').textContent = message;
        document.getElementById('overlay-detail').textContent = detail || 'Please wait...';
        overlay.style.display = 'flex';
    }
}

function hideStatusOverlay() {
    const overlay = document.getElementById('status-overlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

function showSuccessOverlay(message, detail) {
    let overlay = document.getElementById('status-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'status-overlay';
        overlay.className = 'status-overlay';
        document.body.appendChild(overlay);
    }
    
    overlay.innerHTML = `
        <div class="status-content success">
            <div style="font-size: 60px; color: #10b981; margin-bottom: 20px;">✓</div>
            <h2>${message}</h2>
            <p>${detail || ''}</p>
        </div>
    `;
    overlay.style.display = 'flex';
}
