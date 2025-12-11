#!/bin/bash
# Install both MIDI bridge and web server systemd services

set -e

if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root (use sudo)"
    exit 1
fi

echo "=== Installing Digital Piano Picnic Services ==="
echo ""

# Install MIDI Bridge Service
echo "1️⃣  MIDI → Home Assistant Bridge Service"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

SERVICE_FILE="deployment/midi-ha.service"
if [ -f "$SERVICE_FILE" ]; then
    # Prompt for HA token if needed
    if grep -q "your_token_here" "$SERVICE_FILE"; then
        echo "⚠️  Service file contains placeholder token"
        read -p "Enter your HA_TOKEN (or press Enter to skip): " HA_TOKEN
        
        if [ ! -z "$HA_TOKEN" ]; then
            sed -i "s/your_token_here/$HA_TOKEN/" "$SERVICE_FILE"
            echo "   ✓ Token updated"
        fi
    fi
    
    cp "$SERVICE_FILE" /etc/systemd/system/midi-ha.service
    echo "   ✓ Installed midi-ha.service"
else
    echo "   ⊙ Skipping (file not found)"
fi

echo ""
echo "2️⃣  Picnic Product Search Web Interface"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

SERVICE_FILE="deployment/picnic-web.service"
if [ -f "$SERVICE_FILE" ]; then
    # Prompt for Picnic credentials
    if grep -q "your_email@example.com" "$SERVICE_FILE"; then
        echo "⚠️  Service file contains placeholder credentials"
        read -p "Enter your Picnic email: " PICNIC_EMAIL
        read -sp "Enter your Picnic password: " PICNIC_PASSWORD
        echo ""
        
        if [ ! -z "$PICNIC_EMAIL" ] && [ ! -z "$PICNIC_PASSWORD" ]; then
            sed -i "s/your_email@example.com/$PICNIC_EMAIL/" "$SERVICE_FILE"
            sed -i "s/your_password_here/$PICNIC_PASSWORD/" "$SERVICE_FILE"
            echo "   ✓ Credentials updated"
        fi
    fi
    
    cp "$SERVICE_FILE" /etc/systemd/system/picnic-web.service
    echo "   ✓ Installed picnic-web.service"
else
    echo "   ⊙ Skipping (file not found)"
fi

# Reload systemd
echo ""
echo "🔄 Reloading systemd..."
systemctl daemon-reload
echo "   ✓ Done"

# Enable services
echo ""
echo "✅ Enabling services..."
systemctl enable midi-ha.service 2>/dev/null && echo "   ✓ midi-ha.service enabled" || echo "   ⊙ midi-ha.service not found"
systemctl enable picnic-web.service 2>/dev/null && echo "   ✓ picnic-web.service enabled" || echo "   ⊙ picnic-web.service not found"

# Ask to start services
echo ""
read -p "Start services now? [Y/n]: " START_NOW
START_NOW=${START_NOW:-Y}

if [[ "$START_NOW" =~ ^[Yy] ]]; then
    echo ""
    echo "▶️  Starting services..."
    
    systemctl start midi-ha.service 2>/dev/null && echo "   ✓ midi-ha.service started" || echo "   ⊙ midi-ha.service not started"
    systemctl start picnic-web.service 2>/dev/null && echo "   ✓ picnic-web.service started" || echo "   ⊙ picnic-web.service not started"
    
    sleep 2
    
    echo ""
    echo "📊 Service Status:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    systemctl status midi-ha.service --no-pager -l || true
    echo ""
    systemctl status picnic-web.service --no-pager -l || true
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Useful commands:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "MIDI Bridge:"
echo "  Status:  sudo systemctl status midi-ha.service"
echo "  Logs:    sudo journalctl -u midi-ha.service -f"
echo "  Restart: sudo systemctl restart midi-ha.service"
echo ""
echo "Web Interface:"
echo "  Status:  sudo systemctl status picnic-web.service"
echo "  Logs:    sudo journalctl -u picnic-web.service -f"
echo "  Restart: sudo systemctl restart picnic-web.service"
echo "  Access:  http://localhost:8080 or http://$(hostname -I | awk '{print $1}'):8080"
echo ""
echo "Both services:"
echo "  sudo systemctl status midi-ha.service picnic-web.service"
echo "  sudo systemctl restart midi-ha.service picnic-web.service"
echo ""
