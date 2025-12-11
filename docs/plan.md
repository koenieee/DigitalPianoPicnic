x# Digital Piano → Home Assistant Picnic Shopping Cart Integration

## Overview

This project bridges MIDI input from a digital piano connected to a Raspberry Pi to Home Assistant actions. Each piano key can be mapped to a Picnic product, enabling you to build your shopping cart by playing notes. The system includes:

- **Arming mechanism**: Requires a password (note sequence or chord) before shopping actions are enabled
- **Double-tap confirmation**: Each note must be played twice within a time window to add a product
- **Voice announcements**: Home Assistant announces the added product via Assist Satellite
- **Rate limiting**: Prevents accidental duplicate additions
- **Automatic disarm**: Resets after inactivity for safety

## Architecture

```
┌─────────────────┐
│ Digital Piano   │ USB
│ (MIDI Output)   ├──────┐
└─────────────────┘      │
                         │
                    ┌────▼─────────────────────────┐
                    │  Raspberry Pi (Raspbian)     │
                    │                              │
                    │  ┌────────────────────────┐ │
                    │  │  src/midi.py           │ │
                    │  │  - Read MIDI events    │ │
                    │  │  - Detect chords       │ │
                    │  │  - Track double-taps   │ │
                    │  └───────────┬────────────┘ │
                    │              │              │
                    │  ┌───────────▼────────────┐ │
                    │  │  src/bridge.py         │ │
                    │  │  - Arming state        │ │
                    │  │  - Debounce/rate limit │ │
                    │  │  - Map notes→products  │ │
                    │  └───────────┬────────────┘ │
                    │              │              │
                    │  ┌───────────▼────────────┐ │
                    │  │  src/ha_client.py      │ │
                    │  │  - WebSocket client    │ │
                    │  │  - Service calls       │ │
                    │  │  - Reconnection logic  │ │
                    │  └───────────┬────────────┘ │
                    └──────────────┼──────────────┘
                                   │ WebSocket
                                   │
                    ┌──────────────▼──────────────┐
                    │  Home Assistant             │
                    │  - picnic.add_product       │
                    │  - assist_satellite.announce│
                    └─────────────────────────────┘
```

## Configuration

### config/app.yaml

Main application settings for Home Assistant connection, MIDI behavior, arming, confirmation, and announcements.

```yaml
ha:
  url: ws://homeassistant.local:8123/api/websocket
  token_source: env  # Use HA_TOKEN environment variable

midi:
  port_name: ""  # Empty = auto-select first piano; or exact name like "Digital Piano"
  channel: 1     # MIDI channel to listen on (1-16, or "all")
  trigger_on: note_on  # Only note_on with velocity>0 triggers actions
  debounce_ms: 200     # Suppress rapid repeated presses
  rate_limit_per_note_ms: 500  # Minimum time between actions for same note

arming:
  enabled: true
  # Sequence: notes must be played in order within timeout
  sequence: [60, 62, 64]  # C, D, E (Middle C = 60)
  sequence_timeout_ms: 3000
  
  # Chord: notes must be pressed within window (alternative or additional)
  chord: []  # e.g., [65, 69] for F + A
  chord_window_ms: 200
  
  require_both_sequence_and_chord: false  # true = need both to arm
  disarm_after_ms: 60000  # Auto-disarm after 60s of inactivity
  disarm_after_add: false  # true = disarm immediately after each product add

confirmation:
  double_tap_enabled: true
  double_tap_window_ms: 800  # Second press must occur within this time
  per_note_override_allowed: true  # Allow mapping.yaml to override per note

announce:
  enabled: true
  device_id: 4f17bb6b7102f82e8a91bf663bcb76f9  # Your Assist Satellite device
  preannounce: false
  message_template: "{product_name} was added to basket"

mapping_file: config/mapping.yaml

logging:
  level: INFO  # DEBUG for detailed MIDI events
  mode: stdout  # or file path like /var/log/midi-ha.log

runtime:
  reconnect_backoff_ms: [500, 1000, 2000, 5000]  # Exponential backoff
  batch_mode: false  # Future: aggregate multiple presses
```

### config/mapping.yaml

Maps MIDI notes to Picnic products with optional per-note overrides.

```yaml
defaults:
  amount: 1
  config_entry_id: ""  # Set if you have multiple Picnic accounts
  confirmation: double_tap  # double_tap or single_tap

notes:
  60:  # Middle C
    product_id: s1018231
    product_name: "Picnic cola zero"
    amount: 1
    confirmation: double_tap
  
  61:  # C#
    product_id: s1234567
    product_name: "Bananas"
    amount: 2
  
  62:  # D
    product_id: s7654321
    product_name: "Whole milk"
    amount: 1
  
  # Add more notes as needed...
  # MIDI note numbers: C4=60, C#4=61, D4=62, ..., B4=71, C5=72, etc.

controls:
  # Optional: Control Change (CC) mappings
  # cc64:  # Sustain pedal
  #   action: disarm

behavior:
  trigger_only_on_first_press: true
  out_of_range_handling: log  # log or ignore
```

