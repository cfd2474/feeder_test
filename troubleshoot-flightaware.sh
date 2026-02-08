#!/bin/bash
# FlightAware Feeder ID Troubleshooting Script
# This script diagnoses why Feeder ID generation is timing out

set -e

echo "=========================================="
echo "FLIGHTAWARE FEEDER ID TROUBLESHOOTING"
echo "=========================================="
echo ""

# Check if running on the Pi
if [ ! -f /opt/adsb/.env ]; then
    echo "❌ ERROR: Not running on the Pi or /opt/adsb/.env not found"
    echo "Please run this script ON YOUR PI, not in Claude's environment"
    exit 1
fi

echo "Step 1: Checking your configuration"
echo "=========================================="
source /opt/adsb/.env

if [ -z "$FEEDER_LAT" ] || [ -z "$FEEDER_LONG" ]; then
    echo "❌ ERROR: Coordinates not set in .env"
    echo ""
    echo "Found:"
    echo "  FEEDER_LAT='$FEEDER_LAT'"
    echo "  FEEDER_LONG='$FEEDER_LONG'"
    echo ""
    echo "You need to set these in /opt/adsb/.env first!"
    exit 1
fi

echo "✓ Coordinates configured:"
echo "  Latitude:  $FEEDER_LAT"
echo "  Longitude: $FEEDER_LONG"
echo ""

echo "Step 2: Checking Docker availability"
echo "=========================================="
if ! command -v docker &> /dev/null; then
    echo "❌ ERROR: Docker not found or not in PATH"
    exit 1
fi
echo "✓ Docker is available"
echo ""

echo "Step 3: Checking network connectivity to FlightAware"
echo "=========================================="

# Check DNS resolution
echo -n "  DNS resolution for piaware.flightaware.com... "
if nslookup piaware.flightaware.com >/dev/null 2>&1; then
    echo "✓"
    FA_IP=$(nslookup piaware.flightaware.com | grep -A1 "Name:" | grep "Address:" | awk '{print $2}' | head -1)
    echo "    Resolved to: $FA_IP"
else
    echo "❌ FAILED"
    echo ""
    echo "Cannot resolve piaware.flightaware.com"
    echo "This means your DNS is not working properly."
    echo ""
    echo "Try setting DNS servers in /etc/resolv.conf:"
    echo "  nameserver 8.8.8.8"
    echo "  nameserver 1.1.1.1"
    exit 1
fi

# Check ICMP connectivity
echo -n "  Ping test to FlightAware servers... "
if ping -c 2 piaware.flightaware.com >/dev/null 2>&1; then
    echo "✓"
else
    echo "⚠️  FAILED (not critical, but may indicate network issues)"
fi

# Check port 1200 (PiAware registration port)
echo -n "  Port 1200 connectivity test... "
if timeout 5 bash -c "cat < /dev/null > /dev/tcp/piaware.flightaware.com/1200" 2>/dev/null; then
    echo "✓"
else
    echo "❌ FAILED"
    echo ""
    echo "Cannot connect to piaware.flightaware.com:1200"
    echo "This is the port FlightAware uses for feeder registration."
    echo ""
    echo "Possible causes:"
    echo "  1. Firewall blocking outbound connections"
    echo "  2. ISP blocking the port"
    echo "  3. Network issue"
    echo ""
    echo "This is likely why your Feeder ID generation is timing out."
    exit 1
fi
echo ""

echo "Step 4: Checking Docker image availability"
echo "=========================================="
echo "Pulling latest PiAware image (this may take 30-60 seconds)..."
if docker pull ghcr.io/sdr-enthusiasts/docker-piaware:latest; then
    echo "✓ Image pulled successfully"
else
    echo "❌ Failed to pull image"
    echo "Check your internet connection and Docker configuration"
    exit 1
fi
echo ""

