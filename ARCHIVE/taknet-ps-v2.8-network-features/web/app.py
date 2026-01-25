#!/usr/bin/env python3
"""
TAKNET-PS-ADSB-Feeder Web Interface v2.8
Flask app with WiFi portal, mDNS support, and Nginx integration
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import subprocess
import os
import re
from pathlib import Path

app = Flask(__name__)

ENV_FILE = Path("/opt/adsb/config/.env")
CONFIG_BUILDER = "/opt/adsb/scripts/config_builder.py"
WIFI_STATE_FILE = Path("/opt/adsb/config/.wifi-state")
WIFI_CREDS_FILE = Path("/opt/adsb/config/.wifi-credentials")

# TAKNET-PS Server hardcoded connection details - NEVER allow user to change these
TAK_PROTECTED_SETTINGS = {
    'TAKNET_PS_SERVER_HOST_PRIMARY': '100.117.34.88',
    'TAKNET_PS_SERVER_HOST_FALLBACK': '104.225.219.254',
    'TAKNET_PS_SERVER_PORT': '30004',
    'TAKNET_PS_CONNECTION_MODE': 'auto'
}

def read_env():
    """Read .env file and return as dict"""
    env_vars = {}
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars

def write_env(env_vars):
    """Write dict to .env file"""
    lines = []
    for key, value in env_vars.items():
        lines.append(f"{key}={value}\n")
    with open(ENV_FILE, 'w') as f:
        f.writelines(lines)

def get_docker_status():
    """Get Docker container status"""
    try:
        result = subprocess.run(
            ['docker', 'ps', '--format', '{{.Names}}\t{{.Status}}'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            containers = {}
            for line in result.stdout.strip().split('\n'):
                if line:
                    name, status = line.split('\t', 1)
                    containers[name] = status
            return containers
        return {}
    except:
        return {}

def restart_service():
    """Restart ultrafeeder service"""
    import time
    try:
        # Brief delay to prevent rapid-fire restarts
        time.sleep(2)
        
        result = subprocess.run(
            ['systemctl', 'restart', 'ultrafeeder'],
            timeout=30,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✓ Ultrafeeder service restarted")
            return True
        else:
            print(f"✗ Restart failed (code {result.returncode}): {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("✗ Restart timed out after 30 seconds")
        return False
    except Exception as e:
        print(f"✗ Restart error: {str(e)}")
        return False

def rebuild_config():
    """Run config_builder.py to regenerate ULTRAFEEDER_CONFIG"""
    try:
        result = subprocess.run(
            ['python3', CONFIG_BUILDER],
            timeout=15,
            capture_output=True,
            text=True,
            cwd='/opt/adsb/scripts'
        )
        if result.returncode == 0:
            print("✓ Config rebuilt successfully")
            print(result.stdout)
            return True
        else:
            print(f"✗ Config builder failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Config builder error: {str(e)}")
        return False

def install_tailscale(auth_key=None, hostname=None):
    """Install and configure Tailscale"""
    try:
        # Check if tailscale is already installed
        result = subprocess.run(['which', 'tailscale'], capture_output=True)
        
        if result.returncode != 0:
            print("Installing Tailscale...")
            # Install Tailscale
            subprocess.run(
                ['curl', '-fsSL', 'https://tailscale.com/install.sh'],
                capture_output=True,
                check=True
            )
            subprocess.run(
                ['sh', '-c', 'curl -fsSL https://tailscale.com/install.sh | sh'],
                capture_output=True,
                timeout=120
            )
        
        # If auth key provided, authenticate
        if auth_key:
            cmd = ['tailscale', 'up', f'--authkey={auth_key}']
            if hostname:
                cmd.append(f'--hostname={hostname}')
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print(f"✓ Tailscale authenticated with hostname: {hostname}")
                return True
            else:
                print(f"✗ Tailscale auth failed: {result.stderr}")
                return False
        
        return True
    except Exception as e:
        print(f"✗ Tailscale install error: {str(e)}")
        return False

def get_tailscale_status():
    """Get Tailscale connection status"""
    try:
        result = subprocess.run(
            ['tailscale', 'status', '--json'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            import json
            return json.loads(result.stdout)
        return None
    except:
        return None

def check_wifi_state():
    """Check if system is in WiFi hotspot mode"""
    if WIFI_STATE_FILE.exists():
        return WIFI_STATE_FILE.read_text().strip()
    return "unknown"

def scan_wifi_networks():
    """Scan for available WiFi networks"""
    try:
        # Use nmcli to scan for networks
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY', 'dev', 'wifi', 'list'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            networks = []
            seen_ssids = set()
            
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split(':')
                    if len(parts) >= 3:
                        ssid = parts[0].strip()
                        signal = parts[1].strip()
                        security = parts[2].strip()
                        
                        # Skip empty SSIDs and duplicates
                        if ssid and ssid not in seen_ssids:
                            seen_ssids.add(ssid)
                            
                            # Parse signal strength
                            try:
                                signal_int = int(signal)
                            except:
                                signal_int = 0
                            
                            # Determine security type
                            if not security or security == '--':
                                security_type = 'Open'
                            else:
                                security_type = 'Secured'
                            
                            networks.append({
                                'ssid': ssid,
                                'signal': signal_int,
                                'security': security_type
                            })
            
            # Sort by signal strength
            networks.sort(key=lambda x: x['signal'], reverse=True)
            return networks
        
        return []
    except Exception as e:
        print(f"WiFi scan error: {str(e)}")
        return []

# ============================================================================
# ROUTES - Main Pages
# ============================================================================

@app.route('/')
def index():
    """Home page with smart redirect"""
    
    # Check if we're in WiFi hotspot mode
    wifi_state = check_wifi_state()
    if wifi_state == "hotspot":
        return redirect(url_for('wifi_portal'))
    
    env = read_env()
    
    # Check if SDR is configured (either READSB_DEVICE or any SDR_X variable)
    sdr_configured = False
    if 'READSB_DEVICE' in env and env['READSB_DEVICE']:
        sdr_configured = True
    # Also check for SDR_0, SDR_1, etc.
    for key in env:
        if key.startswith('SDR_') and env[key]:
            sdr_configured = True
            break
    
    if not sdr_configured:
        return redirect(url_for('setup_sdr'))
    
    # Check if location is configured
    lat = env.get('FEEDER_LAT', '0.0')
    try:
        if float(lat) == 0.0:
            return redirect(url_for('setup'))
    except:
        return redirect(url_for('setup'))
    
    # Everything configured, show dashboard
    return redirect(url_for('dashboard'))

@app.route('/wifi-portal')
def wifi_portal():
    """WiFi captive portal for hotspot mode"""
    return render_template('wifi-portal.html')

@app.route('/setup/sdr')
def setup_sdr():
    """SDR Configuration Wizard - Step 1"""
    return render_template('setup-sdr.html')

@app.route('/setup')
def setup():
    """Main Setup Wizard - Steps 2-4 (Location, Tailscale, Aggregators)"""
    env = read_env()
    return render_template('setup.html', config=env)

@app.route('/loading')
def loading():
    """Loading screen shown during service startup"""
    return render_template('loading.html')

@app.route('/dashboard')
def dashboard():
    """Main dashboard - system status"""
    env = read_env()
    docker_status = get_docker_status()
    tailscale_status = get_tailscale_status()
    
    return render_template('dashboard.html', config=env, docker_status=docker_status, tailscale_status=tailscale_status)

@app.route('/settings')
def settings():
    """Settings page - modify configuration"""
    env = read_env()
    tailscale_status = get_tailscale_status()
    return render_template('settings.html', config=env, tailscale_status=tailscale_status)

# ============================================================================
# API ROUTES - SDR Configuration
# ============================================================================

@app.route('/api/sdr/detect', methods=['GET'])
def api_sdr_detect():
    """Detect RTL-SDR devices using rtl_test"""
    try:
        result = subprocess.run(
            ['rtl_test', '-t'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        devices = []
        output = result.stdout + result.stderr
        
        # Parse rtl_test output
        # Looking for lines like: "Found 2 device(s):" and device details
        for line in output.split('\n'):
            # Match device lines: "  0:  Realtek, RTL2838UHIDIR, SN: 00000001"
            match = re.match(r'\s*(\d+):\s+(.+?)(?:,\s*SN:\s*(\S+))?$', line)
            if match:
                device_id = int(match.group(1))
                device_info = match.group(2).strip()
                serial = match.group(3) if match.group(3) else f"Device{device_id}"
                
                devices.append({
                    'id': device_id,
                    'info': device_info,
                    'serial': serial
                })
        
        if devices:
            return jsonify({'success': True, 'devices': devices})
        else:
            return jsonify({'success': False, 'message': 'No RTL-SDR devices detected'})
    
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'message': 'Device detection timed out'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/sdr/configure', methods=['POST'])
def api_sdr_configure():
    """Save SDR configuration"""
    try:
        data = request.json
        devices = data.get('devices', [])
        
        if not devices:
            return jsonify({'success': False, 'message': 'No devices configured'})
        
        env = read_env()
        
        # Clear existing SDR configuration
        keys_to_remove = [k for k in env.keys() if k.startswith('SDR_') or k.startswith('READSB_')]
        for key in keys_to_remove:
            del env[key]
        
        # Save new SDR configuration
        for idx, device in enumerate(devices):
            device_id = device.get('id')
            use_for = device.get('useFor')  # NOTE: Changed from 'use_for' to 'useFor'
            gain = device.get('gain', 'autogain')
            biastee = device.get('biastee', False)
            
            if use_for:
                freq = '1090' if use_for == '1090' else '978'
                env[f'SDR_{idx}'] = f"{freq},{gain},{str(biastee).lower()}"
                
                # Set READSB variables for first 1090 device
                if use_for == '1090' and 'READSB_DEVICE' not in env:
                    env['READSB_DEVICE'] = str(device_id)
                    env['READSB_GAIN'] = gain
                    env['READSB_ENABLE_BIASTEE'] = 'ON' if biastee else 'OFF'
        
        write_env(env)
        return jsonify({'success': True, 'message': 'SDR configuration saved'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# ============================================================================
# API ROUTES - Configuration Management
# ============================================================================

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    return jsonify(read_env())

@app.route('/api/config', methods=['POST'])
def save_config():
    """Save configuration from wizard"""
    try:
        data = request.json
        env = read_env()
        
        # Update all provided values
        for key, value in data.items():
            # Protect TAKNET-PS server settings from modification
            if key not in TAK_PROTECTED_SETTINGS:
                env[key] = str(value)
        
        # Ensure TAKNET-PS protected settings are always present
        for key, value in TAK_PROTECTED_SETTINGS.items():
            env[key] = value
        
        # Force TAKNET-PS to always be enabled
        env['TAKNET_PS_ENABLED'] = 'true'
        env['TAKNET_PS_MLAT_ENABLED'] = 'true'
        env['TAKNET_PS_MLAT_PORT'] = '30105'
        
        write_env(env)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ============================================================================
# API ROUTES - Tailscale Management
# ============================================================================

@app.route('/api/tailscale/install', methods=['POST'])
def api_install_tailscale():
    """Install and configure Tailscale"""
    try:
        data = request.json
        auth_key = data.get('authKey')
        hostname = data.get('hostname', 'taknet-ps-adsb')
        
        if install_tailscale(auth_key, hostname):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Tailscale installation failed'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/tailscale/status', methods=['GET'])
def api_tailscale_status():
    """Get Tailscale status"""
    status = get_tailscale_status()
    if status:
        return jsonify({'success': True, 'status': status})
    return jsonify({'success': False, 'message': 'Tailscale not available'})

# ============================================================================
# API ROUTES - Service Management
# ============================================================================

@app.route('/api/service/restart', methods=['POST'])
def api_restart_service():
    """Restart ultrafeeder service"""
    try:
        # First rebuild config
        if not rebuild_config():
            return jsonify({
                'success': False, 
                'message': 'Configuration rebuild failed'
            })
        
        # Then restart service
        if restart_service():
            return jsonify({'success': True})
        else:
            return jsonify({
                'success': False,
                'message': 'Service restart failed - check logs'
            })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/status', methods=['GET'])
def api_status():
    """Get overall system status"""
    env = read_env()
    docker_status = get_docker_status()
    
    # Determine primary feed status
    feeds_active = []
    if 'ultrafeeder' in docker_status:
        feeds_active.append('TAKNET-PS')
        
        # Check if other feeds are enabled
        if env.get('FR24_ENABLED') == 'true' and env.get('FR24_SHARING_KEY'):
            feeds_active.append('FlightRadar24')
        if env.get('ADSBX_ENABLED') == 'true' and env.get('ADSBX_UUID'):
            feeds_active.append('ADS-B Exchange')
        if env.get('AIRPLANESLIVE_ENABLED') == 'true' and env.get('AIRPLANESLIVE_UUID'):
            feeds_active.append('Airplanes.Live')
    
    return jsonify({
        'ultrafeeder_running': 'ultrafeeder' in docker_status,
        'fr24_running': 'fr24' in docker_status,
        'feeds_active': feeds_active,
        'docker_status': docker_status
    })

@app.route('/api/docker/status', methods=['GET'])
def api_docker_status():
    """Get Docker container status"""
    return jsonify(get_docker_status())

# ============================================================================
# API ROUTES - WiFi Portal
# ============================================================================

@app.route('/api/wifi/scan', methods=['GET'])
def api_wifi_scan():
    """Scan for available WiFi networks"""
    try:
        networks = scan_wifi_networks()
        return jsonify({'success': True, 'networks': networks})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/wifi/connect', methods=['POST'])
def api_wifi_connect():
    """Save WiFi credentials and trigger connection attempt"""
    try:
        data = request.json
        ssid = data.get('ssid')
        password = data.get('password', '')
        
        if not ssid:
            return jsonify({'success': False, 'message': 'SSID required'})
        
        # Save credentials to file
        WIFI_CREDS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(WIFI_CREDS_FILE, 'w') as f:
            f.write(f'WIFI_SSID="{ssid}"\n')
            f.write(f'WIFI_PASSWORD="{password}"\n')
        
        # Trigger connection attempt (this will reboot the device)
        subprocess.Popen(['/opt/adsb/scripts/wifi-manager.sh', 'connect'])
        
        return jsonify({'success': True, 'message': 'Connecting to network...'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/wifi/state', methods=['GET'])
def api_wifi_state():
    """Get current WiFi state"""
    state = check_wifi_state()
    return jsonify({'state': state})

# ============================================================================
# Captive Portal Detection (for iOS/Android)
# ============================================================================

@app.route('/generate_204')
@app.route('/gen_204')
@app.route('/ncsi.txt')
@app.route('/connecttest.txt')
def captive_portal_detect():
    """Captive portal detection endpoints"""
    wifi_state = check_wifi_state()
    if wifi_state == "hotspot":
        return redirect(url_for('wifi_portal'))
    return "OK", 204

# ============================================================================
# Run Flask App
# ============================================================================

if __name__ == '__main__':
    # Ensure config directory exists
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Run on all interfaces
    app.run(host='0.0.0.0', port=5000, debug=False)
