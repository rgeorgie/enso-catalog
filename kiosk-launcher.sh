#!/bin/bash

# Check if Chromium kiosk is already running
if pgrep -f "chromium.*kiosk" > /dev/null; then
    echo "Chromium kiosk already running, exiting."
    exit 0
fi

# Wait for the Flask app to be ready
echo "Waiting for Flask app to be ready..."
while ! curl -s --head http://localhost:5000/kiosk > /dev/null; do
    sleep 1
done
echo "Flask app is ready."

URL="http://localhost:5000/kiosk"

# Flags to reduce keyring/gnome prompts and disable auto-updates/extensions
CHROME_FLAGS="--no-default-browser-check --no-first-run --password-store=basic --disable-features=CredentialManagement --disable-extensions --disable-component-update --no-sandbox --ozone-platform=wayland"

# Get the default browser
BROWSER=$(xdg-settings get default-web-browser 2>/dev/null)

if [ -z "$BROWSER" ]; then
    # Fallback if xdg-settings not available (e.g., macOS)
    if command -v open >/dev/null 2>&1; then
        # macOS
        open "$URL"
    else
        # Last resort
        xdg-open "$URL"
    fi
    exit 0
fi

# Extract browser name from .desktop file
BROWSER_NAME=$(basename "$BROWSER" .desktop)

case $BROWSER_NAME in
    firefox)
        if command -v firefox >/dev/null 2>&1; then
            firefox --kiosk "$URL"
        else
            xdg-open "$URL"
        fi
        ;;
    google-chrome)
        if command -v google-chrome >/dev/null 2>&1; then
            google-chrome $CHROME_FLAGS --kiosk "$URL"
        else
            xdg-open "$URL"
        fi
        ;;
    chromium)
        if command -v chromium >/dev/null 2>&1; then
            chromium $CHROME_FLAGS --kiosk "$URL"
        else
            xdg-open "$URL"
        fi
        ;;
    chromium-browser)
        if command -v chromium-browser >/dev/null 2>&1; then
            chromium-browser $CHROME_FLAGS --kiosk "$URL"
        else
            xdg-open "$URL"
        fi
        ;;
    falkon)
        if command -v falkon >/dev/null 2>&1; then
            falkon -K "$URL"
        else
            xdg-open "$URL"
        fi
        ;;
    org.kde.falkon)
        if command -v falkon >/dev/null 2>&1; then
            falkon -K "$URL"
        else
            xdg-open "$URL"
        fi
        ;;
    midori)
        if command -v midori >/dev/null 2>&1; then
            midori --app="$URL"
        else
            xdg-open "$URL"
        fi
        ;;
    *)
        # Default to xdg-open for unknown browsers
        xdg-open "$URL"
        ;;
esac