echo "Step 5: Running OFFICIAL FlightAware method (30 second test)"
echo "=========================================="
echo "This is the exact command from the official sdr-enthusiasts docs:"
echo ""
echo "  timeout 30 docker run --rm -e LAT=\"\$FEEDER_LAT\" -e LONG=\"\$FEEDER_LONG\" \\"
echo "    ghcr.io/sdr-enthusiasts/docker-piaware:latest | grep \"my feeder ID\""
echo ""
echo "Starting container and waiting up to 30 seconds..."
echo "----------------------------------------"

# Capture full output
TEMP_LOG="/tmp/piaware-test-$$.log"
timeout 30 docker run --rm \
    -e LAT="$FEEDER_LAT" \
    -e LONG="$FEEDER_LONG" \
    ghcr.io/sdr-enthusiasts/docker-piaware:latest 2>&1 | tee "$TEMP_LOG"

echo ""
echo "=========================================="
echo "Step 6: Analyzing results"
echo "=========================================="

# Check if we got a feeder ID
FEEDER_ID=$(grep -i "my feeder ID is" "$TEMP_LOG" | grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' | head -1)

if [ -n "$FEEDER_ID" ]; then
    echo ""
    echo "✅ SUCCESS! Feeder ID generated:"
    echo ""
    echo "    $FEEDER_ID"
    echo ""
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "1. Copy the Feeder ID above"
    echo "2. Claim it at: https://flightaware.com/adsb/piaware/claim/$FEEDER_ID"
    echo "3. Or enter it in TAKNET-PS web interface"
    echo ""
    
    # Offer to save it
    read -p "Save this Feeder ID to /opt/adsb/.env? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if grep -q "^PIAWARE_FEEDER_ID=" /opt/adsb/.env; then
            sed -i "s|^PIAWARE_FEEDER_ID=.*|PIAWARE_FEEDER_ID=$FEEDER_ID|" /opt/adsb/.env
        else
            echo "PIAWARE_FEEDER_ID=$FEEDER_ID" >> /opt/adsb/.env
        fi
        echo "✓ Saved to /opt/adsb/.env"
    fi
    
else
    echo "❌ No Feeder ID found in output"
    echo ""
    echo "Full container output:"
    echo "----------------------------------------"
    cat "$TEMP_LOG"
    echo "----------------------------------------"
    echo ""
    echo "DIAGNOSIS:"
    echo ""
    
    # Check for specific error patterns
    if grep -qi "timeout" "$TEMP_LOG"; then
        echo "⚠️  Container timed out after 30 seconds"
        echo ""
        echo "The official docs say 30 seconds should be enough."
        echo "This suggests a problem with network connectivity to FlightAware."
        echo ""
        echo "Even though we passed the port 1200 test above, the actual"
        echo "registration process may be taking too long."
        echo ""
        echo "RECOMMENDATION: Try the manual website method instead:"
        echo "  1. Go to: https://flightaware.com/adsb/piaware/claim"
        echo "  2. Enter coordinates: Lat $FEEDER_LAT, Lon $FEEDER_LONG"
        echo "  3. Get your Feeder ID from FlightAware"
        echo "  4. Enter it manually in TAKNET-PS"
        
    elif grep -qi "connection refused\|network\|unreachable" "$TEMP_LOG"; then
        echo "⚠️  Network connection problem detected"
        echo ""
        echo "The container cannot reach FlightAware servers."
        echo "Check firewall rules and network configuration."
        
    elif grep -qi "error\|failed\|cannot" "$TEMP_LOG"; then
        echo "⚠️  Container reported an error"
        echo ""
        echo "See the output above for specific error messages."
        
    else
        echo "⚠️  Container ran but didn't generate a Feeder ID"
        echo ""
        echo "This is unusual. Possible causes:"
        echo "  1. FlightAware servers are experiencing issues"
        echo "  2. Rate limiting (too many requests from your IP)"
        echo "  3. Invalid coordinates"
        echo ""
        echo "RECOMMENDATION: Wait 15 minutes and try again, or use"
        echo "the manual website method:"
        echo "  https://flightaware.com/adsb/piaware/claim"
    fi
fi

echo ""
echo "=========================================="
echo "Troubleshooting complete!"
echo "=========================================="
echo ""
echo "Log saved to: $TEMP_LOG"

rm -f "$TEMP_LOG"
