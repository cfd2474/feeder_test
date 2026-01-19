#!/usr/bin/env python3
"""
TAK-ADSB-Feeder Web Interface v2.1
Flask app with TAK Server protection
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import subprocess
import os
from pathlib import Path

app = Flask(__name__)

ENV_FILE = Path("/opt/adsb/config/.env")
CONFIG_BUILDER = "/opt/adsb/scripts/config_builder.py"

# TAK Server hardcoded defaults - NEVER override these from user input
TAK_DEFAULTS = {
    'TAK_ENABLED': 'true',
    'TAK_SERVER_HOST_PRIMARY': '100.117.34.88',
    'TAK_SERVER_HOST_FALLBACK': '104.225.219.254',
    'TAK_SERVER_PORT': '30004',
    'TAK_CONNECTION_MODE': 'auto'
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
    try:
        subprocess.run(['systemctl', 'restart', 'ultrafeeder'], timeout=10)
        return True
    except:
        return False

def rebuild_config():
    """Run config_builder.py"""
    try:
        subprocess.run(['python3', CONFIG_BUILDER], timeout=5)
        return True
    except:
        return False

# Routes
@app.route('/')
def index():
    """Main page - check if configured"""
    env = read_env()
    
    # Check if basic config exists
    if env.get('FEEDER_LAT', '0.0') == '0.0':
        return redirect(url_for('setup'))
    
    return redirect(url_for('dashboard'))

@app.route('/setup')
def setup():
    """Setup wizard"""
    env = read_env()
    return render_template('setup.html', config=env)

@app.route('/dashboard')
def dashboard():
    """Status dashboard"""
    env = read_env()
    docker_status = get_docker_status()
    return render_template('dashboard.html', config=env, docker=docker_status)

@app.route('/settings')
def settings():
    """Settings page"""
    env = read_env()
    return render_template('settings.html', config=env)

# API Endpoints
@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    return jsonify(read_env())

@app.route('/api/config', methods=['POST'])
def save_config():
    """
    Save configuration
    CRITICAL: Protect TAK Server settings from user override
    """
    try:
        data = request.json
        env = read_env()
        
        # PROTECT TAK SETTINGS - Always use hardcoded defaults
        # Remove any TAK parameters from user input
        tak_keys = ['TAK_ENABLED', 'TAK_SERVER_HOST', 'TAK_SERVER_HOST_PRIMARY', 
                    'TAK_SERVER_HOST_FALLBACK', 'TAK_SERVER_PORT', 'TAK_CONNECTION_MODE']
        
        for key in tak_keys:
            if key in data:
                del data[key]  # Remove user-provided TAK settings
        
        # Update env with user data (TAK excluded)
        for key, value in data.items():
            env[key] = str(value)
        
        # Ensure TAK defaults are always present and correct
        for key, value in TAK_DEFAULTS.items():
            env[key] = value
        
        # Write to file
        write_env(env)
        
        # Rebuild ULTRAFEEDER_CONFIG
        rebuild_config()
        
        return jsonify({'success': True, 'message': 'Configuration saved'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/service/restart', methods=['POST'])
def api_restart_service():
    """Restart ultrafeeder service"""
    try:
        # Rebuild config first
        rebuild_config()
        
        # Restart service
        if restart_service():
            return jsonify({'success': True, 'message': 'Service restarting'})
        else:
            return jsonify({'success': False, 'message': 'Failed to restart'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

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

if __name__ == '__main__':
    # Run on all interfaces, port 5000
    app.run(host='0.0.0.0', port=5000, debug=False)