## Module Responsibilities

### src/midi.py

**MIDI input and event processing**

- List and select MIDI input ports (auto or by name)
- Open port with `mido` and `python-rtmidi` backend
- Parse `note_on`, `note_off`, and control change messages
- Detect chords (multiple notes within time window)
- Track double-tap timing per note
- Handle MIDI channel filtering
- Provide event stream to bridge

**Key functions:**
- `list_input_ports() -> List[str]`
- `open_input(port_name: str) -> MidiInput`
- `read_events(input) -> Iterator[MidiEvent]`
- `detect_chord(events, window_ms) -> Optional[Set[int]]`

### src/ha_client.py

**Home Assistant WebSocket and service calls**

- Connect to HA WebSocket API (`/api/websocket`)
- Authenticate with long-lived access token
- Send `call_service` messages for:
  - `picnic.add_product` (domain, service, service_data)
  - `assist_satellite.announce` (with target device_id)
- Handle WebSocket reconnection with exponential backoff
- Parse service call results and errors
- Structured logging for all HA interactions

**Key classes:**
- `HAClient(url: str, token: str)`
- `async def connect()`
- `async def call_service(domain, service, service_data, target)`
- `async def close()`

### src/bridge.py

**Main application logic and state machine**

- Load configuration from `config/app.yaml` and `config/mapping.yaml`
- Initialize MIDI input and HA client
- Implement arming state machine:
  - DISARMED → (sequence/chord match) → ARMED
  - ARMED → (timeout/disarm) → DISARMED
- Track per-note state for double-tap confirmation
- Enforce debounce and rate limiting
- Build service call payloads from mapping
- Coordinate MIDI events → HA service calls → announcements
- Main event loop with graceful shutdown

**Key classes:**
- `ArmingStateMachine(config)`
- `ConfirmationTracker(config)`
- `Bridge(config)`
- `async def run()`

## Home Assistant Services

### picnic.add_product

Adds a product to your Picnic shopping cart.

**Payload:**
```yaml
action: picnic.add_product
data:
  product_id: s1018231  # Required (or product_name)
  amount: 1             # Optional, defaults to 1
  config_entry_id: 01JQ1EK0ERC1HRBSK3JK4N2CRZ  # Optional for multi-account
```

**WebSocket message:**
```json
{
  "id": 1,
  "type": "call_service",
  "domain": "picnic",
  "service": "add_product",
  "service_data": {
    "product_id": "s1018231",
    "amount": 1,
    "config_entry_id": "01JQ1EK0ERC1HRBSK3JK4N2CRZ"
  }
}
```

### assist_satellite.announce

Announces a message on a specific Assist Satellite device.

**Payload:**
```yaml
action: assist_satellite.announce
data:
  message: "Picnic cola zero was added to basket"
  preannounce: false
target:
  device_id: 4f17bb6b7102f82e8a91bf663bcb76f9
```

**WebSocket message:**
```json
{
  "id": 2,
  "type": "call_service",
  "domain": "assist_satellite",
  "service": "announce",
  "service_data": {
    "message": "Picnic cola zero was added to basket",
    "preannounce": false
  },
  "target": {
    "device_id": "4f17bb6b7102f82e8a91bf663bcb76f9"
  }
}
```

## Raspberry Pi Deployment

### Prerequisites

**Hardware:**
- Raspberry Pi (3B+, 4, or 5 recommended)
- Raspbian OS (Bookworm or Bullseye)
- Digital piano with USB MIDI output

**Software:**
- Python 3.9+ (pre-installed on Raspbian Bookworm)
- `libasound2` (ALSA library for MIDI)
- Git (for version control and deployment)

### Installation Steps

1. **Clone repository to Raspberry Pi:**
   ```bash
   cd ~
   git clone <your-repo-url> DigitalPianoPicnic
   cd DigitalPianoPicnic
   ```

2. **Install system dependencies:**
   ```bash
   sudo apt-get update
   sudo apt-get install -y libasound2-dev python3-pip
   ```

3. **Install Python dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

4. **Configure application:**
   - Copy `config/app.yaml.example` to `config/app.yaml`
   - Copy `config/mapping.yaml.example` to `config/mapping.yaml`
   - Edit both files with your Home Assistant URL, device ID, and note mappings
   - Set `HA_TOKEN` environment variable:
     ```bash
     echo 'export HA_TOKEN="your-long-lived-token"' >> ~/.bashrc
     source ~/.bashrc
     ```

5. **Test manually:**
   ```bash
   python3 src/bridge.py
   ```
   - Verify MIDI port detection
   - Test arming sequence
   - Confirm double-tap and product adds

6. **Install systemd service:**
   ```bash
   sudo cp deployment/midi-ha.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable midi-ha.service
   sudo systemctl start midi-ha.service
   ```

7. **Verify logs:**
   ```bash
   sudo journalctl -u midi-ha.service -f
   ```

