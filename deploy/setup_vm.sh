#!/bin/bash
# Oracle Cloud Free VM setup script.
# Run once as your regular user (not root) after SSH-ing in.
# Tested on Ubuntu 22.04 (default Oracle Cloud image).
#
# Usage:
#   chmod +x setup_vm.sh
#   ./setup_vm.sh

set -e

echo "==> Installing system dependencies"
sudo apt-get update -q
sudo apt-get install -y -q python3-pip python3-venv git

echo "==> Cloning repo (edit URL below)"
# Replace with your actual repo URL
git clone https://github.com/YOUR_USERNAME/job_alert.git ~/job_alert
cd ~/job_alert

echo "==> Creating venv and installing dependencies"
python3 -m venv venv
venv/bin/pip install -q --upgrade pip
venv/bin/pip install -r requirements.txt

echo "==> Copying config"
cp config.example.yaml config.yaml
echo ""
echo "ACTION REQUIRED: Edit config.yaml with your Telegram credentials."
echo "  nano ~/job_alert/config.yaml"
echo ""
echo "Then run:  bash deploy/install_service.sh"
