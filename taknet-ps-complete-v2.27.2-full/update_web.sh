#!/bin/bash
# Quick Web App Update Script for v2.9.0
# Updates only the web interface without touching Docker containers

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  TAKNET-PS Web App Update to v2.9.0"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root: sudo bash update_web.sh"
    exit 1
fi

# Backup current web directory
echo "📦 Backing up current web app..."
if [ -d /opt/adsb/web ]; then
    cp -r /opt/adsb/web /opt/adsb/web.backup.$(date +%Y%m%d-%H%M%S)
    echo "✓ Backup created"
else
    echo "⚠️  Web directory not found, creating fresh install"
fi

# Download the complete package
echo ""
echo "⬇️  Downloading v2.9.0..."
cd /tmp
curl -fsSL https://github.com/cfd2474/feeder_test/raw/main/taknet-ps-complete-v2.9.0.tar.gz -o taknet-ps-v2.9.0.tar.gz

# Extract
echo "📂 Extracting files..."
tar -xzf taknet-ps-v2.9.0.tar.gz

# Update only the web directory
echo "🔄 Updating web app files..."
if [ -d /opt/adsb/web ]; then
    rm -rf /opt/adsb/web
fi
cp -r taknet-ps-complete-v2.9.0/web /opt/adsb/

# Set permissions
echo "🔐 Setting permissions..."
chown -R adsb:adsb /opt/adsb/web
chmod +x /opt/adsb/web/app.py

# Restart the web service
echo "🔄 Restarting web service..."
systemctl restart adsb-web.service

# Wait for service to start
sleep 2

# Check status
if systemctl is-active --quiet adsb-web.service; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  ✅ Update Complete!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "🌐 Access your updated interface:"
    echo "   http://taknet-ps.local:5000"
    echo ""
    echo "✨ New in v2.9.0:"
    echo "   • Blank location fields with validation"
    echo "   • Zip code priority system"
    echo "   • Network status display"
    echo "   • Full-screen status overlays"
    echo "   • New Logs tab"
    echo ""
else
    echo ""
    echo "⚠️  Web service failed to start"
    echo "Check logs: sudo journalctl -u adsb-web.service -n 50"
    echo ""
    echo "To restore backup:"
    echo "   sudo rm -rf /opt/adsb/web"
    echo "   sudo cp -r /opt/adsb/web.backup.* /opt/adsb/web"
    echo "   sudo systemctl restart adsb-web.service"
    exit 1
fi

# Cleanup
rm -rf /tmp/taknet-ps-v2.9.0.tar.gz /tmp/taknet-ps-complete-v2.9.0

echo "Done!"
