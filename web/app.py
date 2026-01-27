#!/usr/bin/env python3
"""
TAKNET-PS-ADSB-Feeder Web Interface v2.1
Flask app with Tailscale hostname management
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import subprocess
import os
from pathlib import Path

app = Flask(__name__)

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
            timeout=30,  # Increased from 10 to 30 seconds for docker compose
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
        print(f"✗ Restart exception: {e}")
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
        # Check if already installed
        check_result = subprocess.run(['which', 'tailscale'], 
                                     capture_output=True, timeout=5)
        
        if check_result.returncode != 0:
            # Install Tailscale
            install_cmd = 'curl -fsSL https://tailscale.com/install.sh | sh'
            subprocess.run(install_cmd, shell=True, timeout=120)
        
        # If auth key provided, re-authenticate
        if auth_key:
            # Down first to clear previous connection
            subprocess.run(['tailscale', 'down'], timeout=10)
            
            # Build up command with optional hostname
            cmd = ['tailscale', 'up', '--authkey', auth_key]
            
            if hostname:
                cmd.extend(['--hostname', hostname])
            
            # Up with new key and hostname
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return {'success': False, 'message': f'Authentication failed: {result.stderr}'}
        else:
            # Just start Tailscale
            subprocess.run(['tailscale', 'up'], timeout=30)
        
        return {'success': True, 'message': 'Tailscale configured successfully'}
        
    except subprocess.TimeoutExpired:
        return {'success': False, 'message': 'Installation timed out'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def get_tailscale_status():
    """Get Tailscale connection status"""
    try:
        result = subprocess.run(['tailscale', 'status'], 
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
    return render_template('dashboard.html', config=env, docker=docker_status)

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
    
    return jsonify({
        'docker': docker_status,
        'feeds': feeds,
        'configured': env.get('FEEDER_LAT', '0.0') != '0.0'
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
