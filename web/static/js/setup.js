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
    
    // Declare variables for Tailscale
    let tailscaleEnabled, tailscaleKey;
    
    // Check if we're online or offline
    if (isOnline) {
        // ONLINE MODE: Read Tailscale key field
        console.log("Online mode: Reading Tailscale key...");
        tailscaleKey = document.getElementById('tailscale_key').value.trim();
        
        // Enable Tailscale if key is provided
        tailscaleEnabled = tailscaleKey.length > 0;
        console.log("Tailscale:", {enabled: tailscaleEnabled, hasKey: tailscaleKey.length > 0});
        
        if (tailscaleKey && tailscaleKey.length > 0) {
            console.log("Tailscale key provided, will be enabled");
        } else {
            console.log("No Tailscale key, will be disabled");
        }
    } else {
        // OFFLINE MODE: Disable all internet-dependent services
        console.log("Offline mode: Disabling Tailscale");
        tailscaleEnabled = false;
        tailscaleKey = '';
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
        TAILSCALE_AUTH_KEY: tailscaleKey || ''
        
        // TAKNET-PS Server is hardcoded - DO NOT send these parameters
        // TAKNET_PS_ENABLED, TAKNET_PS_SERVER_HOST_*, TAKNET_PS_SERVER_PORT will use defaults from env-template
        
        // Note: Aggregators (FR24, Airplanes.Live, adsb.fi, adsb.lol) are configured on the Feeds page
        // They are not part of the wizard anymore
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

// Enable/disable Connect Tailscale button based on key input
function checkTailscaleKey() {
    const keyInput = document.getElementById('tailscale_key');
    const connectBtn = document.getElementById('connect-tailscale-btn');
    
    if (keyInput && connectBtn) {
        const key = keyInput.value.trim();
        // Enable button if key looks valid (starts with tskey- and is reasonably long)
        const isValidFormat = key.startsWith('tskey-') && key.length > 20;
        connectBtn.disabled = !isValidFormat;
    }
}

// Connect Tailscale with auth key
async function connectTailscale() {
    const keyInput = document.getElementById('tailscale_key');
    const authKey = keyInput.value.trim();
    
    if (!authKey) {
        showStatus('Please enter a Tailscale auth key', 'error');
        return;
    }
    
    // Show progress modal
    document.getElementById('tailscaleProgressModal').style.display = 'block';
    document.getElementById('progress-status-text').textContent = 'Starting Tailscale installation...';
    document.getElementById('progress-details').innerHTML = '<div>[' + new Date().toLocaleTimeString() + '] Initializing...</div>';
    
    try {
        // Start installation
        const response = await fetch('/api/tailscale/install', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                auth_key: authKey
            })
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.message || 'Failed to start Tailscale installation');
        }
        
        // Save the key to config immediately
        await fetch('/api/config/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                TAILSCALE_ENABLED: 'true',
                TAILSCALE_AUTH_KEY: authKey
            })
        });
        
        // Start polling for progress
        pollTailscaleProgress();
        
    } catch (error) {
        console.error('Failed to connect Tailscale:', error);
        document.getElementById('progress-status-text').textContent = 'Error: ' + error.message;
        document.getElementById('progress-status-text').style.color = '#ef4444';
        document.getElementById('progress-modal-buttons').style.display = 'block';
    }
}

// Skip Tailscale and go to Location step
function skipTailscale() {
    // Save that Tailscale is disabled
    fetch('/api/config/update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            TAILSCALE_ENABLED: 'false'
        })
    }).then(() => {
        nextStep(1); // Go to Location step
    }).catch(error => {
        console.error('Failed to save Tailscale disabled:', error);
        nextStep(1); // Go anyway
    });
}

// Poll Tailscale installation progress
let progressPollInterval = null;

