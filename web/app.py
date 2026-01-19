#!/usr/bin/env python3
"""
TAK-ADSB-Feeder v2.0 Flask Web Interface
Production implementation with Docker management
"""

from flask import Flask, jsonify, request, render_template
import sys
from pathlib import Path

# Add the web directory to path
sys.path.insert(0, str(Path(__file__).parent))

from docker_manager import DockerManager, DockerOperations, EnvironmentManager
from aggregator_status import AggregatorStatusManager

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Initialize managers
docker_mgr = DockerManager()
docker_ops = DockerOperations()
env_mgr = EnvironmentManager()
status_mgr = AggregatorStatusManager(docker_mgr, env_mgr)

# ============================================
# Docker Management Routes
# ============================================

@app.route('/api/docker/status')
def docker_status():
    """Get status of all Docker containers"""
    return jsonify({
        'success': True,
        'containers': docker_mgr.getAllContainerStatus(),
        'running': docker_mgr.getRunningContainers(),
        'is_busy': docker_ops.is_busy(),
        'state': docker_ops.state
    })

@app.route('/api/docker/start', methods=['POST'])
def docker_start():
    """Start all Docker services"""
    if docker_ops.is_busy():
        return jsonify({
            'success': False,
            'error': 'Another operation is in progress'
        }), 409
    
    success = docker_ops.start_services()
    
    return jsonify({
        'success': success,
        'message': 'Starting Docker services' if success else 'Failed to start'
    })

@app.route('/api/docker/stop', methods=['POST'])
def docker_stop():
    """Stop all Docker services"""
    if docker_ops.is_busy():
        return jsonify({
            'success': False,
            'error': 'Another operation is in progress'
        }), 409
    
    success = docker_ops.stop_services()
    
    return jsonify({
        'success': success,
        'message': 'Stopping Docker services' if success else 'Failed to stop'
    })

@app.route('/api/docker/restart', methods=['POST'])
def docker_restart():
    """Restart all Docker services"""
    if docker_ops.is_busy():
        return jsonify({
            'success': False,
            'error': 'Another operation is in progress'
        }), 409
    
    success = docker_ops.restart_services()
    
    return jsonify({
        'success': success,
        'message': 'Restarting Docker services' if success else 'Failed to restart'
    })

@app.route('/api/docker/restart/<service>', methods=['POST'])
def docker_restart_service(service):
    """Restart a specific Docker service"""
    if docker_ops.is_busy():
        return jsonify({
            'success': False,
            'error': 'Another operation is in progress'
        }), 409
    
    success = docker_ops.restart_service(service)
    
    return jsonify({
        'success': success,
        'message': f'Restarting {service}' if success else f'Failed to restart {service}'
    })

@app.route('/api/docker/update', methods=['POST'])
def docker_update():
    """Update Docker images and restart"""
    if docker_ops.is_busy():
        return jsonify({
            'success': False,
            'error': 'Another operation is in progress'
        }), 409
    
    success = docker_ops.update_and_restart()
    
    return jsonify({
        'success': success,
        'message': 'Updating Docker images and restarting' if success else 'Failed to update'
    })

@app.route('/api/docker/operation/status')
def operation_status():
    """Check if a Docker operation is in progress"""
    return jsonify({
        'busy': docker_ops.is_busy(),
        'state': docker_ops.state
    })

# ============================================
# Aggregator Management Routes
# ============================================

@app.route('/api/aggregators/status')
def aggregators_status():
    """Get status of all aggregators"""
    force = request.args.get('force', 'false').lower() == 'true'
    
    status = status_mgr.check_all(force=force)
    
    return jsonify({
        'success': True,
        'aggregators': status,
        'enabled': status_mgr.get_enabled_aggregators(),
        'good': status_mgr.get_good_aggregators()
    })

@app.route('/api/aggregators/<agg_name>/status')
def aggregator_status(agg_name):
    """Get status of a specific aggregator"""
    force = request.args.get('force', 'false').lower() == 'true'
    
    status = status_mgr.check_one(agg_name, force=force)
    
    if status is None:
        return jsonify({
            'success': False,
            'error': f'Unknown aggregator: {agg_name}'
        }), 404
    
    return jsonify({
        'success': True,
        **status
    })

