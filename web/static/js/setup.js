// Setup wizard navigation
function nextStep(step) {
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
                    'User-Agent': 'TAK-ADSB-Feeder/2.1'
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

// Save configuration and start service
async function saveAndStart() {
    const lat = document.getElementById('lat').value;
    const lon = document.getElementById('lon').value;
    const alt = document.getElementById('alt').value;
    const tz = document.getElementById('tz').value;
    const siteName = document.getElementById('site_name').value.trim();
    
    // Validate required fields
    if (!lat || !lon || !alt) {
        showStatus('Please enter latitude, longitude, and altitude', 'error');
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
    
    showStatus('Looking up location information...', 'info');
    
    // Get zip code from coordinates
    const zipCode = await getZipCodeFromCoords(lat, lon);
    
    let finalSiteName;
    if (zipCode) {
        // Format: ZIPCODE-Name
        finalSiteName = `${zipCode}-${siteName}`;
        showStatus(`Location found: ${zipCode}. Saving configuration...`, 'success');
    } else {
        // If zip code lookup fails, use default prefix
        finalSiteName = `00000-${siteName}`;
        showStatus('Could not determine zip code, using default. Saving configuration...', 'info');
    }
    
    const config = {
        // Location settings
        FEEDER_LAT: lat,
        FEEDER_LONG: lon,
        FEEDER_ALT_M: alt,
        FEEDER_TZ: tz,
        MLAT_SITE_NAME: finalSiteName,
        
        // TAK Server is hardcoded - DO NOT send these parameters
        // TAK_ENABLED, TAK_SERVER_HOST_*, TAK_SERVER_PORT will use defaults from env-template
        
        // Optional aggregators only
        FR24_ENABLED: document.getElementById('fr24_enabled').checked ? 'true' : 'false',
        FR24_SHARING_KEY: document.getElementById('fr24_key').value,
        
        ADSBX_ENABLED: document.getElementById('adsbx_enabled').checked ? 'true' : 'false',
        ADSBX_UUID: document.getElementById('adsbx_uuid').value,
        
        AIRPLANESLIVE_ENABLED: document.getElementById('airplaneslive_enabled').checked ? 'true' : 'false',
        AIRPLANESLIVE_UUID: document.getElementById('airplaneslive_uuid').value
    };
    
    try {
        // Save config
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        
        if (!response.ok) throw new Error('Failed to save configuration');
        
        showStatus('Configuration saved! Starting service...', 'success');
        
        // Restart service
        const restartResponse = await fetch('/api/service/restart', {
            method: 'POST'
        });
        
        if (!restartResponse.ok) throw new Error('Failed to restart service');
        
        showStatus(`✓ Setup complete! Feeder name: ${finalSiteName}. Redirecting to dashboard...`, 'success');
        
        setTimeout(() => {
            window.location.href = '/dashboard';
        }, 3000);
        
    } catch (error) {
        showStatus('Error: ' + error.message, 'error');
    }
}

function showStatus(message, type) {
    const status = document.getElementById('status');
    status.textContent = message;
    status.className = type;
    status.style.display = 'block';
}
