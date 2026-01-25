#!/bin/bash
# TAKNET-PS WiFi Connection Manager
# Handles automatic WiFi hotspot fallback when no network connectivity

HOTSPOT_SSID="TAKNET-PS"
HOTSPOT_IP="10.42.0.1"
HOTSPOT_INTERFACE="wlan0"
CONNECTIVITY_CHECK_HOST="8.8.8.8"
STATE_FILE="/opt/adsb/config/.wifi-state"
CONFIG_DIR="/opt/adsb/config"

# Function to check internet connectivity
check_connectivity() {
    # Check multiple targets to avoid false negatives
    ping -c 1 -W 2 8.8.8.8 &>/dev/null && return 0
    ping -c 1 -W 2 1.1.1.1 &>/dev/null && return 0
    ping -c 1 -W 2 208.67.222.222 &>/dev/null && return 0
    return 1
}

# Function to check if connected to WiFi
check_wifi_connected() {
    # Check if wlan0 has an IP and a default route
    ip addr show $HOTSPOT_INTERFACE | grep -q "inet " && \
    ip route | grep -q "default.*$HOTSPOT_INTERFACE" && \
    return 0
    return 1
}

# Function to start hotspot mode
start_hotspot() {
    echo "$(date): Starting WiFi hotspot mode..." | tee -a /var/log/taknet-wifi.log
    
    # Stop NetworkManager to prevent conflicts
    systemctl stop NetworkManager
    
    # Configure static IP on wlan0
    ip link set $HOTSPOT_INTERFACE down
    ip addr flush dev $HOTSPOT_INTERFACE
    ip addr add ${HOTSPOT_IP}/24 dev $HOTSPOT_INTERFACE
    ip link set $HOTSPOT_INTERFACE up
    
    # Configure hostapd
    cat > /etc/hostapd/hostapd.conf << EOF
interface=$HOTSPOT_INTERFACE
driver=nl80211
ssid=$HOTSPOT_SSID
hw_mode=g
channel=6
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
EOF
    
    # Configure dnsmasq for DHCP and DNS
    cat > /etc/dnsmasq.d/taknet-hotspot.conf << EOF
interface=$HOTSPOT_INTERFACE
dhcp-range=10.42.0.10,10.42.0.100,255.255.255.0,12h
dhcp-option=3,$HOTSPOT_IP
dhcp-option=6,$HOTSPOT_IP
address=/#/$HOTSPOT_IP
EOF
    
    # Start services
    systemctl stop dnsmasq
    systemctl start dnsmasq
    systemctl start hostapd
    
    # Update state file
    echo "hotspot" > $STATE_FILE
    
    echo "$(date): WiFi hotspot '$HOTSPOT_SSID' started at $HOTSPOT_IP" | tee -a /var/log/taknet-wifi.log
}

# Function to stop hotspot and try connecting to WiFi
stop_hotspot() {
    echo "$(date): Stopping WiFi hotspot..." | tee -a /var/log/taknet-wifi.log
    
    systemctl stop hostapd
    systemctl stop dnsmasq
    
    # Remove dnsmasq config
    rm -f /etc/dnsmasq.d/taknet-hotspot.conf
    
    # Restart NetworkManager to handle WiFi
    systemctl start NetworkManager
    
    echo "normal" > $STATE_FILE
}

# Function to attempt WiFi connection
try_wifi_connection() {
    local ssid="$1"
    local password="$2"
    
    echo "$(date): Attempting to connect to WiFi: $ssid" | tee -a /var/log/taknet-wifi.log
    
    # Stop hotspot first
    stop_hotspot
    
    # Wait for NetworkManager to initialize
    sleep 3
    
    # Use nmcli to connect
    if [ -n "$password" ]; then
        nmcli dev wifi connect "$ssid" password "$password"
    else
        nmcli dev wifi connect "$ssid"
    fi
    
    # Wait for connection
    sleep 5
    
    # Verify connectivity
    if check_connectivity; then
        echo "$(date): Successfully connected to $ssid" | tee -a /var/log/taknet-wifi.log
        echo "connected" > $STATE_FILE
        return 0
    else
        echo "$(date): Failed to connect to $ssid" | tee -a /var/log/taknet-wifi.log
        return 1
    fi
}

# Main logic
case "${1:-check}" in
    check)
        # Check current state
        if [ -f "$STATE_FILE" ]; then
            CURRENT_STATE=$(cat $STATE_FILE)
        else
            CURRENT_STATE="unknown"
        fi
        
        # Check if we have connectivity
        if check_connectivity; then
            echo "$(date): Network connectivity OK" >> /var/log/taknet-wifi.log
            
            # If we're in hotspot mode but now have connectivity, something connected us
            # Keep the connection but log it
            if [ "$CURRENT_STATE" = "hotspot" ]; then
                echo "$(date): Network restored, disabling hotspot" | tee -a /var/log/taknet-wifi.log
                systemctl stop hostapd
                systemctl stop dnsmasq
                echo "connected" > $STATE_FILE
            fi
            exit 0
        fi
        
        # No connectivity - check if we should start hotspot
        echo "$(date): No network connectivity detected" | tee -a /var/log/taknet-wifi.log
        
        # Start hotspot mode
        start_hotspot
        ;;
    
    connect)
        # Called by web UI to connect to WiFi
        # Expects: /opt/adsb/config/.wifi-credentials with SSID and PASSWORD
        if [ ! -f "$CONFIG_DIR/.wifi-credentials" ]; then
            echo "Error: No WiFi credentials found"
            exit 1
        fi
        
        source "$CONFIG_DIR/.wifi-credentials"
        
        if try_wifi_connection "$WIFI_SSID" "$WIFI_PASSWORD"; then
            # Success - schedule reboot
            rm -f "$CONFIG_DIR/.wifi-credentials"
            echo "$(date): WiFi connection successful, rebooting..." | tee -a /var/log/taknet-wifi.log
            sleep 1
            reboot
        else
            # Failed - restart hotspot
            echo "$(date): WiFi connection failed, restarting hotspot..." | tee -a /var/log/taknet-wifi.log
            start_hotspot
            exit 1
        fi
        ;;
    
    start-hotspot)
        start_hotspot
        ;;
    
    stop-hotspot)
        stop_hotspot
        ;;
    
    *)
        echo "Usage: $0 {check|connect|start-hotspot|stop-hotspot}"
        exit 1
        ;;
esac
