#!/bin/bash
# Installs job_alert notifier as a systemd service that starts on boot.
# Run after setup_vm.sh and after filling in config.yaml.
#
# Usage:
#   chmod +x install_service.sh
#   ./install_service.sh

set -e

INSTALL_DIR="$HOME/job_alert"
VENV_PYTHON="$INSTALL_DIR/venv/bin/python"
SERVICE_NAME="job_alert"

echo "==> Writing systemd service to /etc/systemd/system/${SERVICE_NAME}.service"
sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=Job Alert Notifier
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$VENV_PYTHON notify.py
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "==> Enabling and starting service"
sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}
sudo systemctl start  ${SERVICE_NAME}

echo ""
echo "Done. Service status:"
sudo systemctl status ${SERVICE_NAME} --no-pager
echo ""
echo "Useful commands:"
echo "  View logs:    journalctl -u ${SERVICE_NAME} -f"
echo "  Stop:         sudo systemctl stop ${SERVICE_NAME}"
echo "  Restart:      sudo systemctl restart ${SERVICE_NAME}"
