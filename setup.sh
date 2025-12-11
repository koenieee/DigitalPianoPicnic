#!/bin/bash
# Quick setup script for Raspberry Pi

set -e

echo "=== Digital Piano → Home Assistant Setup ==="
echo ""

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "⚠️  This script is for Linux/Raspbian only"
    echo "   For Windows, follow README.md manual setup"
    exit 1
fi

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y libasound2-dev python3-pip git

# Install Python dependencies in virtual environment
echo "🐍 Creating virtual environment and installing dependencies..."
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
deactivate

# Create config files from examples
echo "⚙️  Creating configuration files..."
if [ ! -f config/app.yaml ]; then
    cp config/app.yaml.example config/app.yaml
    echo "   ✓ Created config/app.yaml"
else
    echo "   ⊙ config/app.yaml already exists (not overwriting)"
fi

if [ ! -f config/mapping.yaml ]; then
    cp config/mapping.yaml.example config/mapping.yaml
    echo "   ✓ Created config/mapping.yaml"
else
    echo "   ⊙ config/mapping.yaml already exists (not overwriting)"
fi

# Prompt for HA token
echo ""
echo "🔑 Home Assistant Setup"
echo "   You need a Long-Lived Access Token from Home Assistant."
echo "   Generate one at: http://homeassistant.local:8123/profile"
echo ""
read -p "   Enter your HA token (or press Enter to set later): " HA_TOKEN

if [ ! -z "$HA_TOKEN" ]; then
    # Add to .bashrc if not already there
    if ! grep -q "export HA_TOKEN=" ~/.bashrc; then
        echo "" >> ~/.bashrc
        echo "# Home Assistant token for MIDI bridge" >> ~/.bashrc
        echo "export HA_TOKEN=\"$HA_TOKEN\"" >> ~/.bashrc
        echo "   ✓ Token saved to ~/.bashrc"
    else
        echo "   ⊙ HA_TOKEN already in ~/.bashrc (not overwriting)"
    fi
    export HA_TOKEN="$HA_TOKEN"
fi

# List MIDI ports
echo ""
echo "🎹 Available MIDI ports:"
python3 -c "import mido; ports = mido.get_input_names(); [print(f'   {i}: {p}') for i, p in enumerate(ports)]" 2>/dev/null || echo "   (Connect your piano to see ports)"

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit config/app.yaml (set HA URL and device ID)"
echo "  2. Edit config/mapping.yaml (map notes to products)"
if [ -z "$HA_TOKEN" ]; then
    echo "  3. Set HA_TOKEN in deployment/midi-ha.service"
fi
echo "  4. Test keyboard: source venv/bin/activate && python3 src/bridge.py --test"
echo "  5. Test with HA: source venv/bin/activate && python3 src/bridge.py"
echo "  6. Install service: sudo ./deployment/install-service.sh"
echo ""
echo "See README.md and TEST_MODE.md for detailed instructions."
