#!/bin/bash

# Enso Karate Catalog Systemd Removal Script
# This script stops, disables, and removes the systemd services

set -e

echo "Enso Karate Catalog - Systemd Removal"
echo "====================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script as root (sudo)"
    exit 1
fi

# Stop services if running
echo "Stopping services..."
systemctl stop enso-catalog.service 2>/dev/null || echo "enso-catalog.service not running"
systemctl stop enso-kiosk.service 2>/dev/null || echo "enso-kiosk.service not running"

# Disable services
echo "Disabling services..."
systemctl disable enso-catalog.service 2>/dev/null || echo "enso-catalog.service not enabled"
systemctl disable enso-kiosk.service 2>/dev/null || echo "enso-kiosk.service not enabled"

# Remove service files and desktop file
echo "Removing service files..."
rm -f /etc/systemd/system/enso-catalog.service
rm -f /etc/systemd/system/enso-kiosk.service
rm -f /etc/xdg/autostart/kiosk.desktop

# Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload

echo ""
echo "Removal complete!"
echo ""
echo "The following have been removed:"
echo "  - enso-catalog.service"
echo "  - enso-kiosk.service"
echo "  - kiosk.desktop"
echo ""
echo "Services are no longer installed or running."
echo "You can reinstall them anytime by running: sudo ./setup-systemd.sh"