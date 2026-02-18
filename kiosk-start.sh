#!/usr/bin/env bash
# Wrapper to locate the active graphical user and run the kiosk launcher as them.
# - Finds a /run/user/<uid>/bus socket and uses that uid's user.
# - Falls back to 'pi' if none found.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCHER="${REPO_DIR}/kiosk-launcher.sh"

find_user_by_runtime_dir() {
  for d in /run/user/*; do
    if [ -S "$d/bus" ]; then
      uid=$(basename "$d")
      # ignore system users
      if [ "$uid" -ge 100 ]; then
        user=$(getent passwd "$uid" | cut -d: -f1 || true)
        if [ -n "$user" ]; then
          echo "$uid:$user"
          return 0
        fi
      fi
    fi
  done
  return 1
}

DEFAULT_USER="pi"
if out=$(find_user_by_runtime_dir); then
  uid=${out%%:*}
  user=${out##*:}
else
  # Try to detect common desktop owner for :0 via who
  user=$(who | awk '/:0/ {print $1; exit}' || true)
  if [ -z "$user" ]; then
    user="$DEFAULT_USER"
    uid=$(id -u "$user" 2>/dev/null || echo 1000)
  else
    uid=$(id -u "$user")
  fi
fi

XAUTH="/home/$user/.Xauthority"
DBUS_ADDR="unix:path=/run/user/$uid/bus"
RUNTIME_DIR="/run/user/$uid"

echo "[kiosk-start] launching kiosk as user=$user uid=$uid (XAUTH=$XAUTH DBUS=$DBUS_ADDR)"

exec sudo -u "$user" -H env \
  DISPLAY=:0 \
  XAUTHORITY="$XAUTH" \
  DBUS_SESSION_BUS_ADDRESS="$DBUS_ADDR" \
  XDG_RUNTIME_DIR="$RUNTIME_DIR" \
  "$LAUNCHER"

