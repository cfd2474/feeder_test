#!/usr/bin/env python3
"""
TAK-ADSB-Feeder Config Builder v2.1
Builds ULTRAFEEDER_CONFIG with TAK Server as hardcoded priority
Supports primary/fallback connection modes
"""

import sys
import socket
from pathlib import Path

def read_env(env_file):
    """Read .env file and return as dict"""
    env_vars = {}
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    return env_vars

def check_host_reachable(host, port, timeout=2):
    """Check if a host:port is reachable"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, int(port)))
        sock.close()
        return result == 0
    except:
        return False

def select_tak_host(env_vars):
    """
    Select TAK Server host based on connection mode and availability
    Returns: (selected_host, connection_type)
    """
    mode = env_vars.get('TAK_CONNECTION_MODE', 'auto').lower()
    primary = env_vars.get('TAK_SERVER_HOST_PRIMARY', '').strip()
    fallback = env_vars.get('TAK_SERVER_HOST_FALLBACK', '').strip()
    port = env_vars.get('TAK_SERVER_PORT', '30004').strip()
    
    # Force modes
    if mode == 'primary' and primary:
        print(f"ℹ TAK: Forced to primary: {primary}")
        return (primary, 'primary-forced')
    
    if mode == 'fallback' and fallback:
        print(f"ℹ TAK: Forced to fallback: {fallback}")
        return (fallback, 'fallback-forced')
    
    # Auto mode - test connectivity
    if mode == 'auto':
        if primary and check_host_reachable(primary, port):
            print(f"✓ TAK: Primary reachable: {primary}")
            return (primary, 'primary-auto')
        elif fallback and check_host_reachable(fallback, port):
            print(f"⚠ TAK: Primary unreachable, using fallback: {fallback}")
            return (fallback, 'fallback-auto')
        elif primary:
            print(f"⚠ TAK: Neither reachable, defaulting to primary: {primary}")
            return (primary, 'primary-default')
    
    # Monitor mode (Phase 2) - use primary, external monitor will handle failover
    if mode == 'monitor' and primary:
        print(f"ℹ TAK: Monitor mode, using primary: {primary}")
        return (primary, 'monitor-mode')
    
    # Fallback to primary if nothing else works
    if primary:
        return (primary, 'primary-fallback')
    elif fallback:
        return (fallback, 'fallback-only')
    
    return (None, 'disabled')

def build_config(env_vars):
    """Build ULTRAFEEDER_CONFIG string with TAK as priority"""
    config_parts = []
    
    # TAK Server - ALWAYS FIRST (Priority Feed)
    if env_vars.get('TAK_ENABLED', 'true').lower() == 'true':
        tak_host, connection_type = select_tak_host(env_vars)
        port = env_vars.get('TAK_SERVER_PORT', '30004').strip()
        mlat_port = env_vars.get('TAK_MLAT_PORT', '30105').strip()
        
        if tak_host:
            # Beast feed
            config_parts.append(f"adsb,{tak_host},{port},beast_reduce_plus_out")
            print(f"✓ TAK Server Beast: {tak_host}:{port} ({connection_type})")
            
            # MLAT feed (if enabled)
            if env_vars.get('TAK_MLAT_ENABLED', 'true').lower() == 'true':
                config_parts.append(f"mlat,{tak_host},{mlat_port},39001")
                print(f"✓ TAK Server MLAT: {tak_host}:{mlat_port}")
            else:
                print("ℹ TAK Server MLAT: Disabled")
        else:
            print("✗ TAK Server: No valid host configuration found")
    else:
        print("ℹ TAK Server: Disabled (not recommended)")
    
    # FlightRadar24
    if env_vars.get('FR24_ENABLED', '').lower() == 'true':
        if env_vars.get('FR24_SHARING_KEY', '').strip():
            config_parts.append("adsb,feed.flightradar24.com,30004,beast_reduce_plus_out")
            config_parts.append("mlat,mlat.flightradar24.com,31090,39000")
            print("✓ FlightRadar24")
    
    # ADS-B Exchange
    if env_vars.get('ADSBX_ENABLED', '').lower() == 'true':
        uuid = env_vars.get('ADSBX_UUID', '').strip()
        if uuid:
            config_parts.append(f"adsb,feed1.adsbexchange.com,30004,beast_reduce_plus_out,uuid={uuid}")
            config_parts.append(f"mlat,feed.adsbexchange.com,31090,39001,uuid={uuid}")
            print("✓ ADS-B Exchange")
    
    # Airplanes.Live
    if env_vars.get('AIRPLANESLIVE_ENABLED', '').lower() == 'true':
        uuid = env_vars.get('AIRPLANESLIVE_UUID', '').strip()
        if uuid:
            config_parts.append(f"adsb,feed.airplanes.live,30004,beast_reduce_plus_out,uuid={uuid}")
            config_parts.append(f"mlat,mlat.airplanes.live,31090,39002,uuid={uuid}")
            print("✓ Airplanes.Live")
    
    # RadarBox
    if env_vars.get('RADARBOX_ENABLED', '').lower() == 'true':
        if env_vars.get('RADARBOX_SHARING_KEY', '').strip():
            config_parts.append("adsb,feed.radarbox.com,30001,beast_reduce_plus_out")
            config_parts.append("mlat,mlat.radarbox.com,31090,39003")
            print("✓ RadarBox")
    
    # PlaneFinder
    if env_vars.get('PLANEFINDER_ENABLED', '').lower() == 'true':
        if env_vars.get('PLANEFINDER_SHARECODE', '').strip():
            config_parts.append("adsb,feed.planefinder.net,30054,beast_reduce_plus_out")
            print("✓ PlaneFinder")
    
    # OpenSky Network
    if env_vars.get('OPENSKYNETWORK_ENABLED', '').lower() == 'true':
        username = env_vars.get('OPENSKYNETWORK_USERNAME', '').strip()
        if username and env_vars.get('OPENSKYNETWORK_SERIAL', '').strip():
            config_parts.append("adsb,feed.opensky-network.org,10004,beast_reduce_plus_out")
            print("✓ OpenSky Network")
    
    return ';'.join(config_parts)

def update_env_file(env_file, config_string):
    """Update ULTRAFEEDER_CONFIG in .env file"""
    lines = []
    updated = False
    
    with open(env_file) as f:
        for line in f:
            if line.strip().startswith('ULTRAFEEDER_CONFIG='):
                lines.append(f'ULTRAFEEDER_CONFIG={config_string}\n')
                updated = True
            else:
                lines.append(line)
    
    if not updated:
        lines.append(f'\nULTRAFEEDER_CONFIG={config_string}\n')
    
    with open(env_file, 'w') as f:
        f.writelines(lines)

def main():
    env_file = Path("/opt/adsb/config/.env")
    
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("TAK-ADSB-Feeder Config Builder v2.1")
    print("Building ULTRAFEEDER_CONFIG...")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # Read environment
    env_vars = read_env(env_file)
    
    # Build config
    config_string = build_config(env_vars)
    
    # Update .env
    update_env_file(env_file, config_string)
    
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    if config_string:
        feed_count = len([p for p in config_string.split(';') if p.startswith('adsb,')])
        print(f"✓ Configuration built: {feed_count} active feeds")
    else:
        print("⚠ No aggregators enabled")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
