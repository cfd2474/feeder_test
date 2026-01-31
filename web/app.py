#!/usr/bin/env python3
"""
TAKNET-PS-ADSB-Feeder Web Interface v2.1
Flask app with Tailscale hostname management
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import subprocess
import os
from pathlib import Path
import json
import threading
import time

app = Flask(__name__)

# Version information
VERSION = "2.19.0"

# Global progress tracking
service_progress = {
    'service': 'idle',
    'progress': 0,
    'total': 0,
    'status': 'Ready',
    'details': ''
}
progress_lock = threading.Lock()

def update_progress(service, progress, total=100, status='', details=''):
    """Update global progress state"""
    global service_progress
    with progress_lock:
        service_progress = {
            'service': service,
            'progress': progress,
            'total': total,
            'status': status,
            'details': details
        }

def reset_progress():
    """Reset progress to idle"""
    update_progress('idle', 0, 100, 'Ready', '')

ENV_FILE = Path("/opt/adsb/config/.env")
CONFIG_BUILDER = "/opt/adsb/scripts/config_builder.py"

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

def get_taknet_connection_status(env_vars):
    """
    Get current TAKNET-PS connection status by running Tailscale detection
    Returns dict with selected_host, connection_type, etc.
    """
    import sys
    sys.path.insert(0, '/opt/adsb/scripts')
    try:
        from config_builder import check_tailscale_running, select_taknet_host
        
        if env_vars.get('TAKNET_PS_ENABLED', 'true').lower() != 'true':
            return None
        
        # Run the same detection logic as config_builder.py
        selected_host, connection_type = select_taknet_host(env_vars)
        
        if not selected_host:
            return None
        
        return {
            'enabled': True,
            'selected_host': selected_host,
            'connection_type': connection_type,
            'port': env_vars.get('TAKNET_PS_SERVER_PORT', '30004'),
            'mlat_port': env_vars.get('TAKNET_PS_MLAT_PORT', '30105'),
            'mlat_enabled': env_vars.get('TAKNET_PS_MLAT_ENABLED', 'true').lower() == 'true'
        }
    except Exception as e:
        print(f"Error getting TAKNET-PS status: {e}")
        return None

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

def get_docker_status_all():
    """Get Docker container status for ALL containers (running and stopped)"""
    try:
        result = subprocess.run(
            ['docker', 'ps', '-a', '--format', '{{.Names}}\t{{.Status}}'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            containers = {}
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('\t', 1)
                    if len(parts) == 2:
                        name, status = parts
                        containers[name] = status
            return containers
        return {}
    except:
        return {}

def container_exists(container_name):
    """Check if a Docker container exists (running or stopped)"""
    try:
        result = subprocess.run(
            ['docker', 'ps', '-a', '--format', '{{.Names}}'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            containers = result.stdout.strip().split('\n')
            return container_name in containers
        return False
    except:
        return False

# Cache for service states to prevent flickering
service_state_cache = {}
service_state_cache_time = {}
SERVICE_STATE_CACHE_DURATION = 2  # seconds

def get_service_state(service_name):
    """Get detailed service state: downloading, starting, running, stopped, or not_installed"""
    global service_progress, service_state_cache, service_state_cache_time
    
    # Return cached state if still valid
    current_time = time.time()
    if service_name in service_state_cache:
        cache_age = current_time - service_state_cache_time.get(service_name, 0)
        if cache_age < SERVICE_STATE_CACHE_DURATION:
            return service_state_cache[service_name]
    
    # Check if currently being downloaded/started (tracked by progress system)
    with progress_lock:
        if service_progress['service'] == service_name:
            if service_progress['progress'] < 100:
                state = 'downloading' if service_progress['progress'] < 85 else 'starting'
                service_state_cache[service_name] = state
                service_state_cache_time[service_name] = current_time
                return state
    
    # Single atomic Docker check - get ALL container statuses at once
    docker_status_all = get_docker_status_all()
    container_name = service_name
    
    # Check if container exists and get its status
    if container_name in docker_status_all:
        status = docker_status_all[container_name]
        
        # Parse Docker status string
        if 'Up' in status:
            state = 'running'
        elif 'Restarting' in status:
            state = 'starting'
        elif 'Exited' in status or 'Created' in status:
            state = 'stopped'
        else:
            # Unknown status - default to stopped
            state = 'stopped'
    else:
        # Container doesn't exist
        state = 'not_installed'
    
    # Cache the result
    service_state_cache[service_name] = state
    service_state_cache_time[service_name] = current_time
    
    return state

def monitor_docker_progress(service_name='ultrafeeder'):
    """Monitor Docker pull progress in background thread for any service"""
    try:
        update_progress(service_name, 10, 100, 'Pulling image...', 'Starting')
        
        # For FR24 (Docker container), monitor container creation and startup
        # For other services (systemd), watch journalctl
        if service_name == 'fr24':
            # FR24 is a Docker container managed by docker compose
            # Monitor by polling container state
            start_time = time.time()
            max_wait = 180  # 3 minutes max
            
            update_progress(service_name, 20, 100, 'Initiating download...', 'Pulling image')
            
            while time.time() - start_time < max_wait:
                try:
                    # Check if container exists
                    result = subprocess.run(
                        ['docker', 'ps', '-a', '--filter', 'name=^fr24$', '--format', '{{.Status}}'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    
                    if result.returncode == 0 and result.stdout.strip():
                        status = result.stdout.strip()
                        
                        if 'Up' in status:
                            # Container is running!
                            update_progress(service_name, 100, 100, 'Running', 'Complete')
                            break
                        elif 'Created' in status or 'Exited' in status:
                            # Container exists but not running yet
                            update_progress(service_name, 85, 100, 'Starting container...', 'Almost done')
                        else:
                            # Container exists in some other state
                            update_progress(service_name, 70, 100, 'Initializing...', 'Starting')
                    else:
                        # Container doesn't exist yet - image is still pulling
                        elapsed = time.time() - start_time
                        # Gradual progress from 20% to 80% over 2 minutes
                        progress = min(80, 20 + int((elapsed / 120) * 60))
                        update_progress(service_name, progress, 100, 'Downloading image...', f'{int(elapsed)}s elapsed')
                    
                    time.sleep(2)  # Poll every 2 seconds
                    
                except Exception as e:
                    print(f"FR24 monitoring error: {e}")
                    time.sleep(2)
            
            # If we timed out, set to a reasonable state
            if time.time() - start_time >= max_wait:
                update_progress(service_name, 90, 100, 'Starting...', 'Please wait')
            
        else:
            # Monitor journalctl for systemd services (ultrafeeder)
            process = subprocess.Popen(
                ['journalctl', '-u', service_name, '-f', '--since', 'now'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            start_time = time.time()
            max_wait = 180  # 3 minutes max
            
            while time.time() - start_time < max_wait:
                line = process.stdout.readline()
                if not line:
                    time.sleep(0.5)
                    continue
                
                # Parse Docker pull progress
                # Example: "Pulling fs layer" / "Downloading" / "Extracting"
                if 'Pulling fs layer' in line or 'Waiting' in line:
                    update_progress(service_name, 20, 100, 'Pulling layers...', 'Initializing')
                elif 'Downloading' in line:
                    # Try to extract download progress if available
                    # Format: "Downloading [==>  ] 25.5MB/100MB"
                    try:
                        if 'MB' in line:
                            parts = line.split('/')
                            if len(parts) >= 2:
                                # Extract downloaded and total
                                downloaded_str = parts[0].split()[-1].replace('MB', '')
                                total_str = parts[1].split()[0].replace('MB', '')
                                downloaded = float(downloaded_str)
                                total = float(total_str)
                                percent = int((downloaded / total) * 100) if total > 0 else 30
                                percent = min(80, max(20, percent))  # Clamp between 20-80%
                                update_progress(service_name, percent, 100, 'Downloading...', f'{downloaded:.1f}MB / {total:.1f}MB')
                            else:
                                update_progress(service_name, 40, 100, 'Downloading...', 'In progress')
                        else:
                            update_progress(service_name, 40, 100, 'Downloading...', 'In progress')
                    except:
                        update_progress(service_name, 40, 100, 'Downloading...', 'In progress')
                elif 'Extracting' in line or 'Pull complete' in line:
                    update_progress(service_name, 85, 100, 'Extracting...', 'Almost done')
                elif 'Started' in line or 'Running' in line:
                    update_progress(service_name, 100, 100, 'Running', 'Complete')
                    break
                
                # Fallback: gradual increase over time if no specific messages
                elapsed = time.time() - start_time
                if elapsed > 5:
                    fallback_percent = min(80, 15 + int((elapsed / max_wait) * 65))
                    if service_progress['progress'] < fallback_percent:
                        update_progress(service_name, fallback_percent, 100, 'Downloading...', f'{int(elapsed)}s elapsed')
            
            process.terminate()
        
    except Exception as e:
        print(f"Progress monitoring error for {service_name}: {e}")
        # Fallback to time-based estimation
        for i in range(10, 90, 10):
            update_progress(service_name, i, 100, 'Starting...', f'{i}%')
            time.sleep(3)

def restart_service():
    """Restart ultrafeeder service - non-blocking, returns immediately"""
    import time
    try:
        # Brief delay to prevent rapid-fire restarts
        time.sleep(2)
        
        # Reset progress before starting
        reset_progress()
        
        # Start progress monitoring in background thread
        monitor_thread = threading.Thread(target=monitor_docker_progress, args=('ultrafeeder',), daemon=True)
        monitor_thread.start()
        
        # Start restart in background (non-blocking)
        # The systemctl command will continue running, but we return immediately
        # The loading page will poll /api/service/ready to check when it's actually up
        subprocess.Popen(
            ['systemctl', 'restart', 'ultrafeeder'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print("✓ Ultrafeeder restart initiated (non-blocking)")
        return True
        
    except Exception as e:
        print(f"✗ Failed to initiate restart: {e}")
        return False

def rebuild_config():
    """Run config_builder.py"""
    try:
        result = subprocess.run(
            ['python3', CONFIG_BUILDER],
            timeout=10,
            capture_output=True,
            text=True,
            cwd='/opt/adsb'
        )
        if result.returncode == 0:
            print("✓ Config rebuilt successfully")
            print(result.stdout)
            return True
        else:
            print(f"✗ Config rebuild failed (code {result.returncode})")
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
            return False
    except subprocess.TimeoutExpired:
        print("✗ Config rebuild timed out after 10 seconds")
        return False
    except Exception as e:
        print(f"✗ Config rebuild exception: {e}")
        return False

def install_tailscale(auth_key=None, hostname=None):
    """Install and configure Tailscale with optional hostname"""
    try:
        # Use full path to tailscale binary
        tailscale_bin = '/usr/bin/tailscale'
        
        # Check if already installed
        check_result = subprocess.run(['which', 'tailscale'], 
                                     capture_output=True, timeout=5)
        
        was_just_installed = False
        if check_result.returncode != 0:
            # Install Tailscale
            print("⚙ Installing Tailscale...")
            install_cmd = 'curl -fsSL https://tailscale.com/install.sh | sh'
            install_result = subprocess.run(install_cmd, shell=True, timeout=120, 
                                          capture_output=True, text=True)
            
            if install_result.returncode != 0:
                return {'success': False, 'message': f'Installation failed: {install_result.stderr}'}
            
            # Verify installation succeeded by checking if binary exists
            if not os.path.exists(tailscale_bin):
                return {'success': False, 'message': 'Installation completed but tailscale binary not found'}
            
            print("✓ Tailscale installed successfully")
            was_just_installed = True
        
        # If auth key provided, authenticate
        if auth_key:
            # Only run 'down' if Tailscale was already installed (not if we just installed it)
            if not was_just_installed:
                print("⚙ Clearing previous Tailscale connection...")
                try:
                    subprocess.run([tailscale_bin, 'down'], timeout=10, capture_output=True)
                except Exception as e:
                    print(f"⚠ Warning: Could not run 'tailscale down': {e}")
            
            # Build up command with optional hostname
            cmd = [tailscale_bin, 'up', '--authkey', auth_key]
            
            if hostname:
                cmd.extend(['--hostname', hostname])
            
            print(f"⚙ Connecting to Tailscale network as: {hostname if hostname else 'default hostname'}...")
            # Up with new key and hostname
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return {'success': False, 'message': f'Authentication failed: {result.stderr}'}
            
            print("✓ Connected to Tailscale network")
        else:
            # Just start Tailscale (no auth key provided)
            print("⚙ Starting Tailscale...")
            result = subprocess.run([tailscale_bin, 'up'], timeout=30, 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                return {'success': False, 'message': f'Failed to start Tailscale: {result.stderr}'}
        
        # SECURITY: Automatically configure SSH for Tailscale-only access
        # Run the configure-ssh-tailscale.sh script
        try:
            ssh_config_script = '/opt/adsb/configure-ssh-tailscale.sh'
            if os.path.exists(ssh_config_script):
                subprocess.run(['bash', ssh_config_script], 
                             capture_output=True, 
                             timeout=10,
                             check=False)  # Don't fail if SSH config has issues
                print("✓ SSH configured for Tailscale-only access")
        except Exception as e:
            print(f"⚠️ SSH configuration failed (non-critical): {e}")
        
        return {'success': True, 'message': 'Tailscale configured successfully'}
        
    except subprocess.TimeoutExpired:
        return {'success': False, 'message': 'Installation timed out'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def get_tailscale_status():
    """Get Tailscale connection status"""
    try:
        tailscale_bin = '/usr/bin/tailscale'
        result = subprocess.run([tailscale_bin, 'status'], 
                               capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            return {'success': True, 'status': result.stdout}
        else:
            return {'success': False, 'status': 'Tailscale not running'}
            
    except FileNotFoundError:
        return {'success': False, 'status': 'Tailscale not installed'}
    except Exception as e:
        return {'success': False, 'status': str(e)}

# Routes
@app.route('/')
def index():
    """Main page - check if configured"""
    env = read_env()
    
    # ALWAYS check SDR first (even on fresh install)
    # If no SDR device configured, go to SDR wizard
    sdr_configured = False
    if env.get('READSB_DEVICE'):
        sdr_configured = True
    else:
        # Check if any SDR_X entries exist
        for key in env.keys():
            if key.startswith('SDR_'):
                sdr_configured = True
                break
    
    if not sdr_configured:
        return redirect(url_for('setup_sdr'))
    
    # Then check if location is configured
    # Default env has FEEDER_LAT=0.0, so check if it's still default
    if env.get('FEEDER_LAT', '0.0') == '0.0' or env.get('FEEDER_LAT', '0') == '0':
        return redirect(url_for('setup'))
    
    # Everything configured, go to dashboard
    return redirect(url_for('dashboard'))

@app.route('/setup/sdr')
def setup_sdr():
    """Setup wizard - Step 1: SDR Configuration"""
    return render_template('setup-sdr.html')

@app.route('/setup')
def setup():
    """Setup wizard - Step 2: Location Configuration"""
    env = read_env()
    return render_template('setup.html', config=env)

@app.route('/loading')
def loading():
    """Loading page with real-time status"""
    return render_template('loading.html')

@app.route('/dashboard')
def dashboard():
    """Status dashboard"""
    env = read_env()
    docker_status = get_docker_status()
    taknet_status = get_taknet_connection_status(env)
    return render_template('dashboard.html', config=env, docker=docker_status, version=VERSION, taknet_status=taknet_status)

@app.route('/logs')
def logs():
    """Logs page (placeholder)"""
    return render_template('logs.html')

@app.route('/settings')
def settings():
    """Settings page"""
    env = read_env()
    return render_template('settings.html', config=env)

# API Endpoints

# SDR Configuration APIs
@app.route('/api/sdr/detect', methods=['GET'])
def api_sdr_detect():
    """Detect connected SDR devices"""
    import re
    try:
        # Run rtl_test to detect devices
        result = subprocess.run(
            ['rtl_test', '-t'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        output = result.stderr + result.stdout
        devices = []
        
        # Parse output
        device_pattern = r'(\d+):\s+([^,]+),\s+([^,]+),\s+SN:\s+(\S+)'
        matches = re.findall(device_pattern, output)
        
        for match in matches:
            index, manufacturer, product, serial = match
            device = {
                'index': int(index),
                'type': 'rtlsdr',
                'manufacturer': manufacturer.strip(),
                'product': product.strip(),
                'serial': serial.strip(),
                'useFor': '',  # Default empty
                'gain': 'autogain',  # Default
                'biastee': False  # Default
            }
            
            # Check if already configured
            env = read_env()
            device_key = f'SDR_{index}'
            if device_key in env:
                config = env[device_key].split(',')
                if len(config) >= 3:
                    device['useFor'] = config[0]
                    device['gain'] = config[1]
                    device['biastee'] = config[2].lower() == 'true'
            
            devices.append(device)
        
        return jsonify({'success': True, 'devices': devices})
        
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'devices': [], 'error': 'Detection timed out'}), 500
    except FileNotFoundError:
        return jsonify({'success': False, 'devices': [], 'error': 'rtl_test not found'}), 500
    except Exception as e:
        return jsonify({'success': False, 'devices': [], 'error': str(e)}), 500

@app.route('/api/sdr/configure', methods=['POST'])
def api_sdr_configure():
    """Save SDR configuration"""
    try:
        data = request.json
        devices = data.get('devices', [])
        
        env = read_env()
        
        # Save each configured device
        for device in devices:
            if device.get('useFor'):
                index = device.get('index')
                use_for = device.get('useFor', '')
                gain = device.get('gain', 'autogain')
                biastee = 'true' if device.get('biastee', False) else 'false'
                
                # Store as SDR_0=1090,autogain,false
                env[f'SDR_{index}'] = f"{use_for},{gain},{biastee}"
                
                # Set primary device (first 1090 device found)
                if use_for == '1090' and 'READSB_DEVICE' not in env:
                    env['READSB_DEVICE'] = str(index)
                    env['READSB_GAIN'] = gain
                    if biastee == 'true':
                        env['READSB_ENABLE_BIASTEE'] = 'ON'
        
        write_env(env)
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    return jsonify(read_env())

@app.route('/api/config', methods=['POST'])
def save_config():
    """
    Save configuration
    CRITICAL: User can only toggle TAKNET_PS_ENABLED, cannot change connection details
    NOTE: Tailscale and FR24 setup are handled by their dedicated endpoints/buttons
    """
    try:
        data = request.json
        env = read_env()
        
        # PROTECT TAK CONNECTION SETTINGS
        # User can only change TAKNET_PS_ENABLED (on/off), nothing else
        tak_protected_keys = ['TAKNET_PS_SERVER_HOST', 'TAKNET_PS_SERVER_HOST_PRIMARY', 
                              'TAKNET_PS_SERVER_HOST_FALLBACK', 'TAKNET_PS_SERVER_PORT', 
                              'TAKNET_PS_CONNECTION_MODE']
        
        # Remove any protected TAK settings from user input
        for key in tak_protected_keys:
            if key in data:
                del data[key]
        
        # Update env with user data (protected TAK settings excluded)
        for key, value in data.items():
            env[key] = str(value)
        
        # Force protected TAK connection settings (always these values)
        for key, value in TAK_PROTECTED_SETTINGS.items():
            env[key] = value
        
        # Write to file
        write_env(env)
        
        # Rebuild ULTRAFEEDER_CONFIG
        rebuild_config()
        
        return jsonify({'success': True, 'message': 'Configuration saved'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/tailscale/install', methods=['POST'])
def api_install_tailscale():
    """Install/update Tailscale with optional auth key and hostname"""
    try:
        data = request.json
        auth_key = data.get('auth_key', None)
        hostname = data.get('hostname', None)
        
        result = install_tailscale(auth_key, hostname)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/tailscale/status', methods=['GET'])
def api_tailscale_status():
    """Get Tailscale connection status"""
    try:
        result = get_tailscale_status()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'status': str(e)}), 500

@app.route('/api/fr24/activate', methods=['POST'])
def api_activate_fr24():
    """Activate FR24 service - start container and monitor download"""
    try:
        env = read_env()
        
        # Check if FR24 is enabled and has key
        if env.get('FR24_ENABLED') != 'true':
            return jsonify({'success': False, 'message': 'FR24 is not enabled in configuration'}), 400
        
        if not env.get('FR24_SHARING_KEY', '').strip():
            return jsonify({'success': False, 'message': 'FR24 sharing key is not configured'}), 400
        
        # Rebuild config to update docker-compose.yml
        rebuild_config()
        
        # Start FR24 container using docker compose
        subprocess.Popen(
            ['docker', 'compose', '-f', '/opt/adsb/config/docker-compose.yml', 'up', '-d', 'fr24'],
            cwd='/opt/adsb/config',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Start FR24 progress monitoring in background thread
        monitor_thread = threading.Thread(target=monitor_docker_progress, args=('fr24',), daemon=True)
        monitor_thread.start()
        print("✓ Started FR24 container and download monitoring")
        
        return jsonify({'success': True, 'message': 'FR24 service activation started'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/service/restart', methods=['POST'])
def api_restart_service():
    """Restart ultrafeeder service"""
    try:
        # Rebuild config first
        config_ok = rebuild_config()
        if not config_ok:
            return jsonify({
                'success': False, 
                'message': 'Configuration rebuild failed. Check logs for details.'
            }), 500
        
        # Restart service
        if restart_service():
            return jsonify({'success': True, 'message': 'Service restarting'})
        else:
            return jsonify({
                'success': False, 
                'message': 'Failed to restart ultrafeeder service. Check journalctl -u ultrafeeder for details.'
            }), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'Exception: {str(e)}'}), 500

@app.route('/api/service/ready', methods=['GET'])
def api_service_ready():
    """Check if ultrafeeder container is running and ready"""
    try:
        docker_status = get_docker_status()
        
        # Check if ultrafeeder container exists and is running
        ultrafeeder_running = False
        for container_name, status in docker_status.items():
            if 'ultrafeeder' in container_name.lower():
                # Check if status contains "Up" (Docker shows "Up X seconds/minutes")
                if 'Up' in status:
                    ultrafeeder_running = True
                    break
        
        return jsonify({
            'ready': ultrafeeder_running,
            'containers': docker_status
        })
    except Exception as e:
        return jsonify({
            'ready': False,
            'error': str(e)
        }), 500

@app.route('/api/service/progress', methods=['GET'])
def api_service_progress():
    """Get current service installation progress"""
    global service_progress
    with progress_lock:
        return jsonify(service_progress)

@app.route('/api/status', methods=['GET'])
def api_status():
    """Get system status"""
    docker_status = get_docker_status()
    env = read_env()
    
    # Parse ULTRAFEEDER_CONFIG to show active feeds
    config_str = env.get('ULTRAFEEDER_CONFIG', '')
    feeds = []
    if config_str:
        for part in config_str.split(';'):
            if part.startswith('adsb,'):
                parts = part.split(',')
                if len(parts) >= 2:
                    feeds.append(parts[1])  # hostname
    
    # Get service states
    service_states = {
        'ultrafeeder': get_service_state('ultrafeeder'),
        'fr24': get_service_state('fr24') if env.get('FR24_ENABLED') == 'true' else None,
        'adsbx': get_service_state('adsbx') if env.get('ADSBX_ENABLED') == 'true' else None,
        'adsblol': get_service_state('adsblol') if env.get('ADSBLOL_ENABLED') == 'true' else None
    }
    
    return jsonify({
        'docker': docker_status,
        'feeds': feeds,
        'configured': env.get('FEEDER_LAT', '0.0') != '0.0',
        'service_states': service_states
    })

@app.route('/api/service/<service_name>/state', methods=['GET'])
def api_service_state(service_name):
    """Get state of a specific service"""
    state = get_service_state(service_name)
    return jsonify({
        'service': service_name,
        'state': state
    })

@app.route('/api/network-status', methods=['GET'])
def api_network_status():
    """Get network connectivity status"""
    import socket
    
    def check_internet():
        """Check if internet is accessible"""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except:
            return False
    
    def get_primary_ip():
        """Get primary IP address"""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip
    
    has_internet = check_internet()
    ip_address = get_primary_ip()
    hostname = socket.gethostname()
    
    return jsonify({
        'internet': has_internet,
        'ip_address': ip_address,
        'hostname': hostname
    })

if __name__ == '__main__':
    # Run on all interfaces, port 5000
    app.run(host='0.0.0.0', port=5000, debug=False)
