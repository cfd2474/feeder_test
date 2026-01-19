#!/usr/bin/env python3
"""
Docker Manager for TAK-ADSB-Feeder
Based on adsb.im production implementation

Provides:
- Container status caching (10-second refresh)
- Thread-safe operations with locking
- Background operation execution
"""

import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, Optional, List


class Lock:
    """Lock wrapper to prevent concurrent Docker operations"""
    
    def __init__(self):
        self.lock = threading.Lock()
    
    def acquire(self, blocking: bool = True, timeout: float = -1.0) -> bool:
        """Acquire the lock"""
        return self.lock.acquire(blocking=blocking, timeout=timeout)
    
    def release(self) -> None:
        """Release the lock"""
        return self.lock.release()
    
    def locked(self) -> bool:
        """Check if lock is currently held"""
        return self.lock.locked()
    
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.release()


class DockerManager:
    """
    Manage Docker container status with intelligent caching
    
    Features:
    - Cache docker ps results for 10 seconds
    - Thread-safe container status queries
    - Automatic cache refresh
    """
    
    def __init__(self, base_path: str = "/opt/TAK_ADSB"):
        self.base_path = Path(base_path)
        self.compose_script = self.base_path / "scripts" / "docker-compose-adsb"
        self.env_file = self.base_path / "config" / ".env"
        
        # Container status cache
        self.containerCheckLock = threading.RLock()
        self.lastContainerCheck: float = 0.0
        self.dockerPsCache: Dict[str, str] = {}
    
    def refreshDockerPs(self) -> None:
        """
        Refresh Docker container status cache
        Rate-limited to once per 10 seconds
        """
        with self.containerCheckLock:
            now = time.time()
            if now - self.lastContainerCheck < 10:
                # Cache still fresh, do nothing
                return
            
            self.lastContainerCheck = now
            self.dockerPsCache = {}
            
            cmdline = "docker ps --filter status=running --format '{{.Names}};{{.Status}}'"
            
            try:
                result = subprocess.run(
                    cmdline,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        if ';' in line:
                            name, status = line.split(';', 1)
                            self.dockerPsCache[name] = status
                else:
                    print(f"Error running docker ps: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                print("Timeout refreshing docker ps cache")
            except Exception as e:
                print(f"Exception refreshing docker ps: {e}")
    
    def getContainerStatus(self, container_name: str) -> Optional[str]:
        """
        Get cached status of a specific container
        
        Args:
            container_name: Name of the container
            
        Returns:
            Status string or None if not running
        """
        self.refreshDockerPs()
        return self.dockerPsCache.get(container_name)
    
    def getAllContainerStatus(self) -> Dict[str, str]:
        """
        Get status of all running containers
        
        Returns:
            Dictionary of container_name: status
        """
        self.refreshDockerPs()
        return self.dockerPsCache.copy()
    
    def isContainerRunning(self, container_name: str) -> bool:
        """Check if a container is running"""
        return self.getContainerStatus(container_name) is not None
    
    def getRunningContainers(self) -> List[str]:
        """Get list of running container names"""
        self.refreshDockerPs()
        return list(self.dockerPsCache.keys())


class DockerOperations:
    """
    Manage Docker operations with background execution and locking
    
    Features:
    - Background operation execution
    - Lock prevents concurrent operations
    - Wait for operation completion
    """
    
    def __init__(self, base_path: str = "/opt/TAK_ADSB"):
        self.base_path = Path(base_path)
        self.compose_script = self.base_path / "scripts" / "docker-compose-adsb"
        self.operation_lock = Lock()
    
    def bg_run(self, cmdline: str, silent: bool = False) -> bool:
        """
        Run a command in background with lock protection
        
        Args:
            cmdline: Shell command to execute
            silent: If True, capture output
            
        Returns:
            True if started successfully, False if lock couldn't be acquired
        """
        if not self.operation_lock.acquire(blocking=False):
            print(f"Operation locked, couldn't run: {cmdline}")
            return False
        
        # We have the lock
        def do_operation():
            try:
                print(f"Running: {cmdline}")
                subprocess.run(
                    cmdline,
                    shell=True,
                    capture_output=silent,
                    timeout=180
                )
            except subprocess.TimeoutExpired:
                print(f"Timeout running: {cmdline}")
            except Exception as e:
                print(f"Error running command: {e}")
            finally:
                self.operation_lock.release()
        
        threading.Thread(target=do_operation).start()
        return True
    
    def is_busy(self) -> bool:
        """Check if an operation is in progress"""
        return self.operation_lock.locked()
    
    def wait_operation_done(self, timeout: float = 180.0) -> bool:
        """
        Wait for current operation to complete
        
        Args:
            timeout: Maximum seconds to wait
            
        Returns:
            True if operation completed, False if timeout
        """
        if self.operation_lock.acquire(blocking=True, timeout=timeout):
            self.operation_lock.release()
            return True
        return False
    
    @property
    def state(self) -> str:
        """Get operation state ('busy' or 'done')"""
        return "busy" if self.is_busy() else "done"
    
    # Convenience methods for common operations
    
    def start_services(self) -> bool:
        """Start all Docker services"""
        cmdline = f"sudo {self.compose_script} up -d"
        return self.bg_run(cmdline)
    
    def stop_services(self) -> bool:
        """Stop all Docker services"""
        cmdline = f"sudo {self.compose_script} down"
        return self.bg_run(cmdline)
    
    def restart_services(self) -> bool:
        """Restart all Docker services"""
        cmdline = f"sudo {self.compose_script} restart"
        return self.bg_run(cmdline)
    
    def restart_service(self, service_name: str) -> bool:
        """Restart a specific service"""
        cmdline = f"sudo {self.compose_script} restart {service_name}"
        return self.bg_run(cmdline)
    
    def update_images(self) -> bool:
        """Pull latest Docker images"""
        cmdline = f"sudo {self.compose_script} pull"
        return self.bg_run(cmdline)
    
    def update_and_restart(self) -> bool:
        """Pull latest images and restart services"""
        if not self.operation_lock.acquire(blocking=False):
            return False
        
        def do_update():
            try:
                print("Pulling latest images...")
                subprocess.run(
                    f"sudo {self.compose_script} pull",
                    shell=True,
                    timeout=300
                )
                print("Restarting services...")
                subprocess.run(
                    f"sudo {self.compose_script} up -d",
                    shell=True,
                    timeout=180
                )
                print("Update complete!")
            finally:
                self.operation_lock.release()
        
        threading.Thread(target=do_update).start()
        return True


class EnvironmentManager:
    """Manage .env file configuration"""
    
    def __init__(self, env_file: str = "/opt/TAK_ADSB/config/.env"):
        self.env_file = Path(env_file)
    
    def read_env(self) -> Dict[str, str]:
        """Read environment variables from .env file"""
        env_vars = {}
        
        if self.env_file.exists():
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            env_vars[key.strip()] = value.strip()
        
        return env_vars
    
    def write_env(self, env_vars: Dict[str, str]) -> None:
        """Write environment variables to .env file"""
        if not self.env_file.exists():
            # Create new file
            lines = []
            for key, value in env_vars.items():
                lines.append(f"{key}={value}\n")
        else:
            # Update existing file
            with open(self.env_file, 'r') as f:
                lines = f.readlines()
            
            # Update existing keys
            for i, line in enumerate(lines):
                if '=' in line and not line.strip().startswith('#'):
                    key = line.split('=', 1)[0].strip()
                    if key in env_vars:
                        lines[i] = f"{key}={env_vars[key]}\n"
                        del env_vars[key]
            
            # Add new keys
            for key, value in env_vars.items():
                lines.append(f"{key}={value}\n")
        
        with open(self.env_file, 'w') as f:
            f.writelines(lines)
    
    def set_value(self, key: str, value: str) -> None:
        """Set a single environment variable"""
        env_vars = self.read_env()
        env_vars[key] = value
        self.write_env(env_vars)
    
    def get_value(self, key: str, default: str = "") -> str:
        """Get a single environment variable"""
        env_vars = self.read_env()
        return env_vars.get(key, default)
    
    def enable_aggregator(self, aggregator_name: str) -> None:
        """Enable an aggregator"""
        key = f"AF_IS_{aggregator_name.upper()}_ENABLED"
        self.set_value(key, "true")
    
    def disable_aggregator(self, aggregator_name: str) -> None:
        """Disable an aggregator"""
        key = f"AF_IS_{aggregator_name.upper()}_ENABLED"
        self.set_value(key, "false")
    
    def is_aggregator_enabled(self, aggregator_name: str) -> bool:
        """Check if an aggregator is enabled"""
        key = f"AF_IS_{aggregator_name.upper()}_ENABLED"
        return self.get_value(key) == "true"


if __name__ == "__main__":
    # Test the manager
    docker_mgr = DockerManager()
    docker_ops = DockerOperations()
    env_mgr = EnvironmentManager()
    
    print("=== Docker Container Status ===")
    docker_mgr.refreshDockerPs()
    for name, status in docker_mgr.getAllContainerStatus().items():
        print(f"{name}: {status}")
    
    print(f"\n=== Operation State: {docker_ops.state} ===")
    
    print("\n=== Environment Variables ===")
    env_vars = env_mgr.read_env()
    for key, value in list(env_vars.items())[:10]:
        print(f"{key}={value}")
