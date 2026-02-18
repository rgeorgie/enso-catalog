#!/bin/bash
# Map a touchscreen device to the active HDMI output using xinput and xrandr.
# Retries until X is available (useful when started by systemd at boot).

LOG=/tmp/kiosk-touch.log
echo "[map-touchscreen] starting at $(date)" >> "$LOG"

MAX_RETRIES=12
SLEEP=2
retry=0
while [ $retry -lt $MAX_RETRIES ]; do
    DISPLAY_NAME=$(xrandr --query 2>/dev/null | awk '/ connected/ {print $1; exit}')
    if [ -n "$DISPLAY_NAME" ]; then
        echo "[map-touchscreen] display detected: $DISPLAY_NAME" >> "$LOG"
        break
    fi
    echo "[map-touchscreen] waiting for X display... ($retry)" >> "$LOG"
    retry=$((retry+1))
    sleep $SLEEP
done

if [ -z "$DISPLAY_NAME" ]; then
    echo "[map-touchscreen] no display found, exiting" >> "$LOG"
    exit 1
fi

# Find a touchscreen-like device name
TOUCH_DEVICE=$(xinput --list --name-only 2>/dev/null | grep -i -E "touch|touchscreen|stylus|pen" | head -n1)
if [ -z "$TOUCH_DEVICE" ]; then
    echo "[map-touchscreen] no touchscreen device found via xinput" >> "$LOG"
    exit 0
fi
echo "[map-touchscreen] candidate device: $TOUCH_DEVICE" >> "$LOG"

TOUCH_ID=$(xinput --list --id-only "$TOUCH_DEVICE" 2>/dev/null)
if [ -z "$TOUCH_ID" ]; then
    echo "[map-touchscreen] could not get id for device: $TOUCH_DEVICE" >> "$LOG"
    exit 1
fi

# Map touchscreen to the display
if xinput map-to-output "$TOUCH_ID" "$DISPLAY_NAME" 2>>"$LOG"; then
    echo "[map-touchscreen] mapped device id $TOUCH_ID to $DISPLAY_NAME" >> "$LOG"
else
    echo "[map-touchscreen] map-to-output failed for id $TOUCH_ID -> $DISPLAY_NAME" >> "$LOG"
fi

exit 0
