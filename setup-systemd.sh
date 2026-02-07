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
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

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

# Copy service files
echo "Copying service files..."
cp "$SCRIPT_DIR/enso-catalog.service" /etc/systemd/system/
cp "$SCRIPT_DIR/enso-kiosk.service" /etc/systemd/system/

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
echo "To start the services manually:"
echo "  sudo systemctl start enso-catalog"
echo "  sudo systemctl start enso-kiosk"
echo ""
echo "To check status:"
echo "  sudo systemctl status enso-catalog"
echo "  sudo systemctl status enso-kiosk"
echo ""
echo "The services will start automatically on boot."
echo ""
echo "Note: Make sure the project is located at /home/pi/enso-catalog"
echo "      and that the virtual environment is set up correctly."