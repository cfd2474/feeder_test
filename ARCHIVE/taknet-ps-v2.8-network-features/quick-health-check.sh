#!/bin/bash
# Quick Pi Health Check

echo "════════════════════════════════════════════"
echo "  TAKNET-PS System Health Check"
echo "════════════════════════════════════════════"
echo ""

# Memory
echo "📊 MEMORY:"
FREE_MEM=$(free -m | awk 'NR==2{printf "%dMB / %dMB (%.1f%% used)", $3, $2, $3*100/$2}')
echo "  $FREE_MEM"
FREE_MB=$(free -m | awk 'NR==2{print $4}')
if [ $FREE_MB -lt 100 ]; then
    echo "  ⚠️  WARNING: Less than 100MB free!"
fi
echo ""

# CPU Load
echo "💻 CPU LOAD:"
LOAD=$(uptime | awk -F'load average:' '{print $2}')
echo "  Load average:$LOAD"
LOAD1=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
if (( $(echo "$LOAD1 > 2.0" | bc -l) )); then
    echo "  ⚠️  WARNING: High CPU load!"
fi
echo ""

# Temperature
echo "🌡️  TEMPERATURE:"
if command -v vcgencmd &> /dev/null; then
    TEMP=$(vcgencmd measure_temp)
    echo "  $TEMP"
    TEMP_NUM=$(echo $TEMP | grep -o '[0-9]*\.[0-9]*' | head -1)
    if (( $(echo "$TEMP_NUM > 70.0" | bc -l) )); then
        echo "  ⚠️  WARNING: High temperature!"
    fi
else
    echo "  Not available (not on Pi?)"
fi
echo ""

# Disk Space
echo "💾 DISK SPACE:"
DISK=$(df -h / | awk 'NR==2{printf "%s / %s (%s used)", $3, $2, $5}')
echo "  $DISK"
DISK_PCT=$(df -h / | awk 'NR==2{print $5}' | sed 's/%//')
if [ $DISK_PCT -gt 80 ]; then
    echo "  ⚠️  WARNING: Disk over 80% full!"
fi
echo ""

# Services
echo "🔧 SERVICES:"
echo -n "  ultrafeeder: "
systemctl is-active ultrafeeder || echo "❌ Not running"
echo -n "  adsb-web: "
systemctl is-active adsb-web || echo "❌ Not running"
echo -n "  docker: "
systemctl is-active docker || echo "❌ Not running"
echo ""

# Docker Containers
echo "🐳 CONTAINERS:"
if sudo docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null | grep -v NAMES; then
    echo ""
else
    echo "  ❌ No containers running or docker not accessible"
    echo ""
fi

# Restart Count
echo "🔄 SERVICE RESTARTS:"
RESTARTS=$(systemctl show ultrafeeder -p NRestarts --value)
echo "  ultrafeeder: $RESTARTS restarts"
if [ $RESTARTS -gt 5 ]; then
    echo "  ⚠️  WARNING: Multiple restarts detected!"
fi
echo ""

# Failed Services
echo "❌ FAILED SERVICES:"
FAILED=$(systemctl --failed --no-legend | wc -l)
if [ $FAILED -eq 0 ]; then
    echo "  ✓ None"
else
    systemctl --failed --no-legend
fi
echo ""

# Summary
echo "════════════════════════════════════════════"
echo "  HEALTH SUMMARY"
echo "════════════════════════════════════════════"

# Count warnings
WARNINGS=0
[ $FREE_MB -lt 100 ] && ((WARNINGS++))
if (( $(echo "$LOAD1 > 2.0" | bc -l) 2>/dev/null)); then ((WARNINGS++)); fi
[ $DISK_PCT -gt 80 ] && ((WARNINGS++))
[ $RESTARTS -gt 5 ] && ((WARNINGS++))
[ $FAILED -gt 0 ] && ((WARNINGS++))

if [ $WARNINGS -eq 0 ]; then
    echo "  ✅ System Healthy"
else
    echo "  ⚠️  $WARNINGS Warning(s) Detected"
    echo ""
    echo "  Recommendations:"
    [ $FREE_MB -lt 100 ] && echo "    - Free up memory (see PI_FREEZE_GUIDE.md)"
    [ $DISK_PCT -gt 80 ] && echo "    - Clean up disk space"
    if (( $(echo "$LOAD1 > 2.0" | bc -l) 2>/dev/null)); then
        echo "    - Reduce system load"
    fi
    [ $RESTARTS -gt 5 ] && echo "    - Investigate service restart issues"
fi
echo ""