async function pollTailscaleProgress() {
    let attempts = 0;
    const maxAttempts = 60; // 60 seconds timeout
    
    progressPollInterval = setInterval(async () => {
        attempts++;
        
        try {
            const response = await fetch('/api/tailscale/progress');
            const data = await response.json();
            
            updateTailscaleProgressUI(data);
            
            // Check if complete or failed
            if (data.status === 'completed' || data.status === 'failed' || attempts >= maxAttempts) {
                clearInterval(progressPollInterval);
                
                if (data.status === 'completed') {
                    // Success - wait 2 seconds then proceed to next step
                    setTimeout(() => {
                        closeProgressModal();
                        nextStep(1); // Go to Location step
                    }, 2000);
                } else {
                    // Failed or timeout - show close button
                    document.getElementById('progress-modal-buttons').style.display = 'block';
                }
            }
        } catch (error) {
            console.error('Failed to poll progress:', error);
            
            if (attempts >= maxAttempts) {
                clearInterval(progressPollInterval);
                document.getElementById('progress-status-text').textContent = 'Connection timeout - check status in Settings';
                document.getElementById('progress-status-text').style.color = '#f59e0b';
                document.getElementById('progress-modal-buttons').style.display = 'block';
            }
        }
    }, 1000); // Poll every 1 second
}

// Update Tailscale progress UI
function updateTailscaleProgressUI(data) {
    const statusText = document.getElementById('progress-status-text');
    const downloadPercent = document.getElementById('download-percent');
    const downloadProgress = document.getElementById('download-progress');
    const installPercent = document.getElementById('install-percent');
    const installProgress = document.getElementById('install-progress');
    const progressDetails = document.getElementById('progress-details');
    
    // Update status text
    if (data.status === 'downloading') {
        statusText.textContent = 'Downloading Tailscale...';
        statusText.style.color = '#374151';
        downloadPercent.textContent = `${data.download_progress || 0}%`;
        downloadProgress.style.width = `${data.download_progress || 0}%`;
        installPercent.textContent = '0%';
        installProgress.style.width = '0%';
    } else if (data.status === 'installing') {
        statusText.textContent = 'Installing Tailscale...';
        statusText.style.color = '#374151';
        downloadPercent.textContent = '100%';
        downloadProgress.style.width = '100%';
        installPercent.textContent = `${data.install_progress || 0}%`;
        installProgress.style.width = `${data.install_progress || 0}%`;
    } else if (data.status === 'connecting') {
        statusText.textContent = 'Connecting to Tailscale network...';
        statusText.style.color = '#374151';
        downloadPercent.textContent = '100%';
        downloadProgress.style.width = '100%';
        installPercent.textContent = `${data.install_progress || 75}%`;
        installProgress.style.width = `${data.install_progress || 75}%`;
    } else if (data.status === 'completed') {
        statusText.textContent = '✓ Tailscale connected successfully!';
        statusText.style.color = '#10b981';
        downloadPercent.textContent = '100%';
        downloadProgress.style.width = '100%';
        installPercent.textContent = '100%';
        installProgress.style.width = '100%';
    } else if (data.status === 'failed') {
        statusText.textContent = '✗ Tailscale installation failed';
        statusText.style.color = '#ef4444';
    }
    
    // Update details
    if (data.message) {
        const detailLine = document.createElement('div');
        detailLine.textContent = `[${new Date().toLocaleTimeString()}] ${data.message}`;
        detailLine.style.marginBottom = '4px';
        progressDetails.appendChild(detailLine);
        progressDetails.scrollTop = progressDetails.scrollHeight;
    }
}

// Close progress modal
function closeProgressModal() {
    document.getElementById('tailscaleProgressModal').style.display = 'none';
    
    // Reset UI
    document.getElementById('progress-status-text').textContent = 'Initializing...';
    document.getElementById('progress-status-text').style.color = '#374151';
    document.getElementById('download-percent').textContent = '0%';
    document.getElementById('download-progress').style.width = '0%';
    document.getElementById('install-percent').textContent = '0%';
    document.getElementById('install-progress').style.width = '0%';
    document.getElementById('progress-details').innerHTML = '';
    document.getElementById('progress-modal-buttons').style.display = 'none';
    
    // Clear polling interval if still running
    if (progressPollInterval) {
        clearInterval(progressPollInterval);
        progressPollInterval = null;
    }
}

// Initialize Tailscale key checking
document.addEventListener('DOMContentLoaded', function() {
    const keyInput = document.getElementById('tailscale_key');
    if (keyInput) {
        keyInput.addEventListener('input', checkTailscaleKey);
        // Check on page load in case value is pre-filled
        checkTailscaleKey();
    }
});
