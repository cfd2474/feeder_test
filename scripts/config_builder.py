#!/usr/bin/env python3
"""
TAKNET-PS-ADSB-Feeder Config Builder v2.1
Tactical Awareness Kit Network for Enhanced Tracking – Public Safety
Builds ULTRAFEEDER_CONFIG with TAKNET-PS Server as hardcoded priority
Supports primary/fallback connection modes with automatic configuration repair
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

def write_env(env_file, env_vars):
    """Write env vars back to .env file"""
    lines = []
    with open(env_file) as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and '=' in stripped:
                key = stripped.split('=', 1)[0].strip()
                if key in env_vars:
                    lines.append(f"{key}={env_vars[key]}\n")
                else:
                    lines.append(line)
            else:
                lines.append(line)
    
    with open(env_file, 'w') as f:
        f.writelines(lines)

def ensure_taknet_config(env_vars, env_file):
    """
    Ensure TAKNET-PS configuration exists
    Builds missing values automatically to prevent user skip
    Returns: (env_vars, was_repaired)
    """
    required_config = {
        'TAKNET_PS_ENABLED': 'true',
        'TAKNET_PS_SERVER_HOST_PRIMARY': '100.117.34.88',
        'TAKNET_PS_SERVER_HOST_FALLBACK': '104.225.219.254',
        'TAKNET_PS_SERVER_PORT': '30004',
        'TAKNET_PS_CONNECTION_MODE': 'auto',
        'TAKNET_PS_MLAT_ENABLED': 'true',
        'TAKNET_PS_MLAT_PORT': '30105'
    }
    
    was_repaired = False
    
    for key, default_value in required_config.items():
        if key not in env_vars or not env_vars[key]:
            print(f"⚠ Missing {key}, auto-configuring: {default_value}")
            env_vars[key] = default_value
            was_repaired = True
    
    # Write back if repaired
    if was_repaired:
        write_env(env_file, env_vars)
        print("✓ TAKNET-PS configuration auto-repaired and saved")
    
    return env_vars, was_repaired

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

def select_taknet_host(env_vars):
    """
    Select TAKNET-PS Server host based on connection mode and availability
    Returns: (selected_host, connection_type)
    """
    mode = env_vars.get('TAKNET_PS_CONNECTION_MODE', 'auto').lower()
    primary = env_vars.get('TAKNET_PS_SERVER_HOST_PRIMARY', '').strip()
    fallback = env_vars.get('TAKNET_PS_SERVER_HOST_FALLBACK', '').strip()
    port = env_vars.get('TAKNET_PS_SERVER_PORT', '30004').strip()
    
    # Force modes
    if mode == 'primary' and primary:
        print(f"ℹ TAKNET-PS: Forced to primary: {primary}")
        return (primary, 'primary-forced')
    
    if mode == 'fallback' and fallback:
        print(f"ℹ TAKNET-PS: Forced to fallback: {fallback}")
        return (fallback, 'fallback-forced')
    
    # Auto mode - test connectivity
    if mode == 'auto':
        if primary and check_host_reachable(primary, port):
            print(f"✓ TAKNET-PS: Primary reachable: {primary}")
            return (primary, 'primary-auto')
        elif fallback and check_host_reachable(fallback, port):
            print(f"⚠ TAKNET-PS: Primary unreachable, using fallback: {fallback}")
            return (fallback, 'fallback-auto')
        elif primary:
            print(f"⚠ TAKNET-PS: Neither reachable, defaulting to primary: {primary}")
            return (primary, 'primary-default')
    
    # Monitor mode (Phase 2) - use primary, external monitor will handle failover
    if mode == 'monitor' and primary:
        print(f"ℹ TAKNET-PS: Monitor mode, using primary: {primary}")
        return (primary, 'monitor-mode')
    
    # Fallback to primary if nothing else works
    if primary:
        return (primary, 'primary-fallback')
    elif fallback:
        return (fallback, 'fallback-only')
    
    return (None, 'disabled')

def build_config(env_vars):
    """Build ULTRAFEEDER_CONFIG string with TAKNET-PS as priority"""
    config_parts = []
    
    # TAKNET-PS Server - ALWAYS FIRST (Priority Feed)
    if env_vars.get('TAKNET_PS_ENABLED', 'true').lower() == 'true':
        taknet_host, connection_type = select_taknet_host(env_vars)
        port = env_vars.get('TAKNET_PS_SERVER_PORT', '30004').strip()
        mlat_port = env_vars.get('TAKNET_PS_MLAT_PORT', '30105').strip()
        
        if taknet_host:
            # Beast feed
            config_parts.append(f"adsb,{taknet_host},{port},beast_reduce_plus_out")
            print(f"✓ TAKNET-PS Beast: {taknet_host}:{port} ({connection_type})")
            
            # MLAT feed (if enabled)
            if env_vars.get('TAKNET_PS_MLAT_ENABLED', 'true').lower() == 'true':
                config_parts.append(f"mlat,{taknet_host},{mlat_port},39001")
                print(f"✓ TAKNET-PS MLAT: {taknet_host}:{mlat_port}")
            else:
                print("ℹ TAKNET-PS MLAT: Disabled")
        else:
            print("✗ TAKNET-PS Server: No valid host configuration found")
    else:
        print("ℹ TAKNET-PS Server: Disabled (not recommended)")
    
    # FlightRadar24 - Uses dedicated container, not ultrafeeder
    # The FR24 container connects directly to ultrafeeder's Beast output
    if env_vars.get('FR24_ENABLED', '').lower() == 'true':
        if env_vars.get('FR24_SHARING_KEY', '').strip():
            print("✓ FlightRadar24 (via dedicated container)")
        else:
            print("⚠ FlightRadar24 enabled but no sharing key provided")
    
    # ADS-B Exchange
    if env_vars.get('ADSBX_ENABLED', '').lower() == 'true':
        if env_vars.get('ADSBX_UUID', '').strip():
            config_parts.append("adsb,feed.adsb.exchange,30004,beast_reduce_plus_out")
            config_parts.append("mlat,feed.adsb.exchange,31090,39001")
            print("✓ ADS-B Exchange")
    
    # Airplanes.Live
    if env_vars.get('AIRPLANESLIVE_ENABLED', '').lower() == 'true':
        if env_vars.get('AIRPLANESLIVE_UUID', '').strip():
            config_parts.append("adsb,feed.airplanes.live,30004,beast_reduce_plus_out")
            config_parts.append("mlat,mlat.airplanes.live,31090,39002")
            print("✓ Airplanes.Live")
    
    return ';'.join(config_parts)

def main():
    env_file = Path("/opt/adsb/config/.env")
    
    if not env_file.exists():
        print(f"✗ Error: {env_file} not found")
        sys.exit(1)
    
    # Read environment
    env_vars = read_env(env_file)
    
    # Ensure TAKNET-PS config exists (auto-repair if missing)
    env_vars, was_repaired = ensure_taknet_config(env_vars, env_file)
    
    # Build config
    config_str = build_config(env_vars)
    
    # Update ULTRAFEEDER_CONFIG
    env_vars['ULTRAFEEDER_CONFIG'] = config_str
    
    # Write back to .env
    write_env(env_file, env_vars)
    
    print(f"\n✓ Configuration built successfully")
    if was_repaired:
        print("✓ Missing TAKNET-PS settings were automatically configured")
    print(f"Active feeds: {len(config_str.split(';')) if config_str else 0}")

if __name__ == "__main__":
    main()
