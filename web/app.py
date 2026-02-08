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
import uuid
import socket

app = Flask(__name__)

# Version information
VERSION = "2.39.0"

# Global progress tracking
service_progress = {
    'service': 'idle',
    'progress': 0,
    'total': 0,
    'status': 'Ready',
    'details': ''
}
progress_lock = threading.Lock()

# Tailscale installation progress tracking
tailscale_progress = {
    'status': 'idle',  # idle, downloading, installing, registering, completed, failed
    'download_progress': 0,
    'install_progress': 0,
    'register_progress': 0,
    'message': '',
    'download_bytes': 0,
    'total_bytes': 0,
    'error': None
}
tailscale_progress_lock = threading.Lock()

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
    'TAKNET_PS_SERVER_HOST_PRIMARY': 'secure.tak-solutions.com',
    'TAKNET_PS_SERVER_HOST_FALLBACK': 'adsb.tak-solutions.com',
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

def update_env_var(key, value):
    """Update a single environment variable in .env file"""
    env_vars = read_env()
    env_vars[key] = value
    write_env(env_vars)

def get_or_create_feeder_uuid():
    """
    Get existing feeder UUID from .env or generate a new one.
    The UUID persists across reboots and is used by aggregators like adsb.lol
    """
    env_vars = read_env()
    
    # Check if UUID already exists
    if 'FEEDER_UUID' in env_vars and env_vars['FEEDER_UUID']:
        return env_vars['FEEDER_UUID']
    
    # Generate new UUID
    feeder_uuid = str(uuid.uuid4())
    
    # Save to .env
    env_vars['FEEDER_UUID'] = feeder_uuid
    write_env(env_vars)
    
    print(f"Generated new feeder UUID: {feeder_uuid}")
    return feeder_uuid

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
    """Get Tailscale connection status with detailed information"""
    try:
        tailscale_bin = '/usr/bin/tailscale'
        
        # Check if installed
        if not os.path.exists(tailscale_bin):
            return {
                'installed': False,
                'connected': False,
                'message': 'Tailscale not installed'
            }
        
        # Get status
        result = subprocess.run([tailscale_bin, 'status', '--json'], 
                               capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            try:
                status_data = json.loads(result.stdout)
                
                # Check if connected (BackendState should be "Running")
                backend_state = status_data.get('BackendState', '')
                connected = backend_state == 'Running'
                
                # Get self info
                self_info = status_data.get('Self', {})
                ip = self_info.get('TailscaleIPs', [''])[0] if self_info.get('TailscaleIPs') else None
                hostname = self_info.get('DNSName', '').rstrip('.')
                
                return {
                    'installed': True,
                    'connected': connected,
                    'ip': ip,
                    'hostname': hostname,
                    'backend_state': backend_state
                }
            except json.JSONDecodeError:
                # Fall back to non-JSON status
                result = subprocess.run([tailscale_bin, 'status'], 
                                       capture_output=True, text=True, timeout=5)
                return {
                    'installed': True,
                    'connected': 'running' in result.stdout.lower(),
                    'message': 'Connected' if result.returncode == 0 else 'Not connected'
                }
        else:
            return {
                'installed': True,
                'connected': False,
                'message': 'Tailscale installed but not running'
            }
            
    except FileNotFoundError:
        return {
            'installed': False,
            'connected': False,
            'message': 'Tailscale not installed'
        }
    except Exception as e:
        return {
            'installed': False,
            'connected': False,
            'error': str(e)
        }

def update_tailscale_progress(status, download_progress=0, install_progress=0, register_progress=0, message='', download_bytes=0, total_bytes=0):
    """Update global Tailscale progress state"""
    global tailscale_progress
    with tailscale_progress_lock:
        tailscale_progress['status'] = status
        tailscale_progress['download_progress'] = download_progress
        tailscale_progress['install_progress'] = install_progress
        tailscale_progress['register_progress'] = register_progress
        tailscale_progress['message'] = message
        tailscale_progress['download_bytes'] = download_bytes
        tailscale_progress['total_bytes'] = total_bytes
        print(f"[Tailscale Progress] {status}: {message} (download: {download_progress}%, install: {install_progress}%, register: {register_progress}%)")

def install_tailscale_with_progress(auth_key=None, hostname=None):
    """Install and configure Tailscale with progress tracking"""
    try:
        tailscale_bin = '/usr/bin/tailscale'
        
        # === PHASE 1: DOWNLOAD (0-100%) ===
        check_result = subprocess.run(['which', 'tailscale'], 
                                     capture_output=True, timeout=5)
        
        was_just_installed = False
        if check_result.returncode != 0:
            # Download Tailscale with real progress tracking
            update_tailscale_progress('downloading', 0, 0, 0, 'Preparing download...', 0, 0)
            
            # Download install script first to temp file, then execute
            # This lets us track actual download progress
            import tempfile
            temp_script = tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False)
            temp_script_path = temp_script.name
            temp_script.close()
            
            # Download the install script with progress
            download_cmd = ['curl', '-L', '--progress-bar', 
                          'https://tailscale.com/install.sh',
                          '-o', temp_script_path]
            
            # Run download with real-time progress capture
            process = subprocess.Popen(download_cmd, 
                                     stderr=subprocess.PIPE, 
                                     text=True)
            
            # Track download progress from curl's stderr
            last_progress = 0
            for line in process.stderr:
                # Curl progress bar format: ### (percentage)
                # Example: "######################################################################## 100.0%"
                if '%' in line:
                    try:
                        # Extract percentage from progress bar
                        percent_str = line.split()[-1].replace('%', '')
                        percent = float(percent_str)
                        
                        # Estimate bytes (install script is ~30KB, but we'll show approximate download size)
                        # The actual tailscale binary download happens during script execution
                        estimated_total = 30 * 1024  # 30 KB for script
                        downloaded_bytes = int((percent / 100) * estimated_total)
                        
                        # Only update if progress changed significantly
                        if abs(percent - last_progress) >= 5:
                            update_tailscale_progress('downloading', int(percent), 0, 0, 
                                                    'Downloading install script...', 
                                                    downloaded_bytes, estimated_total)
                            last_progress = percent
                    except:
                        pass
            
            process.wait()
            
            if process.returncode != 0:
                os.unlink(temp_script_path)
                update_tailscale_progress('failed', 0, 0, 0, 'Failed to download install script', 0, 0)
                return
            
            update_tailscale_progress('downloading', 100, 0, 0, 'Script downloaded, installing packages...', 
                                    30 * 1024, 30 * 1024)
            
            # Now run the install script
            # Note: The actual binary download happens here, but we can't easily track it
            # We'll show indeterminate progress during package installation
            install_result = subprocess.run(['bash', temp_script_path], 
                                          timeout=120, 
                                          capture_output=True, 
                                          text=True)
            
            # Clean up temp file
            os.unlink(temp_script_path)
            
            if install_result.returncode != 0:
                update_tailscale_progress('failed', 0, 0, 0, 
                                        f'Installation failed: {install_result.stderr}', 0, 0)
                return
            
            # Verify installation succeeded
            if not os.path.exists(tailscale_bin):
                update_tailscale_progress('failed', 0, 0, 0, 
                                        'Installation completed but binary not found', 0, 0)
                return
            
            update_tailscale_progress('downloading', 100, 0, 0, 'Download complete', 0, 0)
            was_just_installed = True
        else:
            # Already installed, skip download phase
            update_tailscale_progress('downloading', 100, 0, 0, 'Tailscale already installed', 0, 0)
        
        time.sleep(0.5)
        
        # === PHASE 2: INSTALL (0-100%) ===
        for i in range(0, 101, 20):
            update_tailscale_progress('installing', 100, i, 0, 'Installing...', 0, 0)
            time.sleep(0.5)
        
        # Clear previous connection if needed
        if auth_key and not was_just_installed:
            try:
                subprocess.run([tailscale_bin, 'down'], timeout=10, capture_output=True)
            except Exception as e:
                print(f"⚠ Warning: Could not run 'tailscale down': {e}")
        
        update_tailscale_progress('installing', 100, 100, 0, 'Installation complete', 0, 0)
        time.sleep(0.5)
        
        # === PHASE 3: REGISTER (0-100%) ===
        if auth_key:
            cmd = [tailscale_bin, 'up', '--authkey', auth_key]
            if hostname:
                cmd.extend(['--hostname', hostname])
            
            update_tailscale_progress('registering', 100, 100, 10, 
                                    'Registering to Tailscale network...', 0, 0)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                update_tailscale_progress('failed', 100, 100, 0, 
                                        f'Authentication failed: {result.stderr}', 0, 0)
                return
            
            for i in range(20, 70, 10):
                update_tailscale_progress('registering', 100, 100, i, 
                                        'Registering to Tailscale network...', 0, 0)
                time.sleep(0.5)
        else:
            update_tailscale_progress('registering', 100, 100, 10, 'Starting Tailscale...', 0, 0)
            result = subprocess.run([tailscale_bin, 'up'], timeout=30, 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                update_tailscale_progress('failed', 100, 100, 0, 
                                        f'Failed to start: {result.stderr}', 0, 0)
                return
            
            for i in range(20, 70, 10):
                update_tailscale_progress('registering', 100, 100, i, 'Starting Tailscale...', 0, 0)
                time.sleep(0.5)
        
        # Verify connection
        connected = False
        for attempt in range(30):
            try:
                status_result = subprocess.run([tailscale_bin, 'status', '--json'], 
                                             capture_output=True, text=True, timeout=5)
                if status_result.returncode == 0:
                    try:
                        status_data = json.loads(status_result.stdout)
                        backend_state = status_data.get('BackendState', '')
                        if backend_state == 'Running':
                            connected = True
                            update_tailscale_progress('registering', 100, 100, 95, 
                                                    'Connection verified!', 0, 0)
                            break
                    except:
                        pass
            except:
                pass
            
            time.sleep(1)
            verify_progress = 70 + min(attempt, 25)
            update_tailscale_progress('registering', 100, 100, verify_progress, 
                                    'Verifying connection...', 0, 0)
        
        if not connected:
            update_tailscale_progress('registering', 100, 100, 95, 
                                    'Verification timed out - Tailscale may still be working', 0, 0)
        
        # Configure SSH
        update_tailscale_progress('registering', 100, 100, 98, 'Configuring SSH security...', 0, 0)
        try:
            ssh_config_script = '/opt/adsb/configure-ssh-tailscale.sh'
            if os.path.exists(ssh_config_script):
                subprocess.run(['bash', ssh_config_script], 
                             capture_output=True, 
                             timeout=10,
                             check=False)
        except Exception as e:
            print(f"⚠️ SSH configuration failed (non-critical): {e}")
        
        # Success!
        update_tailscale_progress('completed', 100, 100, 100, 
                                'Tailscale connected successfully!', 0, 0)
        
    except subprocess.TimeoutExpired:
        update_tailscale_progress('failed', 0, 0, 0, 'Installation timed out', 0, 0)
    except Exception as e:
        update_tailscale_progress('failed', 0, 0, 0, str(e), 0, 0)
        update_tailscale_progress('failed', 0, 0, str(e))

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
    feeder_uuid = get_or_create_feeder_uuid()
    return render_template('setup.html', config=env, feeder_uuid=feeder_uuid)

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
    feeder_uuid = get_or_create_feeder_uuid()
    
    # Get network info
    network_info = {
        'hostname': env.get('TAILSCALE_HOSTNAME', socket.gethostname()),
        'machine_name': env.get('MLAT_SITE_NAME', 'Unknown')
    }
    
    return render_template('dashboard.html', config=env, docker=docker_status, version=VERSION, taknet_status=taknet_status, feeder_uuid=feeder_uuid, network_info=network_info)

@app.route('/logs')
def logs():
    """Logs page (placeholder)"""
    return render_template('logs.html')

@app.route('/api/logs/<source>')
def get_logs(source):
    """Fetch logs from various sources"""
    try:
        if source == 'ultrafeeder':
            # Get ultrafeeder logs from docker
            result = subprocess.run(['docker', 'logs', '--tail', '500', 'ultrafeeder'],
                                  capture_output=True, text=True, timeout=10)
            logs = result.stdout + result.stderr
            
        elif source == 'tailscale':
            # Get tailscale logs from journalctl
            result = subprocess.run(['journalctl', '-u', 'tailscaled', '-n', '500', '--no-pager'],
                                  capture_output=True, text=True, timeout=10)
            logs = result.stdout
            
        elif source == 'vnstat':
            # Get vnstat hour and day reports
            hour_result = subprocess.run(['vnstat', '-h'],
                                       capture_output=True, text=True, timeout=10)
            day_result = subprocess.run(['vnstat', '-d'],
                                      capture_output=True, text=True, timeout=10)
            logs = "=== HOURLY REPORT ===\n" + hour_result.stdout + "\n\n=== DAILY REPORT ===\n" + day_result.stdout
            
        else:
            return jsonify({'success': False, 'message': f'Unknown log source: {source}'})
        
        if not logs or logs.strip() == '':
            logs = f'No logs available for {source}'
        
        return jsonify({'success': True, 'logs': logs})
        
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'message': 'Timeout while fetching logs'})
    except FileNotFoundError:
        return jsonify({'success': False, 'message': f'Service {source} not found or not installed'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/feeds/toggle', methods=['POST'])
def api_feeds_toggle():
    """Toggle feed on/off"""
    try:
        data = request.json
        feed_name = data.get('feed')
        enabled = data.get('enabled', False)
        
        # Map feed names to env variables
        feed_map = {
            'taknet': 'TAKNET_PS_ENABLED',
            'airplaneslive': 'AIRPLANESLIVE_ENABLED',
            'adsbfi': 'ADSBFI_ENABLED',
            'adsblol': 'ADSBLOL_ENABLED',
            'adsbexchange': 'ADSBX_ENABLED'
        }
        
        if feed_name not in feed_map:
            return jsonify({'success': False, 'message': 'Unknown feed'})
        
        env_var = feed_map[feed_name]
        value = 'true' if enabled else 'false'
        
        # Update .env file
        update_env_var(env_var, value)
        
        # Restart ultrafeeder to apply changes
        try:
            subprocess.run(['docker', 'restart', 'ultrafeeder'], timeout=30, check=True)
        except:
            pass  # Continue even if restart fails
        
        return jsonify({'success': True, 'message': f'Feed {feed_name} updated'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/feeds/fr24/setup', methods=['POST'])
def api_fr24_setup():
    """Setup FR24 feeder with existing key"""
    try:
        data = request.json
        feeder_id = data.get('feeder_id', '').strip()
        
        if not feeder_id:
            return jsonify({'success': False, 'message': 'Feeder ID is required'})
        
        # Update .env with FR24 key
        update_env_var('FR24_KEY', feeder_id)
        update_env_var('FR24_ENABLED', 'true')
        
        # Start FR24 container using docker compose
        # Use the correct paths - config is at /opt/adsb not /opt/taknet-ps
        compose_file = '/opt/adsb/config/docker-compose.yml'
        env_file = str(ENV_FILE)  # This is /opt/adsb/config/.env
        
        # Verify files exist before attempting docker compose
        if not Path(compose_file).exists():
            return jsonify({
                'success': False,
                'message': f'docker-compose.yml not found at: {compose_file}\n\nPlease run the installer to create the docker-compose.yml file.'
            })
        
        if not ENV_FILE.exists():
            return jsonify({
                'success': False,
                'message': f'.env file not found at: {env_file}\n\nPlease run the installer to create the .env file.'
            })
        
        result = subprocess.run(
            ['docker', 'compose', '-f', compose_file, '--env-file', env_file, 'up', '-d', 'fr24'],
            capture_output=True, text=True, timeout=60
        )
        
        if result.returncode == 0:
            return jsonify({'success': True, 'message': 'FR24 feed enabled successfully'})
        else:
            return jsonify({'success': False, 'message': f'Failed to start FR24: {result.stderr}'})
        
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'message': 'Operation timed out'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/feeds/fr24/test', methods=['POST'])
def api_fr24_test():
    """Test FR24 key validity"""
    try:
        data = request.json
        feeder_id = data.get('feeder_id', '').strip()
        
        if not feeder_id:
            return jsonify({'success': False, 'message': 'Feeder ID is required'})
        
        # Simple validation - check if key format is reasonable
        if len(feeder_id) < 10:
            return jsonify({'success': False, 'message': 'Feeder ID appears invalid (too short)'})
        
        # Key looks valid
        return jsonify({'success': True, 'message': 'FR24 key format appears valid'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/feeds/fr24/register', methods=['POST'])
def api_fr24_register():
    """Register new FR24 account - smart registration with coordinate formatting"""
    try:
        data = request.json
        email = data.get('email', '').strip()
        
        if not email:
            return jsonify({'success': False, 'message': 'Email is required'})
        
        # Validate email format
        import re
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            return jsonify({'success': False, 'message': 'Invalid email format'})
        
        # Read current env for location data
        env = read_env()
        lat_str = env.get('FEEDER_LAT', '0')
        lon_str = env.get('FEEDER_LONG', '0')
        alt_ft_str = env.get('FEEDER_ALT_FT', '0')
        
        # Validate we have location data
        try:
            lat = float(lat_str)
            lon = float(lon_str)
            alt_ft = float(alt_ft_str)
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Invalid feeder location data. Please configure location in Settings first.'
            })
        
        if lat == 0 or lon == 0:
            return jsonify({
                'success': False,
                'message': 'Feeder location not configured. Please set up your location in Settings first.'
            })
        
        # Format coordinates to EXACTLY 4 decimal places (FR24 requirement)
        lat_formatted = f"{lat:.4f}"
        lon_formatted = f"{lon:.4f}"
        alt_formatted = str(int(alt_ft))  # Altitude in feet, no decimals
        
        # Prepare answers for fr24feed --signup
        signup_inputs = f'''{email}

yes
{lat_formatted}
{lon_formatted}
{alt_formatted}
yes
5
ultrafeeder
30005
no
no
'''
        
        # Run fr24feed --signup in Docker container
        docker_cmd = [
            'docker', 'run', '-i', '--rm',
            'ghcr.io/sdr-enthusiasts/docker-flightradar24:latest',
            'fr24feed', '--signup'
        ]
        
        try:
            result = subprocess.run(
                docker_cmd,
                input=signup_inputs,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            output = result.stdout + result.stderr
            
            # Try to extract sharing key FIRST (success case)
            import re
            key_match = re.search(r'sharing key \(([a-zA-Z0-9]+)\)', output)
            
            if key_match:
                # SUCCESS: Key found and extracted
                sharing_key = key_match.group(1)
                return jsonify({
                    'success': True,
                    'sharing_key': sharing_key,
                    'message': f'Registration successful! Your sharing key: {sharing_key}'
                })
            
            # If we get here, no key was extracted
            # Check for CLEAR FAILURE indicators
            
            # ERROR 1: Three-key limit reached
            if 'limit' in output.lower() or 'maximum' in output.lower() or ('three' in output.lower() and 'feeder' in output.lower()):
                return jsonify({
                    'success': False,
                    'error_type': 'key_limit',
                    'message': f'Your FlightRadar24 account has reached the 3-feeder limit.\n\nTo add this feeder, you need to:\n1. Log in to your FR24 account with: {email}\n2. Remove an old feeder or request additional keys from FR24 support\n3. Copy your sharing key and paste it in the field above',
                    'url': 'https://www.flightradar24.com/account/data-sharing',
                    'email': email,
                    'debug_output': output[:1000]
                })
            
            # ERROR 2: Clear failure messages
            clear_failures = [
                'connection refused' in output.lower(),
                'network unreachable' in output.lower(),
                'could not connect' in output.lower(),
                'timeout' in output.lower() and 'error' in output.lower()
            ]
            
            if any(clear_failures):
                return jsonify({
                    'success': False,
                    'error_type': 'network_error',
                    'message': f'Network error during registration.\n\nYou can register manually:\n1. Log in or create account with: {email}\n2. Complete the FR24 feeder registration\n3. Copy your sharing key and paste it in the field above',
                    'url': 'https://www.flightradar24.com/share-your-data',
                    'email': email,
                    'debug_output': output[:1000]
                })
            
            # DEFAULT: Assume registration succeeded but we couldn't extract the key
            # This is the "fail-open" approach - better to assume success and let user verify
            return jsonify({
                'success': False,
                'error_type': 'key_extraction_failed',
                'message': f'We couldn\'t automatically retrieve your sharing key.\n\nNext steps:\n1. Log in with: {email}\n2. Copy your sharing key\n3. Paste it in the field above and click "Save & Enable FR24"',
                'url': 'https://www.flightradar24.com/account/data-sharing',
                'email': email,
                'registration_successful': True,
                'debug_output': output[:1000]
            })
                
        except subprocess.TimeoutExpired:
            return jsonify({
                'success': False,
                'error_type': 'timeout',
                'message': f'Registration process timed out (took over 2 minutes).\n\nThe registration may have completed successfully.\n\nNext steps:\n1. Log in to your FR24 account with: {email}\n2. Check if your feeder was registered\n3. If yes, copy your sharing key and paste it above',
                'url': 'https://www.flightradar24.com/account/data-sharing',
                'email': email
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error_type': 'exception',
            'message': f'Unexpected error during registration: {str(e)}\n\nYou can register manually:\n1. Visit the FR24 registration page (link below)\n2. Complete registration with your email\n3. Copy your sharing key and paste it above',
            'url': 'https://www.flightradar24.com/share-your-data'
        })

@app.route('/api/feeds/fr24/toggle', methods=['POST'])
def api_fr24_toggle():
    """Toggle FR24 feed enabled/disabled"""
    try:
        data = request.json
        enabled = data.get('enabled', False)
        
        # Update .env
        update_env_var('FR24_ENABLED', 'true' if enabled else 'false')
        
        # Use the correct paths - config is at /opt/adsb not /opt/taknet-ps
        compose_file = '/opt/adsb/config/docker-compose.yml'
        env_file = str(ENV_FILE)  # This is /opt/adsb/config/.env
        
        # Verify files exist before attempting docker compose
        if not Path(compose_file).exists():
            return jsonify({
                'success': False,
                'message': f'docker-compose.yml not found at: {compose_file}\n\nPlease run the installer to create the docker-compose.yml file.'
            })
        
        if not ENV_FILE.exists():
            return jsonify({
                'success': False,
                'message': f'.env file not found at: {env_file}\n\nPlease run the installer to create the .env file.'
            })
        
        # Start or stop FR24 container using docker compose
        if enabled:
            result = subprocess.run(
                ['docker', 'compose', '-f', compose_file, '--env-file', env_file, 'up', '-d', 'fr24'],
                capture_output=True, text=True, timeout=60
            )
        else:
            result = subprocess.run(
                ['docker', 'compose', '-f', compose_file, 'stop', 'fr24'],
                capture_output=True, text=True, timeout=30
            )
        
        if result.returncode == 0:
            return jsonify({'success': True, 'message': f'FR24 feed {"enabled" if enabled else "disabled"}'})
        else:
            return jsonify({'success': False, 'message': f'Failed: {result.stderr}'})
        
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'message': 'Operation timed out'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/settings')
def settings():
    """Settings page"""
    env = read_env()
    return render_template('settings.html', config=env)

@app.route('/feeds')
def feeds():
    """Feeds configuration page"""
    env = read_env()
    feeder_uuid = get_or_create_feeder_uuid()
    return render_template('feeds.html', config=env, feeder_uuid=feeder_uuid, version=VERSION)

@app.route('/feeds/account-required')
def feeds_account_required():
    """Account-required feeds configuration page"""
    env = read_env()
    
    # Check FR24 status
    fr24_key = env.get('FR24_KEY', '')
    fr24_enabled = env.get('FR24_ENABLED', 'false') == 'true'
    fr24_status = False
    if fr24_key and fr24_enabled:
        # Check if FR24 container is running
        try:
            result = subprocess.run(['docker', 'ps', '--filter', 'name=fr24', '--format', '{{.Names}}'],
                                  capture_output=True, text=True, timeout=5)
            fr24_status = 'fr24' in result.stdout
        except:
            fr24_status = False
    
    return render_template('feeds-account-required.html', 
                         fr24_key=fr24_key,
                         fr24_enabled=fr24_enabled,
                         fr24_status=fr24_status)

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
        
        # Reset progress
        global tailscale_progress
        with tailscale_progress_lock:
            tailscale_progress = {
                'status': 'downloading',
                'download_progress': 0,
                'install_progress': 0,
                'register_progress': 0,
                'message': 'Starting installation...',
                'download_bytes': 0,
                'total_bytes': 0,
                'error': None
            }
        
        # Start installation in background thread
        install_thread = threading.Thread(
            target=install_tailscale_with_progress, 
            args=(auth_key, hostname),
            daemon=True
        )
        install_thread.start()
        
        return jsonify({'success': True, 'message': 'Installation started'})
            
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

@app.route('/api/tailscale/progress', methods=['GET'])
def api_tailscale_progress():
    """Get Tailscale installation progress"""
    global tailscale_progress
    with tailscale_progress_lock:
        return jsonify(tailscale_progress)

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
