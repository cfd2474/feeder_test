#!/bin/bash

# TAKNET-PS v2.40.6 Web Update Script
# Updates web interface to v2.40.6 with real-time Docker progress monitoring

set -e

INSTALL_DIR="/opt/adsb"
BACKUP_DIR="${INSTALL_DIR}/web.backup.$(date +%Y%m%d-%H%M%S)"

echo "======================================"
echo "TAKNET-PS v2.40.6 Web Update"
echo "======================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Error: This script must be run as root"
    echo "   Please run: sudo bash update_web.sh"
    exit 1
fi

# Check if installation exists
if [ ! -d "$INSTALL_DIR/web" ]; then
    echo "❌ Error: TAKNET-PS not found at $INSTALL_DIR"
    echo "   Expected directory: $INSTALL_DIR/web"
    exit 1
fi

# Backup current installation
echo "📦 Creating backup..."
cp -r "$INSTALL_DIR/web" "$BACKUP_DIR"
echo "   Backup created: $BACKUP_DIR"
echo ""

# Stop web service
echo "⏸️  Stopping web service..."
systemctl stop adsb-web.service
echo ""

# Install new files
echo "📥 Installing v2.40.6..."
cp -r web/* "$INSTALL_DIR/web/"
echo "   Files copied to $INSTALL_DIR/web/"
echo ""

# Verify installation
echo "🔍 Verifying installation..."
if python3 -m py_compile "$INSTALL_DIR/web/app.py" 2>/dev/null; then
    echo "   ✅ No syntax errors detected"
else
    echo "   ❌ Syntax error in app.py!"
    echo "   Rolling back..."
    rm -rf "$INSTALL_DIR/web"
    cp -r "$BACKUP_DIR" "$INSTALL_DIR/web"
    systemctl start adsb-web.service
    echo "   Rollback complete"
    exit 1
fi

# Check version
VERSION=$(grep "^VERSION = " "$INSTALL_DIR/web/app.py" | cut -d'"' -f2)
echo "   Version installed: $VERSION"
echo ""

# Start web service
echo "▶️  Starting web service..."
systemctl start adsb-web.service
sleep 2
echo ""

# Verify service started
if systemctl is-active --quiet adsb-web.service; then
    echo "======================================"
    echo "✅ UPDATE SUCCESSFUL!"
    echo "======================================"
    echo ""
    echo "Version: $VERSION"
    echo "Backup: $BACKUP_DIR"
    echo ""
    echo "🎉 New Features:"
    echo "   • Real-time Docker progress monitoring"
    echo "   • No more timeout errors during setup"
    echo "   • Shows actual download progress (MB/GB)"
    echo "   • Professional progress indicators"
    echo ""
    echo "🧪 Test It:"
    echo "   1. Open web interface"
    echo "   2. Go to Settings page"
    echo "   3. Click 'Save & Start'"
    echo "   4. Watch the real-time progress!"
    echo ""
    echo "📊 Service Status:"
    systemctl status adsb-web.service --no-pager -l | head -10
else
    echo "======================================"
    echo "❌ UPDATE FAILED"
    echo "======================================"
    echo ""
    echo "Web service did not start properly."
    echo ""
    echo "Checking logs:"
    journalctl -u adsb-web.service -n 20 --no-pager
    echo ""
    echo "Rolling back to backup..."
    systemctl stop adsb-web.service
    rm -rf "$INSTALL_DIR/web"
    cp -r "$BACKUP_DIR" "$INSTALL_DIR/web"
    systemctl start adsb-web.service
    echo "Rollback complete"
    exit 1
fi
