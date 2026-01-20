#!/bin/bash
# TAKNET-PS Auto-Start Configuration Script
# Ensures web UI starts automatically on boot

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  TAKNET-PS Auto-Start Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ This script must be run with sudo"
    echo ""
    echo "Usage: sudo bash auto-start-setup.sh"
    exit 1
fi

echo "Checking current configuration..."
echo ""

# Check if service exists
if [ -f /etc/systemd/system/adsb-web.service ]; then
    echo "✓ Service file exists"
else
    echo "❌ Service file not found at /etc/systemd/system/adsb-web.service"
    exit 1
fi

# Check if service is enabled
if systemctl is-enabled adsb-web.service &>/dev/null; then
    echo "✓ Service is enabled (will start on boot)"
else
    echo "⚠ Service is NOT enabled (will not start on boot)"
    echo ""
    read -p "Enable service now? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        systemctl enable adsb-web.service
        echo "✓ Service enabled"
    fi
fi

# Check if service is running
if systemctl is-active adsb-web.service &>/dev/null; then
    echo "✓ Service is currently running"
else
    echo "⚠ Service is not running"
    echo ""
    read -p "Start service now? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        systemctl start adsb-web.service
        sleep 2
        if systemctl is-active adsb-web.service &>/dev/null; then
            echo "✓ Service started successfully"
        else
            echo "❌ Failed to start service"
            echo ""
            echo "Check logs with: sudo journalctl -u adsb-web -n 50"
        fi
    fi
fi

# Check ultrafeeder service
echo ""
echo "Checking ultrafeeder service..."

if systemctl is-enabled ultrafeeder.service &>/dev/null; then
    echo "✓ Ultrafeeder is enabled (will start on boot)"
else
    echo "⚠ Ultrafeeder is NOT enabled"
    echo ""
    read -p "Enable ultrafeeder service? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        systemctl enable ultrafeeder.service
        echo "✓ Ultrafeeder enabled"
    fi
fi

# Get IP address
IP=$(hostname -I | awk '{print $1}')

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Configuration Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Services that will start on boot:"
systemctl is-enabled adsb-web.service &>/dev/null && echo "  ✓ adsb-web" || echo "  ✗ adsb-web (not enabled)"
systemctl is-enabled ultrafeeder.service &>/dev/null && echo "  ✓ ultrafeeder" || echo "  ✗ ultrafeeder (not enabled)"
systemctl is-enabled docker.service &>/dev/null && echo "  ✓ docker" || echo "  ✗ docker (not enabled)"

echo ""
echo "Services currently running:"
systemctl is-active adsb-web.service &>/dev/null && echo "  ✓ adsb-web" || echo "  ✗ adsb-web (not running)"
systemctl is-active ultrafeeder.service &>/dev/null && echo "  ✓ ultrafeeder" || echo "  ✗ ultrafeeder (not running)"
systemctl is-active docker.service &>/dev/null && echo "  ✓ docker" || echo "  ✗ docker (not running)"

echo ""
echo "Web UI will be available at:"
echo "  http://$IP:5000"
echo ""

# Test reboot behavior
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Test Auto-Start (Optional)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "To verify auto-start works:"
echo "  1. sudo reboot"
echo "  2. Wait 2-3 minutes for boot"
echo "  3. Open http://$IP:5000"
echo ""
echo "If web UI doesn't load after reboot:"
echo "  sudo systemctl status adsb-web"
echo "  sudo journalctl -u adsb-web -n 50"
echo ""

# Offer to reboot
read -p "Reboot now to test auto-start? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Rebooting in 5 seconds... (Ctrl+C to cancel)"
    sleep 5
    reboot
fi

echo ""
echo "✓ Configuration complete!"
echo ""
