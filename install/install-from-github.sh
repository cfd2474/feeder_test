#!/bin/bash
# TAK-ADSB-Feeder Installation Script
# Fetches files from GitHub and installs

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
GITHUB_REPO="https://raw.githubusercontent.com/cfd2474/feeder_test/main"
TEMP_DIR="/tmp/tak-adsb-install"

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
    
    if python3 -c "import flask, psutil" 2>/dev/null; then
        print_success "Flask and psutil already installed"
        return 0
    fi
    
    if command -v apt-get &> /dev/null; then
        echo "Installing via apt..."
        apt-get update -qq
        apt-get install -y python3-flask python3-psutil 2>/dev/null || {
            print_warning "apt install failed, trying pip3..."
            
            if ! command -v pip3 &> /dev/null; then
                echo "Installing pip3..."
                apt-get install -y python3-pip
            fi
            
            pip3 install flask psutil --break-system-packages 2>/dev/null || \
                pip3 install flask psutil
        }
    fi
    
    if python3 -c "import flask, psutil" 2>/dev/null; then
        print_success "Python dependencies installed"
    else
        print_error "Failed to install Python dependencies"
        exit 1
    fi
}

download_files() {
    print_header "Downloading Files from GitHub"
    
    mkdir -p $TEMP_DIR
    cd $TEMP_DIR
    
    echo "Downloading scripts..."
    wget -q $GITHUB_REPO/scripts/docker-compose-adsb -O docker-compose-adsb
    wget -q $GITHUB_REPO/scripts/default.docker-compose -O default.docker-compose
    
    echo "Downloading config files..."
    wget -q $GITHUB_REPO/config/docker-compose.yml -O docker-compose.yml
    wget -q $GITHUB_REPO/config/docker.image.versions -O docker.image.versions
    wget -q $GITHUB_REPO/config/env-template -O env-template
    
    echo "Downloading aggregator configs..."
    mkdir -p aggregators
    for agg in fr24 adsbx airplaneslive radarbox planefinder openskynetwork; do
        wget -q $GITHUB_REPO/config/aggregators/${agg}.yml -O aggregators/${agg}.yml
    done
    
    echo "Downloading Python files..."
    wget -q $GITHUB_REPO/web/docker_manager.py -O docker_manager.py
    wget -q $GITHUB_REPO/web/aggregator_status.py -O aggregator_status.py
    wget -q $GITHUB_REPO/web/app.py -O app.py
    
    print_success "All files downloaded"
}

install_files() {
    print_header "Installing Files"
    
    cd $TEMP_DIR
    
    # Scripts
    cp docker-compose-adsb $SCRIPT_DIR/
    cp default.docker-compose $SCRIPT_DIR/
    chmod +x $SCRIPT_DIR/docker-compose-adsb
    print_success "Scripts installed"
    
    # Config
    cp docker-compose.yml $CONFIG_DIR/
    cp docker.image.versions $BASE_DIR/
    cp env-template $CONFIG_DIR/.env
    print_success "Configuration installed"
    
    # Aggregators
    cp aggregators/*.yml $CONFIG_DIR/aggregators/
    print_success "Aggregator configs installed"
    
    # Python
    cp docker_manager.py $WEB_DIR/
    cp aggregator_status.py $WEB_DIR/
    cp app.py $WEB_DIR/
    print_success "Python files installed"
    
    # Cleanup
    cd /
    rm -rf $TEMP_DIR
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
    
    print_success "Systemd service created"
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
${GREEN}TAK-ADSB-Feeder installed successfully!${NC}

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
   Enable and configure aggregators in .env:
   
   - AF_IS_FR24_ENABLED=true
   - FEEDER_FR24_SHARING_KEY=your_key
   
   - AF_IS_ADSBX_ENABLED=true
   - FEEDER_ADSBX_UUID=your_uuid

3. ${BLUE}Start Docker services:${NC}
   ${YELLOW}sudo systemctl start tak-adsb-docker${NC}

4. ${BLUE}Check status:${NC}
   ${YELLOW}docker ps${NC}
   ${YELLOW}docker logs fr24${NC}

5. ${BLUE}Start Flask API:${NC}
   ${YELLOW}cd $WEB_DIR && python3 app.py${NC}

${YELLOW}Useful Commands:${NC}
   Start:    ${BLUE}sudo systemctl start tak-adsb-docker${NC}
   Stop:     ${BLUE}sudo systemctl stop tak-adsb-docker${NC}
   Restart:  ${BLUE}sudo systemctl restart tak-adsb-docker${NC}
   Status:   ${BLUE}docker ps${NC}

${GREEN}Happy feeding!${NC}
EOF
}

main() {
    print_header "TAK-ADSB-Feeder Installation"
    
    check_root
    check_system
    install_docker
    install_docker_compose
    create_directories
    install_python_deps
    download_files
    install_files
    create_systemd_service
    set_permissions
    print_summary
}

main "$@"
