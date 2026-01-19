#!/bin/bash
# TAK-ADSB-Feeder v2.0 - Production Installation Script
# Based on adsb.im production patterns

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
BASE_DIR="/opt/TAK_ADSB"
SCRIPT_DIR="$BASE_DIR/scripts"
CONFIG_DIR="$BASE_DIR/config"
WEB_DIR="$BASE_DIR/web"

print_header() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }

check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root (sudo)"
        exit 1
    fi
}

check_system() {
    print_header "System Check"
    
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "OS: $NAME $VERSION"
    fi
    
    ARCH=$(uname -m)
    echo "Architecture: $ARCH"
    
    FREE_SPACE=$(df -BG / | tail -1 | awk '{print $4}' | sed 's/G//')
    echo "Free space: ${FREE_SPACE}GB"
    
    if [ "$FREE_SPACE" -lt 5 ]; then
        print_error "Insufficient disk space. Need at least 5GB free."
        exit 1
    fi
    
    print_success "System check passed"
}

install_docker() {
    print_header "Installing Docker"
    
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version)
        print_success "Docker already installed: $DOCKER_VERSION"
        return 0
    fi
    
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sh /tmp/get-docker.sh
    rm /tmp/get-docker.sh
    
    systemctl start docker
    systemctl enable docker
    
    if [ "$SUDO_USER" ]; then
        usermod -aG docker $SUDO_USER
        print_success "Added $SUDO_USER to docker group (logout/login required)"
    fi
    
    print_success "Docker installed successfully"
}

install_docker_compose() {
    print_header "Installing Docker Compose"
    
    if docker compose version &> /dev/null; then
        COMPOSE_VERSION=$(docker compose version)
        print_success "Docker Compose already installed: $COMPOSE_VERSION"
        return 0
    fi
    
    echo "Installing Docker Compose plugin..."
    apt-get update -qq
    apt-get install -y docker-compose-plugin
    
    print_success "Docker Compose installed successfully"
}

create_directories() {
    print_header "Creating Directory Structure"
    
    mkdir -p $BASE_DIR/{bin,config,docker/volumes,web,scripts,state}
    mkdir -p $CONFIG_DIR/{aggregators,readsb}
    mkdir -p $WEB_DIR/{templates,static}
    
    print_success "Directory structure created"
}

install_python_deps() {
    print_header "Installing Python Dependencies"
    
    echo "Checking for Flask and psutil..."
    
    # Try to import to see if already installed
    if python3 -c "import flask, psutil" 2>/dev/null; then
        print_success "Flask and psutil already installed"
        return 0
    fi
    
    # Prefer apt packages on Debian/Raspbian
    if command -v apt-get &> /dev/null; then
        echo "Installing via apt (preferred for Raspberry Pi)..."
        apt-get update -qq
        apt-get install -y python3-flask python3-psutil 2>/dev/null || {
            print_warning "apt install failed, trying pip3..."
            
            # Install pip3 if needed
            if ! command -v pip3 &> /dev/null; then
                echo "Installing pip3..."
                apt-get install -y python3-pip
            fi
            
            # Try pip3 install
            pip3 install flask psutil --break-system-packages 2>/dev/null || \
                pip3 install flask psutil
        }
    else
        # Non-Debian systems
        if ! command -v pip3 &> /dev/null; then
            print_error "pip3 not found. Please install python3-pip first."
            exit 1
        fi
        
        pip3 install flask psutil --break-system-packages 2>/dev/null || \
            pip3 install flask psutil
    fi
    
    # Verify installation
    if python3 -c "import flask, psutil" 2>/dev/null; then
        print_success "Python dependencies installed successfully"
    else
        print_error "Failed to install Python dependencies"
        exit 1
    fi
}

create_config_files() {
    print_header "Creating Configuration Files"
    
    # Create .env file
    cat > "$CONFIG_DIR/.env" << 'EOF'
# TAK-ADSB-Feeder v2.0 Configuration
FEEDER_TZ=UTC
FEEDER_LAT=0.0
FEEDER_LONG=0.0
FEEDER_ALT_M=0
MLAT_SITE_NAME=MyFeeder
MLAT_SITE_NAME_SANITIZED=MyFeeder
_IS_BASE_CONFIG_FINISHED=True

# Readsb
FEEDER_RTL_SDR=rtlsdr
FEEDER_READSB_DEVICE=0
FEEDER_READSB_GAIN=autogain
MLAT_ENABLE=True

# Aggregators
AF_IS_FR24_ENABLED=false
AF_IS_ADSBX_ENABLED=false
AF_IS_AIRPLANESLIVE_ENABLED=false
AF_IS_RADARBOX_ENABLED=false
AF_IS_PLANEFINDER_ENABLED=false

# Credentials
FEEDER_FR24_SHARING_KEY=
FEEDER_ADSBX_UUID=
FEEDER_AIRPLANESLIVE_UUID=
FEEDER_RADARBOX_SHARING_KEY=
FEEDER_PLANEFINDER_SHARECODE=
EOF
    print_success "Created .env configuration"
    
    # Create base docker-compose.yml
    cat > "$CONFIG_DIR/docker-compose.yml" << 'EOF'
version: '3.8'
networks:
  adsb_bridge:
    driver: bridge
services:
  # Base - actual services loaded from aggregators/*.yml
  placeholder:
    image: hello-world
    container_name: placeholder
    restart: "no"
    networks:
      - adsb_bridge
EOF
    print_success "Created docker-compose.yml"
    
    # Create docker.image.versions
    cat > "$BASE_DIR/docker.image.versions" << 'EOF'
FR24_CONTAINER=ghcr.io/sdr-enthusiasts/docker-flightradar24:latest
ADSBX_CONTAINER=ghcr.io/sdr-enthusiasts/docker-adsbexchange:latest
RB_CONTAINER=ghcr.io/sdr-enthusiasts/docker-airnavradar:latest
PF_CONTAINER=ghcr.io/sdr-enthusiasts/docker-planefinder:latest
OS_CONTAINER=ghcr.io/sdr-enthusiasts/docker-opensky-network:latest
EOF
    print_success "Created docker.image.versions"
}

