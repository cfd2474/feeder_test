// Setup wizard navigation
function nextStep(step) {
    document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
    document.getElementById('step' + step).classList.add('active');
}

function prevStep(step) {
    nextStep(step);
}

// Save configuration and start service
async function saveAndStart() {
    const config = {
        FEEDER_LAT: document.getElementById('lat').value,
        FEEDER_LONG: document.getElementById('lon').value,
        FEEDER_ALT_M: document.getElementById('alt').value,
        FEEDER_TZ: document.getElementById('tz').value,
        MLAT_SITE_NAME: document.getElementById('site_name').value,
        
        TAK_ENABLED: document.getElementById('tak_enabled').checked ? 'true' : 'false',
        TAK_SERVER_HOST: document.getElementById('tak_host').value,
        TAK_SERVER_PORT: document.getElementById('tak_port').value,
        
        FR24_ENABLED: document.getElementById('fr24_enabled').checked ? 'true' : 'false',
        FR24_SHARING_KEY: document.getElementById('fr24_key').value,
        
        ADSBX_ENABLED: document.getElementById('adsbx_enabled').checked ? 'true' : 'false',
        ADSBX_UUID: document.getElementById('adsbx_uuid').value,
        
        AIRPLANESLIVE_ENABLED: document.getElementById('airplaneslive_enabled').checked ? 'true' : 'false',
        AIRPLANESLIVE_UUID: document.getElementById('airplaneslive_uuid').value
    };
    
    // Validate location
    if (!config.FEEDER_LAT || !config.FEEDER_LONG) {
        showStatus('Please enter your location', 'error');
        nextStep(1);
        return;
    }
    
    showStatus('Saving configuration...', 'info');
    
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
        
        showStatus('✓ Setup complete! Redirecting to dashboard...', 'success');
        
        setTimeout(() => {
            window.location.href = '/dashboard';
        }, 2000);
        
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
