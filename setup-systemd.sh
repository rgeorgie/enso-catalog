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

if [ ! -f "$SCRIPT_DIR/enso-kiosk.service" ]; then
    echo "Error: enso-kiosk.service not found in $SCRIPT_DIR"
    exit 1
fi

if [ ! -f "$SCRIPT_DIR/kiosk-launcher.sh" ]; then
    echo "Error: kiosk-launcher.sh not found in $SCRIPT_DIR"
    exit 1
fi

# Make sure kiosk-launcher.sh is executable
chmod +x "$SCRIPT_DIR/kiosk-launcher.sh"

# Create a temporary version of the service files and desktop file with the correct project path
TEMP_CATALOG_SERVICE="/tmp/enso-catalog.service"
TEMP_KIOSK_SERVICE="/tmp/enso-kiosk.service"

# Replace the hardcoded path and user (or placeholders) with the actual project directory and user
sed "s|/home/pi/enso-catalog|${PROJECT_DIR}|g; s|@INSTALL_DIR@|${PROJECT_DIR}|g; s|User=pi|${PROJECT_USER}|g; s|@INSTALL_USER@|${PROJECT_USER}|g" "$SCRIPT_DIR/enso-catalog.service" > "$TEMP_CATALOG_SERVICE"
sed "s|/home/pi/enso-catalog|${PROJECT_DIR}|g; s|@INSTALL_DIR@|${PROJECT_DIR}|g; s|User=pi|${PROJECT_USER}|g; s|@INSTALL_USER@|${PROJECT_USER}|g" "$SCRIPT_DIR/enso-kiosk.service" > "$TEMP_KIOSK_SERVICE"

# Create user systemd directory if needed
mkdir -p /home/$PROJECT_USER/.config/systemd/user

# Copy service files
echo "Copying catalog service file..."
cp "$TEMP_CATALOG_SERVICE" /etc/systemd/system/enso-catalog.service
echo "Copying kiosk service file..."
cp "$TEMP_KIOSK_SERVICE" /home/$PROJECT_USER/.config/systemd/user/enso-kiosk.service
chown $PROJECT_USER:$PROJECT_USER /home/$PROJECT_USER/.config/systemd/user/enso-kiosk.service

# Clean up temp files
rm -f "$TEMP_CATALOG_SERVICE" "$TEMP_KIOSK_SERVICE"

# Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable services
echo "Enabling catalog service..."
systemctl enable enso-catalog.service
echo "Enabling kiosk service..."
su - $PROJECT_USER -c "systemctl --user enable enso-kiosk.service"

echo ""
echo "Setup complete!"
echo ""
echo "Project location: $PROJECT_DIR"
echo "Running as user: $PROJECT_USER"
echo ""
echo "To start the services manually:"
echo "  sudo systemctl start enso-catalog"
echo "  systemctl --user start enso-kiosk  # (as $PROJECT_USER)"
echo ""
echo "To check status:"
echo "  sudo systemctl status enso-catalog"
echo "  systemctl --user status enso-kiosk"
echo ""
echo "The Flask service starts automatically on boot."
echo "The kiosk service starts automatically on user login."