#!/bin/bash
# Install systemd service

set -e

SERVICE_NAME="midi-ha"
SERVICE_FILE="deployment/midi-ha.service"
INSTALL_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root (use sudo)"
    exit 1
fi

echo "=== Installing MIDI → HA Bridge Service ==="
echo ""

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo "❌ Service file not found: $SERVICE_FILE"
    exit 1
fi

# Prompt for HA token if not already in service file
if grep -q "your_token_here" "$SERVICE_FILE"; then
    echo "⚠️  Warning: Service file contains placeholder token"
    echo ""
    read -p "Enter your HA_TOKEN (or press Enter to edit manually): " HA_TOKEN
    
    if [ ! -z "$HA_TOKEN" ]; then
        sed -i "s/your_token_here/$HA_TOKEN/" "$SERVICE_FILE"
        echo "   ✓ Token updated in service file"
    else
        echo "   ⊙ Edit $SERVICE_FILE manually before enabling service"
    fi
fi

# Copy service file
echo "📋 Installing service file..."
cp "$SERVICE_FILE" "$INSTALL_PATH"
echo "   ✓ Copied to $INSTALL_PATH"

# Reload systemd
echo "🔄 Reloading systemd..."
systemctl daemon-reload
echo "   ✓ Done"

# Enable service
echo "✅ Enabling service..."
systemctl enable "$SERVICE_NAME.service"
echo "   ✓ Service will start on boot"

# Ask to start now
echo ""
read -p "Start service now? [Y/n]: " START_NOW
START_NOW=${START_NOW:-Y}

if [[ "$START_NOW" =~ ^[Yy] ]]; then
    echo "▶️  Starting service..."
    systemctl start "$SERVICE_NAME.service"
    sleep 2
    
    echo ""
    echo "📊 Service status:"
    systemctl status "$SERVICE_NAME.service" --no-pager
    
    echo ""
    echo "📝 View logs with: sudo journalctl -u $SERVICE_NAME.service -f"
else
    echo ""
    echo "Start manually with: sudo systemctl start $SERVICE_NAME.service"
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "Useful commands:"
echo "  Status:  sudo systemctl status $SERVICE_NAME.service"
echo "  Start:   sudo systemctl start $SERVICE_NAME.service"
echo "  Stop:    sudo systemctl stop $SERVICE_NAME.service"
echo "  Restart: sudo systemctl restart $SERVICE_NAME.service"
echo "  Logs:    sudo journalctl -u $SERVICE_NAME.service -f"
echo "  Disable: sudo systemctl disable $SERVICE_NAME.service"
