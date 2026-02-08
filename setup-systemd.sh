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

# Get the user who owns the project directory
PROJECT_USER="$(stat -c '%U' "$PROJECT_DIR")"

echo "Project directory: $PROJECT_DIR"
echo "Project user: $PROJECT_USER"

# Check if service files exist
if [ ! -f "$SCRIPT_DIR/enso-catalog.service" ]; then
    echo "Error: enso-catalog.service not found in $SCRIPT_DIR"
    exit 1
fi

if [ ! -f "$SCRIPT_DIR/kiosk.desktop" ]; then
    echo "Error: kiosk.desktop not found in $SCRIPT_DIR"
    exit 1
fi

if [ ! -f "$SCRIPT_DIR/kiosk-launcher.sh" ]; then
    echo "Error: kiosk-launcher.sh not found in $SCRIPT_DIR"
    exit 1
fi

# Make sure kiosk-launcher.sh is executable
chmod +x "$SCRIPT_DIR/kiosk-launcher.sh"

# Create a temporary version of the service file and desktop file with the correct project path
TEMP_CATALOG_SERVICE="/tmp/enso-catalog.service"
TEMP_KIOSK_DESKTOP="/tmp/kiosk.desktop"

# Replace the hardcoded path and user with the actual project directory and user
sed "s|/home/pi/enso-catalog|$PROJECT_DIR|g; s|User=pi|User=$PROJECT_USER|g" "$SCRIPT_DIR/enso-catalog.service" > "$TEMP_CATALOG_SERVICE"
sed "s|/home/pi/enso-catalog|$PROJECT_DIR|g" "$SCRIPT_DIR/kiosk.desktop" > "$TEMP_KIOSK_DESKTOP"

# Copy service file and desktop file
echo "Copying service file..."
cp "$TEMP_CATALOG_SERVICE" /etc/systemd/system/enso-catalog.service
echo "Copying kiosk desktop file..."
cp "$TEMP_KIOSK_DESKTOP" /etc/xdg/autostart/kiosk.desktop

# Clean up temp files
rm -f "$TEMP_CATALOG_SERVICE" "$TEMP_KIOSK_DESKTOP"

# Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable service
echo "Enabling service..."
systemctl enable enso-catalog.service

echo ""
echo "Setup complete!"
echo ""
echo "Project location: $PROJECT_DIR"
echo "Running as user: $PROJECT_USER"
echo ""
echo "To start the service manually:"
echo "  sudo systemctl start enso-catalog"
echo ""
echo "To check status:"
echo "  sudo systemctl status enso-catalog"
echo ""
echo "The Flask service will start automatically on boot."
echo "The kiosk will start automatically when the user logs in to the desktop."