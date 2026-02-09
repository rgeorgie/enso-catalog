#!/bin/bash

# Enso Karate Catalog - Raspberry Pi 3 Install Script
# Optimized for Raspberry Pi OS (32-bit or 64-bit) with Chromium Kiosk

set -e

echo "Enso Karate Catalog - RPi 3 Install"
echo "==================================="

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "Please run this script as root (sudo)"
    exit 1
fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

# Get the user who owns the project directory
KIOSK_USER="$(stat -c '%U' "$PROJECT_DIR")"
KIOSK_HOME="/home/$KIOSK_USER"

echo "Installing for project directory: $PROJECT_DIR"
echo "Kiosk user: $KIOSK_USER"
echo "Kiosk home: $KIOSK_HOME"

# Update system
echo "Updating system packages..."
apt update && apt upgrade -y

# Install Python and development tools
echo "Installing Python and development tools..."
apt install -y python3 python3-pip python3-venv python3-dev build-essential

# Install Chromium and kiosk dependencies
echo "Installing Chromium and kiosk dependencies..."
apt install -y chromium-browser unclutter xserver-xorg lightdm

# Install additional dependencies for the app
echo "Installing additional dependencies..."
apt install -y sqlite3 libsqlite3-dev

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv "$PROJECT_DIR/.venv"

# Install gunicorn for production server
echo "Installing gunicorn..."
"$PROJECT_DIR/.venv/bin/pip" install gunicorn

# Activate virtual environment and install requirements
echo "Installing Python dependencies..."
"$PROJECT_DIR/.venv/bin/pip" install --upgrade pip
"$PROJECT_DIR/.venv/bin/pip" install -r "$PROJECT_DIR/requirements.txt"

# Make scripts executable
chmod +x "$PROJECT_DIR/kiosk-launcher.sh"
chmod +x "$PROJECT_DIR/setup-systemd.sh"

# Set up autologin for kiosk user
echo "Setting up autologin for $KIOSK_USER..."
mkdir -p /etc/lightdm/lightdm.conf.d
cat > /etc/lightdm/lightdm.conf.d/60-autologin.conf << EOF
[Seat:*]
autologin-user=$KIOSK_USER
autologin-user-timeout=0
EOF

# Setup kiosk with X11
cat > $KIOSK_HOME/.xsession << EOF
#!/bin/bash
unclutter -idle 0.1 &
sleep 5
exec chromium-browser --kiosk --start-fullscreen --disable-web-security --user-data-dir=/tmp/chromium --no-first-run http://localhost:5000/kiosk
EOF
chmod +x $KIOSK_HOME/.xsession
chown $KIOSK_USER:$KIOSK_USER $KIOSK_HOME/.xsession

# Run systemd setup
echo "Setting up systemd services..."
"$PROJECT_DIR/setup-systemd.sh"

# For RPi kiosk, keep kiosk service enabled as fallback
# systemctl disable enso-kiosk.service

# Optimize for RPi 3 (moderate memory)
echo "Optimizing for RPi 3..."
# Reduce swappiness
echo "vm.swappiness=10" >> /etc/sysctl.conf
# Disable unnecessary services
systemctl disable bluetooth.service
systemctl disable hciuart.service

echo ""
echo "Installation complete!"
echo ""
echo "Project location: $PROJECT_DIR"
echo ""
echo "To start manually:"
echo "  sudo systemctl start enso-catalog"
echo "  sudo systemctl start lightdm  # (X11 session)"
echo ""
echo "The system will boot into kiosk mode automatically."
echo "Reboot to test: sudo reboot"