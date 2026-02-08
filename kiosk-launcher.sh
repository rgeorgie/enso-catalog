#!/bin/bash

URL="http://localhost:5000/kiosk"

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
            google-chrome --kiosk "$URL"
        else
            xdg-open "$URL"
        fi
        ;;
    chromium)
        if command -v chromium >/dev/null 2>&1; then
            chromium --kiosk "$URL"
        else
            xdg-open "$URL"
        fi
        ;;
    chromium-browser)
        if command -v chromium-browser >/dev/null 2>&1; then
            chromium-browser --kiosk "$URL"
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
        # Default to xdg-open for unknown browsers
        xdg-open "$URL"
        ;;
esac