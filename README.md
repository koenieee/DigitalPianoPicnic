# Digital Piano → Home Assistant Picnic Shopping Cart

Build your Picnic shopping cart by playing your digital piano! This project bridges MIDI input from a piano connected to a Raspberry Pi to Home Assistant, allowing each piano key to add a product to your Picnic cart with voice confirmation.

## Features

✨ **Password Protection**: Requires a note sequence or chord before shopping actions are enabled  
🎹 **Double-Tap Confirmation**: Each key must be played twice to prevent accidental additions  
🔊 **Voice Announcements**: Home Assistant announces when system is armed and when products are added via Assist Satellite  
⚡ **Rate Limiting**: Prevents duplicate additions from stuck keys or rapid presses  
🔄 **Auto-Reconnect**: Automatically reconnects if keyboard or Home Assistant disconnects  
🛡️ **Auto-Disarm**: Automatically returns to safe state after inactivity with voice notification  
🎵 **88-Key Support**: Map any MIDI note (0-127) to any Picnic product  

## Architecture

```
Digital Piano (USB) → Raspberry Pi (Python) → Home Assistant (WebSocket) → Picnic API
```

The bridge runs on a Raspberry Pi, reading MIDI events via `mido` and `python-rtmidi`, then triggering Home Assistant services (`picnic.add_product` and `assist_satellite.announce`) over WebSocket.

## Quick Start

### Prerequisites

- **Hardware**: Raspberry Pi 3B+/4/5 with Raspbian OS, digital piano with USB MIDI
- **Home Assistant**: Running instance with Picnic and Assist Satellite integrations configured
- **Python**: 3.9+ (pre-installed on Raspbian Bookworm)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url> ~/DigitalPianoPicnic
   cd ~/DigitalPianoPicnic
   ```

2. **Install system dependencies:**
   ```bash
   sudo apt-get update
   sudo apt-get install -y libasound2-dev python3-pip
   ```

3. **Install Python dependencies (using virtual environment):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip3 install -r requirements.txt
   ```

4. **Configure the application:**
   ```bash
   # Copy example configs
   cp config/app.yaml.example config/app.yaml
   cp config/mapping.yaml.example config/mapping.yaml
   
   # Edit configs with your settings
   nano config/app.yaml  # Set HA URL and device ID
   nano config/mapping.yaml  # Map notes to products
   
   # Set your Home Assistant token
   echo 'export HA_TOKEN="your-long-lived-token-here"' >> ~/.bashrc
   source ~/.bashrc
   ```

5. **Test manually:**
   ```bash
   source venv/bin/activate
   
   # Test mode (no Home Assistant required, just keyboard/MIDI):
   python3 src/bridge.py --test
   
   # Real mode (requires HA_TOKEN and Home Assistant connection):
   python3 src/bridge.py
   ```
   
   **Test mode:**
   - Tests MIDI input, arming sequence, double-tap, and rate limiting
   - Fakes Home Assistant calls (no actual products added)
   - Perfect for verifying keyboard functionality
   
   **Real mode:**
   - Play the arming sequence (default: C-D-E)
   - Play a mapped key twice quickly
   - Verify product is added and announced

6. **Install as system service:**
   ```bash
   # Edit service file with your token
   sudo nano deployment/midi-ha.service
   
   # Install and start
   sudo cp deployment/midi-ha.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable midi-ha.service
   sudo systemctl start midi-ha.service
   
   # Check status
   sudo systemctl status midi-ha.service
   sudo journalctl -u midi-ha.service -f
   ```

## Configuration

### Arming Sequence

Edit `config/app.yaml` to set your password:

```yaml
arming:
  enabled: true
  sequence: [60, 62, 64]  # C, D, E (Middle C = MIDI note 60)
  sequence_timeout_ms: 3000
```

**MIDI Note Reference**: C4=60, C#4=61, D4=62, D#4=63, E4=64, F4=65, F#4=66, G4=67, G#4=68, A4=69, A#4=70, B4=71, C5=72...

### Product Mapping

Edit `config/mapping.yaml` to assign products to keys:

```yaml
notes:
  60:  # Middle C
    product_id: s1018231
    product_name: "Picnic cola zero"
    amount: 1
```

Find Picnic product IDs:

**Option 1: Use the search tool (recommended)**
```bash
# Install the optional tool
pip install python-picnic-api

# Set credentials (secure method)
export PICNIC_USERNAME='your@email.com'
export PICNIC_PASSWORD='yourpassword'

# Search for products
python3 tools/search_products.py "coca cola zero"
python3 tools/search_products.py --interactive

# See tools/README.md for full documentation
```

**Option 3: Manual Lookup via Home Assistant**
1. Open Picnic app/website
2. Add product to cart
3. Check Home Assistant Developer Tools → States → `sensor.picnic_cart_items`
4. Look for `product_id` in the state attributes

Find Picnic config_entry_id (REQUIRED):
1. Go to Home Assistant → Settings → Devices & Services
2. Click on the **Picnic** integration
3. Copy the ID from the URL after `/integration/` (e.g., `01JEN4FWWJ123ABCDEF456789`)
4. Add it to `config/mapping.yaml` under `defaults.config_entry_id`

