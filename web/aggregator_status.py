#!/usr/bin/env python3
"""
Aggregator Status Tracking for TAK-ADSB-Feeder
Based on adsb.im production implementation

Tracks connection status to aggregators by reading:
- readsb prometheus stats for Beast connections
- mlat-client JSON files for MLAT sync status
"""

import json
import re
import time
import threading
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional, Dict


class Status(Enum):
    """Aggregator connection status"""
    DISCONNECTED = "disconnected"
    UNKNOWN = "unknown"
    GOOD = "good"
    BAD = "bad"
    WARNING = "warning"
    DISABLED = "disabled"
    STARTING = "starting"
    CONTAINER_DOWN = "container_down"


# Status display symbols (optional, for UI)
STATUS_SYMBOLS = {
    Status.DISCONNECTED: "✖",
    Status.UNKNOWN: "?",
    Status.GOOD: "✓",
    Status.BAD: "✗",
    Status.WARNING: "⚠",
    Status.DISABLED: "○",
    Status.STARTING: "⟳",
    Status.CONTAINER_DOWN: "▼",
}


class AggregatorStatus:
    """
    Track connection status for a single aggregator
    
    Reads status from:
    - Docker container status
    - readsb prometheus stats (Beast connection)
    - mlat-client JSON stats (MLAT sync)
    
    Caches results for 10 seconds to avoid excessive disk I/O
    """
    
    def __init__(self, agg_name: str, docker_manager, env_manager):
        self.agg_name = agg_name
        self.docker_manager = docker_manager
        self.env_manager = env_manager
        
        self.lock = threading.Lock()
        self.last_check = datetime.fromtimestamp(0)
        
        self.beast_status = Status.UNKNOWN
        self.mlat_status = Status.UNKNOWN
        self.container_status = None
        
        # Container name mapping (aggregator name -> container name)
        self.container_map = {
            'fr24': 'fr24',
            'adsbx': 'adsbx',
            'airplaneslive': 'airplaneslive',
            'radarbox': 'rbfeeder',
            'planefinder': 'pfclient',
            'openskynetwork': 'opensky',
            'adsbhub': 'adsbhub',
        }
        
        # Paths for status files
        self.uf_dir = Path("/run/adsb-feeder-ultrafeeder")
    
    @property
    def container_name(self) -> str:
        """Get Docker container name for this aggregator"""
        return self.container_map.get(self.agg_name, self.agg_name)
    
    def check(self, force: bool = False) -> Dict[str, str]:
        """
        Check aggregator status (cached for 10 seconds)
        
        Args:
            force: Force immediate check, bypass cache
            
        Returns:
            Dictionary with 'beast', 'mlat', 'container', 'symbol' keys
        """
        with self.lock:
            # Use cache if fresh and not forced
            if not force and datetime.now() - self.last_check < timedelta(seconds=10):
                return self._format_status()
            
            # Check if aggregator is enabled
            if not self._is_enabled():
                self.beast_status = Status.DISABLED
                self.mlat_status = Status.DISABLED
                self.container_status = None
                self.last_check = datetime.now()
                return self._format_status()
            
            # Check container status
            self.container_status = self.docker_manager.getContainerStatus(
                self.container_name
            )
            
            if self.container_status is None:
                self.beast_status = Status.CONTAINER_DOWN
                self.mlat_status = Status.CONTAINER_DOWN
            else:
                # Container is running, check feed status
                self._check_beast_status()
                self._check_mlat_status()
            
            self.last_check = datetime.now()
            return self._format_status()
    
    def _is_enabled(self) -> bool:
        """Check if aggregator is enabled in .env"""
        key = f"AF_IS_{self.agg_name.upper()}_ENABLED"
        return self.env_manager.get_value(key) == "true"
    
    def _check_beast_status(self) -> None:
        """
        Check Beast feed connection status from readsb stats
        
        Reads prometheus stats file to check connection uptime
        """
        try:
            stats_file = self.uf_dir / "readsb" / "stats.prom"
            if not stats_file.exists():
                self.beast_status = Status.DISCONNECTED
                return
            
            with open(stats_file, 'r') as f:
                stats_content = f.read()
            
            # Look for connection status in prometheus format
            # Pattern: readsb_net_connector_status{host="feed.example.com",port="30004"} 123
            # Value is seconds connected (0 = disconnected)
            
            # Try to find any connector status for this aggregator
            # This is simplified - production code would match specific host/port
            pattern = r'readsb_net_connector_status\{[^}]*\}\s+(\d+)'
            matches = re.findall(pattern, stats_content)
            
            if matches:
                # Use the first match (in production, would match specific aggregator)
                seconds_connected = int(matches[0])
                
                if seconds_connected <= 0:
                    self.beast_status = Status.DISCONNECTED
                elif seconds_connected > 20:
                    self.beast_status = Status.GOOD
                else:
                    self.beast_status = Status.WARNING
            else:
                self.beast_status = Status.UNKNOWN
                
        except FileNotFoundError:
            self.beast_status = Status.DISCONNECTED
        except Exception as e:
            print(f"Error checking beast status for {self.agg_name}: {e}")
            self.beast_status = Status.UNKNOWN
    
    def _check_mlat_status(self) -> None:
        """
        Check MLAT sync status from mlat-client JSON
        
        Reads mlat-client stats to check sync percentages
        """
        # Check if MLAT is enabled for this aggregator
        mlat_key = f"FEEDER_{self.agg_name.upper()}_MLAT"
        if self.env_manager.get_value(mlat_key) != "yes":
            self.mlat_status = Status.DISABLED
            return
        
        try:
            # Find mlat-client JSON file
            # Pattern: /run/adsb-feeder-ultrafeeder/mlat-client/feed.example.com:31090.json
            mlat_dir = self.uf_dir / "mlat-client"
            
            if not mlat_dir.exists():
                self.mlat_status = Status.DISCONNECTED
                return
            
            # Look for any JSON file (simplified - production matches specific file)
            json_files = list(mlat_dir.glob("*.json"))
            
            if not json_files:
                self.mlat_status = Status.DISCONNECTED
                return
            
            # Read the first JSON file found
            with open(json_files[0], 'r') as f:
                mlat_data = json.load(f)
            
            percent_good = mlat_data.get('good_sync_percentage_last_hour', 0)
            percent_bad = mlat_data.get('bad_sync_percentage_last_hour', 0)
            timestamp = mlat_data.get('now', 0)
            
            # Check if data is stale (more than 60 seconds old)
            if time.time() - timestamp > 60:
                self.mlat_status = Status.DISCONNECTED
            elif percent_good > 10 and percent_bad <= 5:
                self.mlat_status = Status.GOOD
            elif percent_bad > 15:
                self.mlat_status = Status.BAD
            else:
                self.mlat_status = Status.WARNING
                
        except FileNotFoundError:
            self.mlat_status = Status.DISCONNECTED
        except json.JSONDecodeError:
            self.mlat_status = Status.UNKNOWN
        except Exception as e:
            print(f"Error checking MLAT status for {self.agg_name}: {e}")
            self.mlat_status = Status.UNKNOWN
    
    def _format_status(self) -> Dict[str, str]:
        """Format status as dictionary for API response"""
        return {
            'aggregator': self.agg_name,
            'beast': self.beast_status.value,
            'mlat': self.mlat_status.value,
            'container': self.container_status,
            'symbol': STATUS_SYMBOLS.get(self.beast_status, "?"),
            'enabled': self._is_enabled()
        }
    
    @property
    def beast(self) -> str:
        """Get beast status string"""
        return self.beast_status.value
    
    @property
    def mlat(self) -> str:
        """Get MLAT status string"""
        return self.mlat_status.value
    
    @property
    def is_good(self) -> bool:
        """Check if both beast and MLAT are good"""
        return (self.beast_status == Status.GOOD and 
                (self.mlat_status == Status.GOOD or 
                 self.mlat_status == Status.DISABLED))


