#!/usr/bin/env bash
# Wrapper to locate the active graphical user and run the kiosk launcher as them.
# - Detects INSTALL_DIR/INSTALL_USER from /etc/enso-catalog.conf (optional)
# - Finds a /run/user/<uid>/bus socket and uses that uid's user
# - Falls back to the first non-system user (UID >= 1000)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Allow explicit install dir via /etc/enso-catalog.conf containing INSTALL_DIR=/path/to/enso-catalog
if [ -f /etc/enso-catalog.conf ]; then
  . /etc/enso-catalog.conf
fi

# Resolve REPO_DIR: prefer INSTALL_DIR, else project-relative, else common locations
if [ -n "${INSTALL_DIR:-}" ] && [ -x "${INSTALL_DIR}/kiosk-launcher.sh" ]; then
  REPO_DIR="$INSTALL_DIR"
elif [ -x "$SCRIPT_DIR/kiosk-launcher.sh" ]; then
  REPO_DIR="$SCRIPT_DIR"
else
  REPO_DIR=""
  for d in /home/*/enso-catalog /opt/enso-catalog /srv/enso-catalog; do
    for candidate in $d; do
      if [ -x "$candidate/kiosk-launcher.sh" ]; then
        REPO_DIR="$candidate"
        break 2
      fi
    done
  done
  if [ -z "$REPO_DIR" ]; then
    echo "kiosk-start: could not find enso-catalog install directory" >&2
    exit 1
  fi
fi

LAUNCHER="$REPO_DIR/kiosk-launcher.sh"

find_user_by_runtime_dir() {
  for d in /run/user/*; do
    if [ -S "$d/bus" ]; then
      uid=$(basename "$d")
      if [ "$uid" -ge 1000 ]; then
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

# Determine run user: prefer INSTALL_USER, then session owner, then first normal user
if [ -n "${INSTALL_USER:-}" ]; then
  user="$INSTALL_USER"
  uid=$(id -u "$user")
elif out=$(find_user_by_runtime_dir); then
  uid=${out%%:*}
  user=${out##*:}
else
  user=$(awk -F: '$3>=1000 && $1!="nobody" {print $1; exit}' /etc/passwd || true)
  if [ -z "$user" ]; then
    echo "kiosk-start: no suitable user found on system" >&2
    exit 1
  fi
  uid=$(id -u "$user")
fi

XAUTH="/home/$user/.Xauthority"
DBUS_ADDR="unix:path=/run/user/$uid/bus"
RUNTIME_DIR="/run/user/$uid"

echo "[kiosk-start] launching kiosk as user=$user uid=$uid (REPO_DIR=$REPO_DIR)"

exec sudo -u "$user" -H env \
  DISPLAY=:0 \
  XAUTHORITY="$XAUTH" \
  DBUS_SESSION_BUS_ADDRESS="$DBUS_ADDR" \
  XDG_RUNTIME_DIR="$RUNTIME_DIR" \
  "$LAUNCHER"

