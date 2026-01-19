#!/usr/bin/env python3
"""Build ULTRAFEEDER_CONFIG from .env settings"""

import sys
from pathlib import Path

def read_env(env_file):
    env_vars = {}
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    return env_vars

def build_config(env_vars):
    config_parts = []
    
    # TAK Server (Priority 1)
    if env_vars.get('TAK_ENABLED', '').lower() == 'true':
        host = env_vars.get('TAK_SERVER_HOST', '').strip()
        port = env_vars.get('TAK_SERVER_PORT', '8087').strip()
        if host:
            config_parts.append(f"adsb,{host},{port},beast_reduce_plus_out")
            print(f"✓ TAK Server: {host}:{port}")
    
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
    print("Building ULTRAFEEDER_CONFIG...")
    env_vars = read_env(env_file)
    config_string = build_config(env_vars)
    update_env_file(env_file, config_string)
    
    if config_string:
        print(f"\n✓ Built config with {len(config_string.split(';'))} feeds")
    else:
        print("\n⚠ No aggregators enabled")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