class AggregatorStatusManager:
    """
    Manage status checking for all aggregators
    
    Provides centralized status checking with caching
    """
    
    def __init__(self, docker_manager, env_manager):
        self.docker_manager = docker_manager
        self.env_manager = env_manager
        
        # Initialize status checkers for known aggregators
        self.aggregators = {
            'fr24': AggregatorStatus('fr24', docker_manager, env_manager),
            'adsbx': AggregatorStatus('adsbx', docker_manager, env_manager),
            'airplaneslive': AggregatorStatus('airplaneslive', docker_manager, env_manager),
            'radarbox': AggregatorStatus('radarbox', docker_manager, env_manager),
            'planefinder': AggregatorStatus('planefinder', docker_manager, env_manager),
            'openskynetwork': AggregatorStatus('openskynetwork', docker_manager, env_manager),
            'adsbhub': AggregatorStatus('adsbhub', docker_manager, env_manager),
        }
    
    def check_all(self, force: bool = False) -> Dict[str, Dict]:
        """
        Check status of all aggregators
        
        Args:
            force: Force immediate check, bypass cache
            
        Returns:
            Dictionary of aggregator_name: status_dict
        """
        results = {}
        for name, agg in self.aggregators.items():
            results[name] = agg.check(force=force)
        return results
    
    def check_one(self, agg_name: str, force: bool = False) -> Optional[Dict]:
        """
        Check status of a single aggregator
        
        Args:
            agg_name: Name of aggregator
            force: Force immediate check
            
        Returns:
            Status dictionary or None if aggregator not found
        """
        agg = self.aggregators.get(agg_name)
        if agg:
            return agg.check(force=force)
        return None
    
    def get_good_aggregators(self) -> list:
        """Get list of aggregators with good status"""
        self.check_all()
        return [name for name, agg in self.aggregators.items() if agg.is_good]
    
    def get_enabled_aggregators(self) -> list:
        """Get list of enabled aggregators"""
        return [name for name, agg in self.aggregators.items() 
                if agg._is_enabled()]


if __name__ == "__main__":
    # Test the status checker
    from docker_manager import DockerManager, EnvironmentManager
    
    docker_mgr = DockerManager()
    env_mgr = EnvironmentManager()
    status_mgr = AggregatorStatusManager(docker_mgr, env_mgr)
    
    print("=== Aggregator Status ===")
    all_status = status_mgr.check_all()
    
    for name, status in all_status.items():
        print(f"\n{name}:")
        print(f"  Enabled: {status['enabled']}")
        print(f"  Beast: {status['beast']} {status['symbol']}")
        print(f"  MLAT: {status['mlat']}")
        print(f"  Container: {status['container'] or 'Not running'}")