@app.route('/api/aggregators/<agg_name>/enable', methods=['POST'])
def enable_aggregator(agg_name):
    """Enable an aggregator"""
    try:
        env_mgr.enable_aggregator(agg_name)
        
        # Restart Docker services to apply changes
        if not docker_ops.is_busy():
            docker_ops.start_services()
            message = f'{agg_name} enabled and services restarting'
        else:
            message = f'{agg_name} enabled (restart pending - operation in progress)'
        
        return jsonify({
            'success': True,
            'message': message
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/aggregators/<agg_name>/disable', methods=['POST'])
def disable_aggregator(agg_name):
    """Disable an aggregator"""
    try:
        env_mgr.disable_aggregator(agg_name)
        
        # Restart Docker services to apply changes
        if not docker_ops.is_busy():
            docker_ops.restart_services()
            message = f'{agg_name} disabled and services restarting'
        else:
            message = f'{agg_name} disabled (restart pending - operation in progress)'
        
        return jsonify({
            'success': True,
            'message': message
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================
# Configuration Management Routes
# ============================================

@app.route('/api/config/env')
def get_env_config():
    """Get environment configuration"""
    # Filter out sensitive keys
    sensitive_keys = ['KEY', 'UUID', 'PASSWORD', 'SECRET', 'TOKEN']
    
    env_vars = env_mgr.read_env()
    
    filtered = {}
    for key, value in env_vars.items():
        if any(sensitive in key.upper() for sensitive in sensitive_keys):
            filtered[key] = '***REDACTED***'
        else:
            filtered[key] = value
    
    return jsonify({
        'success': True,
        'config': filtered
    })

@app.route('/api/config/env/<key>')
def get_env_value(key):
    """Get a specific environment variable"""
    value = env_mgr.get_value(key)
    
    return jsonify({
        'success': True,
        'key': key,
        'value': value
    })

@app.route('/api/config/env/<key>', methods=['POST'])
def set_env_value(key):
    """Set a specific environment variable"""
    data = request.get_json()
    
    if not data or 'value' not in data:
        return jsonify({
            'success': False,
            'error': 'Missing value in request'
        }), 400
    
    try:
        env_mgr.set_value(key, data['value'])
        
        return jsonify({
            'success': True,
            'message': f'{key} updated',
            'key': key,
            'value': data['value']
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/config/location', methods=['POST'])
def set_location():
    """Set feeder location (lat, lon, alt)"""
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Missing data in request'
        }), 400
    
    try:
        if 'lat' in data:
            env_mgr.set_value('FEEDER_LAT', str(data['lat']))
        if 'lon' in data:
            env_mgr.set_value('FEEDER_LONG', str(data['lon']))
        if 'alt' in data:
            env_mgr.set_value('FEEDER_ALT_M', str(data['alt']))
        
        return jsonify({
            'success': True,
            'message': 'Location updated'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================
# System Info Routes
# ============================================

@app.route('/api/system/info')
def system_info():
    """Get system information"""
    import platform
    import psutil
    
    return jsonify({
        'success': True,
        'system': {
            'platform': platform.system(),
            'platform_version': platform.version(),
            'architecture': platform.machine(),
            'hostname': platform.node(),
            'cpu_count': psutil.cpu_count(),
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory': {
                'total': psutil.virtual_memory().total,
                'available': psutil.virtual_memory().available,
                'percent': psutil.virtual_memory().percent
            },
            'disk': {
                'total': psutil.disk_usage('/').total,
                'used': psutil.disk_usage('/').used,
                'free': psutil.disk_usage('/').free,
                'percent': psutil.disk_usage('/').percent
            }
        }
    })

# ============================================
# Web Interface Routes
# ============================================

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')

@app.route('/aggregators')
def aggregators_page():
    """Aggregator management page"""
    return render_template('aggregators.html')

@app.route('/config')
def config_page():
    """Configuration page"""
    return render_template('config.html')

# ============================================
# Health Check
# ============================================

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'TAK-ADSB-Feeder',
        'version': '2.0'
    })

# ============================================
# Error Handlers
# ============================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

# ============================================
# Main
# ============================================

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False
    )