copy_production_files() {
    print_header "Copying Production Files"
    
    SCRIPT_DIR_SOURCE="."
    
    # Check if we're running from the extracted directory
    if [ ! -f "docker-compose-adsb" ]; then
        print_error "docker-compose-adsb not found in current directory"
        print_error "Please run this script from the 'updated' directory"
        exit 1
    fi
    
    # Copy scripts
    echo "Copying scripts..."
    cp docker-compose-adsb $BASE_DIR/scripts/
    cp default.docker-compose $CONFIG_DIR/
    chmod +x $BASE_DIR/scripts/docker-compose-adsb
    print_success "Scripts copied"
    
    # Copy Docker config
    echo "Copying Docker configuration..."
    cp docker.image.versions $BASE_DIR/
    print_success "Docker configuration copied"
    
    # Copy Python files
    echo "Copying Python files..."
    if [ -f "docker_manager.py" ]; then
        cp docker_manager.py $WEB_DIR/
        cp aggregator_status.py $WEB_DIR/
        cp app.py $WEB_DIR/
        print_success "Python files copied"
    else
        print_warning "Python files not found in current directory"
        print_warning "You'll need to copy them manually later"
    fi
    
    # Copy aggregator compose files if available
    if [ -d "../aggregators" ]; then
        echo "Copying aggregator compose files..."
        cp ../aggregators/*.yml $CONFIG_DIR/aggregators/
        print_success "Aggregator files copied"
    else
        print_warning "Aggregator files not found at ../aggregators/"
        print_warning "Copy them manually: sudo cp aggregators/*.yml $CONFIG_DIR/aggregators/"
    fi
}

create_systemd_service() {
    print_header "Creating Systemd Service"
    
    cat > /etc/systemd/system/tak-adsb-docker.service << 'EOF'
[Unit]
Description=TAK-ADSB-Feeder Docker Aggregators
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/opt/TAK_ADSB/scripts/docker-compose-adsb up -d
ExecStop=/opt/TAK_ADSB/scripts/docker-compose-adsb down
ExecReload=/opt/TAK_ADSB/scripts/docker-compose-adsb up -d
Restart=on-failure
RestartSec=10
User=root
Group=root

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable tak-adsb-docker.service
    
    print_success "Systemd service created and enabled"
}

set_permissions() {
    print_header "Setting Permissions"
    
    if [ "$SUDO_USER" ]; then
        chown -R $SUDO_USER:$SUDO_USER $BASE_DIR
        print_success "Set ownership to $SUDO_USER"
    fi
    
    chmod +x $SCRIPT_DIR/*.sh 2>/dev/null || true
    
    print_success "Permissions set"
}

print_summary() {
    print_header "Installation Complete!"
    
    cat << EOF
${GREEN}TAK-ADSB-Feeder v2.0 installed successfully!${NC}

${YELLOW}Next Steps:${NC}

1. ${BLUE}Configure your location:${NC}
   ${YELLOW}sudo nano $CONFIG_DIR/.env${NC}
   
   Set these values:
   - FEEDER_LAT=33.5539
   - FEEDER_LONG=-117.2139
   - FEEDER_ALT_M=304
   - FEEDER_TZ=America/Los_Angeles
   - MLAT_SITE_NAME=YourFeederName

2. ${BLUE}Add aggregator credentials:${NC}
   Still in .env, enable and configure aggregators:
   
   - AF_IS_FR24_ENABLED=true
   - FEEDER_FR24_SHARING_KEY=your_key_here
   
   - AF_IS_ADSBX_ENABLED=true
   - FEEDER_ADSBX_UUID=your_uuid_here

3. ${BLUE}Start Docker services:${NC}
   ${YELLOW}sudo systemctl start tak-adsb-docker${NC}

4. ${BLUE}Check container status:${NC}
   ${YELLOW}docker ps${NC}
   ${YELLOW}docker logs fr24${NC}

5. ${BLUE}Start Flask web interface:${NC}
   ${YELLOW}cd $WEB_DIR${NC}
   ${YELLOW}python3 app.py${NC}
   
   Access at: http://$(hostname -I | awk '{print $1}'):5000

${YELLOW}Useful Commands:${NC}
   Start:    ${BLUE}sudo systemctl start tak-adsb-docker${NC}
   Stop:     ${BLUE}sudo systemctl stop tak-adsb-docker${NC}
   Restart:  ${BLUE}sudo systemctl restart tak-adsb-docker${NC}
   Status:   ${BLUE}docker ps${NC}
   Logs:     ${BLUE}docker logs <container>${NC}

${GREEN}Happy feeding!${NC}
EOF
}

main() {
    print_header "TAK-ADSB-Feeder v2.0 Production Installation"
    
    check_root
    check_system
    install_docker
    install_docker_compose
    create_directories
    install_python_deps
    create_config_files
    copy_production_files
    create_systemd_service
    set_permissions
    print_summary
}

main "$@"