### MIDI Device Permissions

If you encounter permission errors accessing MIDI devices:

```bash
# Add user to audio group
sudo usermod -aG audio $USER

# Create udev rule (optional, usually not needed)
echo 'SUBSYSTEM=="sound", MODE="0666"' | sudo tee /etc/udev/rules.d/99-midi.rules
sudo udevadm control --reload-rules
```

Log out and back in for group changes to take effect.

### Troubleshooting

**No MIDI ports detected:**
- Connect piano and run: `amidi -l`
- Check USB connection: `lsusb`
- Verify ALSA: `aplay -l`

**WebSocket connection fails:**
- Verify HA URL is correct (use IP if `.local` doesn't resolve)
- Check token validity in Home Assistant UI
- Test connectivity: `curl -v ws://homeassistant.local:8123/api/websocket`

**Service won't start:**
- Check logs: `sudo journalctl -u midi-ha.service -n 50`
- Verify paths in `midi-ha.service` match your installation
- Ensure `HA_TOKEN` is set in service environment

## Logging and Observability

### Log Levels

- **DEBUG**: All MIDI events, state transitions, payload details
- **INFO**: Service starts, arming/disarming, product adds, announcements
- **WARNING**: Rate limit hits, mapping misses, reconnections
- **ERROR**: Service call failures, WebSocket errors, config issues

### Structured Logging Format

```
[TIMESTAMP] [LEVEL] [MODULE] message key1=value1 key2=value2
```

Example:
```
2025-12-11 14:32:45 INFO bridge Armed state=armed trigger=sequence
2025-12-11 14:32:50 INFO bridge Product added note=60 product_id=s1018231 amount=1
2025-12-11 14:32:51 INFO ha_client Announcement sent device_id=4f17bb...
```

### Metrics to Monitor

- MIDI events per minute (to detect stuck keys)
- Arming/disarming frequency
- Product add success rate
- WebSocket reconnection count
- Average latency (MIDI event → HA response)

## Roadmap

### Phase 1: Core Functionality (Current)
- [x] Planning and architecture
- [x] MIDI input with `mido` and `python-rtmidi`
- [x] Home Assistant WebSocket client
- [x] Arming state machine (sequence and/or chord)
- [x] Double-tap confirmation per note
- [x] Product add service calls
- [x] Voice announcements via Assist Satellite
- [x] Basic logging and error handling
- [x] Systemd service for autostart
- [x] Test mode for offline validation

### Phase 2: Robustness (Next)
- [ ] Configuration validation with schemas
- [ ] Comprehensive error handling and retries
- [ ] Health check endpoint or status LED
- [ ] Product name caching (query HA for names if missing)
- [ ] Multi-account support with account selection by chord
- [ ] Rate limit visualization (LED or log warnings)
- [ ] Unit tests for state machine and mapping

### Phase 3: Enhanced UX (Future)
- [ ] Web UI for live mapping editor
- [ ] MIDI learn mode (press key to assign product)
- [ ] Visual feedback on piano (if supported via MIDI out)
- [ ] Batch mode: collect multiple notes, then "submit" chord
- [ ] Undo last add (special note or chord)
- [ ] Shopping cart display on e-ink screen
- [ ] Integration with Picnic API for product search

### Phase 4: Advanced Features (Aspirational)
- [ ] Velocity-based quantity (harder press = more units)
- [ ] Sustain pedal for modifier actions
- [ ] Octave shifting for product categories
- [ ] Export shopping list to other services
- [ ] Multi-user support (different arming passwords)
- [ ] Analytics dashboard (most-played notes/products)

## Security Considerations

1. **Token Storage**: Never commit `HA_TOKEN` to version control. Use environment variables or systemd `EnvironmentFile`.
2. **Network**: Home Assistant WebSocket should be on local network or secured with TLS.
3. **Arming**: Use a non-trivial sequence (4+ notes) or chord to prevent accidental arming.
4. **Rate Limiting**: Configured limits prevent abuse or stuck keys from flooding HA.
5. **Auto-disarm**: Timeout ensures system returns to safe state if unattended.

## Contributing

When adding features or fixing bugs:

1. Update this plan document with new config options or behavior changes
2. Add logging at appropriate levels
3. Update `config/*.yaml.example` files
4. Test on Raspberry Pi with real hardware before committing
5. Document any new Home Assistant service dependencies

## References

- **Mido Documentation**: https://mido.readthedocs.io/
- **python-rtmidi**: https://spotlightkid.github.io/python-rtmidi/
- **Home Assistant WebSocket API**: https://developers.home-assistant.io/docs/api/websocket/
- **Home Assistant REST API**: https://developers.home-assistant.io/docs/api/rest/
- **Picnic Integration**: https://www.home-assistant.io/integrations/picnic/
- **Assist Satellite**: https://www.home-assistant.io/integrations/assist_satellite/

---

**Last Updated**: 2025-12-11  
**Version**: 1.0.0  
**Status**: Implementation in progress
