#!/bin/bash

# Enso Karate Catalog Systemd Setup Script
# This script installs and enables systemd services for the Flask app and kiosk mode

set -e

echo "Enso Karate Catalog - Systemd Setup"
echo "==================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script as root (sudo)"
    exit 1
fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

echo "Project directory: $PROJECT_DIR"

# Check if service files exist
if [ ! -f "$SCRIPT_DIR/enso-catalog.service" ]; then
    echo "Error: enso-catalog.service not found in $SCRIPT_DIR"
    exit 1
fi

if [ ! -f "$SCRIPT_DIR/enso-kiosk.service" ]; then
    echo "Error: enso-kiosk.service not found in $SCRIPT_DIR"
    exit 1
fi

# Create a temporary version of the service files with the correct project path
TEMP_CATALOG_SERVICE="/tmp/enso-catalog.service"
TEMP_KIOSK_SERVICE="/tmp/enso-kiosk.service"

# Replace the hardcoded path with the actual project directory
sed "s|/home/pi/enso-catalog|$PROJECT_DIR|g" "$SCRIPT_DIR/enso-catalog.service" > "$TEMP_CATALOG_SERVICE"
sed "s|/home/pi/enso-catalog|$PROJECT_DIR|g" "$SCRIPT_DIR/enso-kiosk.service" > "$TEMP_KIOSK_SERVICE"

# Copy service files
echo "Copying service files..."
cp "$TEMP_CATALOG_SERVICE" /etc/systemd/system/enso-catalog.service
cp "$TEMP_KIOSK_SERVICE" /etc/systemd/system/enso-kiosk.service

# Clean up temp files
rm -f "$TEMP_CATALOG_SERVICE" "$TEMP_KIOSK_SERVICE"

# Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable services
echo "Enabling services..."
systemctl enable enso-catalog.service
systemctl enable enso-kiosk.service

echo ""
echo "Setup complete!"
echo ""
echo "Project location: $PROJECT_DIR"
echo ""
echo "To start the services manually:"
echo "  sudo systemctl start enso-catalog"
echo "  sudo systemctl start enso-kiosk"
echo ""
echo "To check status:"
echo "  sudo systemctl status enso-catalog"
echo "  sudo systemctl status enso-kiosk"
echo ""
echo "The services will start automatically on boot."