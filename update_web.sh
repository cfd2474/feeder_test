#!/bin/bash
# Quick Web App Update Script for v2.38.2
# Updates only the web interface without touching Docker containers

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  TAKNET-PS Web App Update to v2.38.2"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run as root: sudo bash update_web.sh"
    exit 1
fi

# Backup current web directory
echo "Backing up current web app..."
if [ -d /opt/adsb/web ]; then
    cp -r /opt/adsb/web /opt/adsb/web.backup.$(date +%Y%m%d-%H%M%S)
    echo "Backup created"
else
    echo "WARNING: Web directory not found, creating fresh install"
fi

# Stop web service
echo ""
echo "Stopping web service..."
systemctl stop adsb-web.service

# Update web app files
echo "Updating web app files..."
if [ -d ./web ]; then
    # Update main app
    echo "  - Copying app.py..."
    cp ./web/app.py /opt/adsb/web/
    
    # Update templates individually
    echo "  - Copying templates..."
    cp ./web/templates/dashboard.html /opt/adsb/web/templates/
    cp ./web/templates/feeds.html /opt/adsb/web/templates/
    cp ./web/templates/feeds-account-required.html /opt/adsb/web/templates/
    cp ./web/templates/settings.html /opt/adsb/web/templates/
    cp ./web/templates/logs.html /opt/adsb/web/templates/
    cp ./web/templates/setup.html /opt/adsb/web/templates/
    cp ./web/templates/setup-sdr.html /opt/adsb/web/templates/
    cp ./web/templates/loading.html /opt/adsb/web/templates/
    
    # Update static files
    echo "  - Copying static files..."
    cp -r ./web/static/* /opt/adsb/web/static/
    
    echo "Files updated successfully"
else
    echo "ERROR: web directory not found"
    echo "Are you running this from the extracted package directory?"
    exit 1
fi

# Set permissions
echo "Setting permissions..."
chown -R adsb:adsb /opt/adsb/web
chmod +x /opt/adsb/web/app.py

# Restart the web service
echo "Restarting web service..."
systemctl restart adsb-web.service

# Wait for service to start
sleep 2

# Check status
if systemctl is-active --quiet adsb-web.service; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Update Complete!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Access your updated interface:"
    echo "   http://taknet-ps.local:5000"
    echo ""
    echo "New in v2.38.2:"
    echo "   • Smart FR24 setup: single field detects email or key"
    echo "   • Enter email → auto-registers and populates key"
    echo "   • Enter key → uses it directly"
    echo "   • Proper coordinate formatting (4 decimal places)"
    echo "   • Simpler UX like adsb.im"
    echo ""
else
    echo ""
    echo "WARNING: Web service failed to start"
    echo "Check logs: sudo journalctl -u adsb-web.service -n 50"
    echo ""
    echo "To restore backup:"
    echo "   sudo systemctl stop adsb-web.service"
    echo "   sudo rm -rf /opt/adsb/web"
    echo "   sudo cp -r /opt/adsb/web.backup.* /opt/adsb/web"
    echo "   sudo systemctl restart adsb-web.service"
    exit 1
fi

echo "Done!"
