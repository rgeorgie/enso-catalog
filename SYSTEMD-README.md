# Systemd Setup for Enso Karate Catalog

This directory contains systemd service files and setup script to automatically start the Flask application and kiosk mode on boot.

## Files

- `enso-catalog.service` - Systemd service for the Flask application
- `enso-kiosk.service` - Systemd service for kiosk mode browser
- `setup-systemd.sh` - Setup script to install and enable the services
- `remove-systemd.sh` - Removal script to uninstall the services

## Prerequisites

1. Raspberry Pi with Raspberry Pi OS (or similar Linux distribution)
2. Project installed in any directory (the setup script will auto-detect the location)
3. Virtual environment set up (typically `.venv` in the project directory)
4. Chromium browser installed (`sudo apt install chromium-browser`)
5. User `pi` exists and has appropriate permissions (or modify the service files for your user)

## Installation

1. Copy this directory's contents to your Raspberry Pi
2. Run the setup script as root:

```bash
sudo ./setup-systemd.sh
```

The script will:
- Copy service files to `/etc/systemd/system/`
- Reload systemd daemon
- Enable both services for automatic startup

## Service Configuration

### Flask Application Service (`enso-catalog.service`)
- Runs as user `pi`
- Working directory: `/home/pi/enso-catalog`
- Uses virtual environment Python
- Restarts automatically on failure
- Starts after network is available

### Kiosk Service (`enso-kiosk.service`)
- Runs as user `pi`
- Requires the Flask service to be running
- Starts Chromium in kiosk mode
- Points to `http://localhost:5000/kiosk`
- Restarts automatically on failure
- Starts after graphical target

## Manual Control

Start services:
```bash
sudo systemctl start enso-catalog
sudo systemctl start enso-kiosk
```

Stop services:
```bash
sudo systemctl stop enso-catalog
sudo systemctl stop enso-kiosk
```

Check status:
```bash
sudo systemctl status enso-catalog
sudo systemctl status enso-kiosk
```

View logs:
```bash
sudo journalctl -u enso-catalog -f
sudo journalctl -u enso-kiosk -f
```

## Customization

The setup script automatically detects your project location and configures the services accordingly. If you need to customize further:

1. **Different User**: Edit the service files and change `User=pi` to your desired user
2. **Different Virtual Environment**: The services expect `.venv` in the project directory. If yours is different, modify the `PATH` environment variable in the service files
3. **Different Display**: For kiosk service, ensure `DISPLAY=:0` matches your X session
4. **Manual Path Override**: If auto-detection doesn't work, you can manually edit the `ENSO_PROJECT_DIR` environment variable in the installed service files

After making changes, reload systemd:
```bash
sudo systemctl daemon-reload
sudo systemctl restart enso-catalog enso-kiosk
```

## Removal/Uninstallation

To completely remove the systemd services:

```bash
sudo ./remove-systemd.sh
```

This script will:
- Stop both services if running
- Disable the services
- Remove the service files from `/etc/systemd/system/`
- Reload the systemd daemon

After removal, the services will no longer start on boot and can be reinstalled anytime with `sudo ./setup-systemd.sh`.

## Troubleshooting

- If services fail to start, check the journal logs
- Ensure all paths in service files exist and are accessible
- Verify the virtual environment is properly set up
- Make sure the user has permission to run the services

## Security Notes

- Services run as user `pi` (not root)
- Consider additional security measures for production use
- The kiosk browser runs with some security features disabled for local operation