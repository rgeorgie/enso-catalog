#!/bin/bash

# Enso Karate Catalog - Raspberry Pi Zero Install Script
# Optimized for Raspberry Pi OS Lite (32-bit) Bullseye with WPE WebKit (Cog) Kiosk

set -e

echo "Enso Karate Catalog - RPi Zero Install"
echo "======================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script as root (sudo)"
    exit 1
fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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

# Install Cog and kiosk dependencies
echo "Installing Cog and kiosk dependencies..."
apt install -y cog unclutter

# Check if Bookworm (Raspberry Pi OS 12) and setup display accordingly
if grep -q "bookworm" /etc/os-release; then
    echo "Detected Bookworm - setting up Wayland kiosk..."
    apt install -y sway wayland-utils lightdm
else
    echo "Detected Bullseye or older - setting up X11 kiosk..."
    apt install -y xserver-xorg lightdm
fi

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

# Setup kiosk based on OS version
if grep -q "bookworm" /etc/os-release; then
    # Bookworm - Wayland with Sway
    mkdir -p $KIOSK_HOME/.config/sway
    cat > $KIOSK_HOME/.config/sway/config << EOF
exec unclutter -idle 0.1
exec "sleep 5 && cog --platform=fdo --enable-web-security=false --enable-write-console-messages-to-stdout http://localhost:5000/kiosk"
bindsym Mod4+shift+e exec swaymsg exit
bindsym Mod4+shift+r reload
output * bg /dev/null solid_color 0x000000
EOF
    chown -R $KIOSK_USER:$KIOSK_USER $KIOSK_HOME/.config
    # Set sway as session
    mkdir -p /usr/share/xsessions
    cat > /usr/share/xsessions/sway.desktop << EOF
[Desktop Entry]
Name=Sway
Comment=An i3-compatible Wayland compositor
Exec=sway
Type=Application
EOF
    sed -i 's/autologin-session=.*/autologin-session=sway/' /etc/lightdm/lightdm.conf.d/60-autologin.conf
else
    # Bullseye or older - X11
    cat > $KIOSK_HOME/.xsession << EOF
#!/bin/bash
unclutter -idle 0.1 &
sleep 5
exec cog --platform=x11 --enable-web-security=false --enable-write-console-messages-to-stdout http://localhost:5000/kiosk
EOF
    chmod +x $KIOSK_HOME/.xsession
    chown $KIOSK_USER:$KIOSK_USER $KIOSK_HOME/.xsession
fi

# Run systemd setup
echo "Setting up systemd services..."
"$PROJECT_DIR/setup-systemd.sh"

# For RPi kiosk, keep kiosk service enabled as fallback
# systemctl disable enso-kiosk.service

# Optimize for RPi Zero (low memory)
echo "Optimizing for RPi Zero..."
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
if grep -q "bookworm" /etc/os-release; then
    echo "  sudo systemctl start lightdm  # (Wayland/Sway session)"
else
    echo "  sudo systemctl start lightdm  # (X11 session)"
fi
echo ""
echo "The system will boot into kiosk mode automatically."
echo "Reboot to test: sudo reboot"