Update `config/mapping.yaml`:
```yaml
defaults:
  config_entry_id: "01JEN4FWWJ123ABCDEF456789"  # From Picnic integration URL
```

### Voice Announcements

Find your Assist Satellite device ID:
1. Go to Home Assistant → Settings → Devices & Services
2. Find your Assist Satellite device
3. Click on it and copy the device ID from the URL

Update `config/app.yaml`:
```yaml
announce:
  enabled: true
  device_id: 4f17bb6b7102f82e8a91bf663bcb76f9
  message_template: "{product_name} was added to basket"
```

## Usage

1. **Arm the system**: Play the password sequence (default: C-D-E)
2. **Add products**: Play any mapped key twice within 800ms
3. **Listen**: Home Assistant announces the product name
4. **Auto-disarm**: System disarms after 60 seconds of inactivity

### Tips

- Use a memorable melody as your password (4+ notes recommended)
- Map frequently-used products to convenient keys (white keys near middle C)
- Adjust `double_tap_window_ms` if you have difficulty with timing
- Set `disarm_after_add: true` for extra security (requires re-arming after each product)

## Troubleshooting

### No MIDI ports detected

```bash
# List USB devices
lsusb

# List MIDI ports
amidi -l

# Test MIDI input
aseqdump -p <port>
```

### WebSocket connection fails

```bash
# Test connectivity
curl -v ws://homeassistant.local:8123/api/websocket

# Use IP address if .local doesn't resolve
# Update config/app.yaml with: ws://192.168.1.100:8123/api/websocket
```

### Service won't start

```bash
# Check logs
sudo journalctl -u midi-ha.service -n 50 --no-pager

# Check HA_TOKEN is set in service file
sudo systemctl cat midi-ha.service

# Test manually
HA_TOKEN="your-token" python3 src/bridge.py
```

### Products not adding

- Verify Picnic integration is configured in Home Assistant
- Check product IDs are correct (case-sensitive)
- Review logs: `sudo journalctl -u midi-ha.service -f`
- Test service call in HA Developer Tools

### Announcements not working

- Verify Assist Satellite device ID is correct
- Test announcement manually in HA Developer Tools
- Check device is online and responding

### Piano disconnected

**Symptom**: `MIDI connection lost` in logs

**Solution**: The system automatically tries to reconnect every 5 seconds. Just plug the keyboard back in or power it on.

**Security**: The arming state is automatically reset to DISARMED when the device disconnects, so you'll need to re-enter your password sequence after reconnection.

To change reconnect delay, edit `config/app.yaml`:
```yaml
runtime:
  midi_reconnect_delay_sec: 10  # Wait 10 seconds between retries
```

## Development

### Project Structure

```
DigitalPianoPicnic/
├── config/
│   ├── app.yaml.example          # Main config template
│   └── mapping.yaml.example      # Product mapping template
├── src/
│   ├── midi.py                   # MIDI input handling
│   ├── ha_client.py              # Home Assistant WebSocket client
│   └── bridge.py                 # Main application logic
├── deployment/
│   └── midi-ha.service           # Systemd service file
├── docs/
│   └── plan.md                   # Detailed project plan
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variables template
└── README.md                     # This file
```

### Testing Modules Independently

**Test MIDI input:**
```bash
python3 src/midi.py
```

**Test HA client:**
```bash
export HA_URL="ws://homeassistant.local:8123/api/websocket"
export HA_TOKEN="your-token"
python3 src/ha_client.py
```

**Test keyboard/MIDI functionality (no HA required):**
```bash
python3 src/bridge.py --test
```

**Test full bridge (requires HA):**
```bash
python3 src/bridge.py
```

### Adding Features

See the following documentation:
- [`docs/plan.md`](docs/plan.md) - Complete roadmap and architecture details
- [`docs/ARMING_ANNOUNCEMENTS.md`](docs/ARMING_ANNOUNCEMENTS.md) - Voice announcement configuration
- [`TEST_MODE.md`](TEST_MODE.md) - Testing without Home Assistant
- [`QUICKSTART.md`](QUICKSTART.md) - Quick setup guide

## Security

- **Never commit** `config/app.yaml`, `config/mapping.yaml`, or `.env` files
- Store `HA_TOKEN` in environment variables or systemd `EnvironmentFile`
- Use a non-trivial arming sequence (4+ notes)
- Enable `disarm_after_add` for high-security scenarios
- Run service as non-root user (default: `pi`)

## Contributing

Contributions welcome! Please:
1. Update [`docs/plan.md`](docs/plan.md) for architectural changes
2. Add logging at appropriate levels
3. Update config examples if adding options
4. Test on real hardware before submitting PR

## License

MIT License - see LICENSE file for details

## Credits

- **MIDI**: [mido](https://mido.readthedocs.io/) and [python-rtmidi](https://spotlightkid.github.io/python-rtmidi/)
- **Home Assistant**: [WebSocket API](https://developers.home-assistant.io/docs/api/websocket/)
- **Picnic**: [Integration](https://www.home-assistant.io/integrations/picnic/)

## Support

For issues or questions:
- Check [`docs/plan.md`](docs/plan.md) for detailed documentation
- Review logs: `sudo journalctl -u midi-ha.service -f`
- Open an issue on GitHub

---

**Made with ❤️ for lazy grocery shopping** 🎹🛒
