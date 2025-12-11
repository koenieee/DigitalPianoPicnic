# Project Structure

```
DigitalPianoPicnic/
│
├── 📖 Documentation
│   ├── README.md                    # Main user guide with installation & usage
│   ├── QUICKSTART.md                # 5-minute setup guide
│   ├── IMPLEMENTATION_SUMMARY.md    # Complete implementation details
│   ├── docs/
│   │   └── plan.md                  # Architecture, roadmap, design decisions
│   └── LICENSE                      # MIT License
│
├── ⚙️ Configuration
│   ├── config/
│   │   ├── app.yaml.example         # Main application config template
│   │   └── mapping.yaml.example     # MIDI note → product mapping template
│   ├── .env.example                 # Environment variables template
│   └── .gitignore                   # Git ignore patterns
│
├── 🐍 Source Code
│   └── src/
│       ├── __init__.py              # Python package marker
│       ├── midi.py                  # MIDI input handling (478 lines)
│       │                            # - Port detection & opening
│       │                            # - Event parsing (note_on, note_off, CC)
│       │                            # - Chord detection
│       │                            # - Double-tap tracking
│       │
│       ├── ha_client.py             # Home Assistant WebSocket client (316 lines)
│       │                            # - WebSocket connection & authentication
│       │                            # - Service calls (picnic, assist_satellite)
│       │                            # - Reconnection with backoff
│       │                            # - Error handling
│       │
│       └── bridge.py                # Main application logic (483 lines)
│                                    # - Config loading (YAML)
│                                    # - Arming state machine
│                                    # - Confirmation tracking
│                                    # - Rate limiting & debouncing
│                                    # - Event coordination
│                                    # - Main async loop
│
├── 🚀 Deployment
│   ├── deployment/
│   │   ├── midi-ha.service          # Systemd service unit file
│   │   └── install-service.sh       # Service installation script
│   └── setup.sh                     # Automated Raspberry Pi setup
│
├── 📦 Dependencies
│   └── requirements.txt             # Python packages:
│                                    # - mido (MIDI library)
│                                    # - python-rtmidi (MIDI backend)
│                                    # - PyYAML (config parsing)
│                                    # - websockets (HA WebSocket client)
│
└── 🗑️ Legacy
    └── piano.py                     # Original empty file (can be deleted)
```

## File Purposes

### Documentation Files

| File | Purpose | Audience |
|------|---------|----------|
| `README.md` | Main documentation, installation guide, troubleshooting | End users |
| `QUICKSTART.md` | Fast 5-minute setup guide | Impatient users 😄 |
| `TEST_MODE.md` | Keyboard-only testing guide without Home Assistant | Testing/validation |
| `IMPLEMENTATION_SUMMARY.md` | Implementation details, next steps, diagnostics | You (developer) |
| `docs/plan.md` | Complete architecture, config schemas, roadmap | Developers/contributors |

### Configuration Files

| File | Purpose | When to Edit |
|------|---------|--------------|
| `config/app.yaml.example` | Template for main config | Copy to `app.yaml` and customize |
| `config/mapping.yaml.example` | Template for note mappings | Copy to `mapping.yaml` and add products |
| `.env.example` | Template for environment vars | Reference only (use systemd env) |

**Note**: Never commit actual `app.yaml`, `mapping.yaml`, or `.env` files with secrets!

### Source Code Modules

| Module | Responsibility | Key Classes/Functions |
|--------|----------------|----------------------|
| `src/midi.py` | MIDI hardware interface | `MidiInput`, `ChordDetector`, `DoubleTapTracker` |
| `src/ha_client.py` | Home Assistant API | `HAClient`, `ServiceCallResult` |
| `src/bridge.py` | Application logic & orchestration | `Bridge`, `ArmingStateMachine`, `RateLimiter` |

### Tools

| Tool | Purpose |
|------|---------|
| `tools/search_web.py` | **Web interface (recommended)** - Search products with visual keyboard key selector and one-click save |
| `tools/search_products.py` | Command-line interface - Search Picnic products to find IDs for mapping |
| `tools/README.md` | Documentation for product search tools |

**Command-line options:**
- `python3 tools/search_web.py` - Start web server (then open http://localhost:8080)
- `python3 tools/search_products.py --interactive` - CLI interactive mode
- `python3 tools/search_products.py "bananas"` - CLI single search
- `python3 src/bridge.py` - Normal mode (requires Home Assistant)
- `python3 src/bridge.py --test` - Test mode (no Home Assistant, fake calls)
- `python3 src/bridge.py --config <path>` - Custom config file
- `python3 tools/search_products.py "query"` - Search for product IDs

### Deployment Files

| File | Purpose | Usage |
|------|---------|-------|
| `setup.sh` | One-command setup for Pi | Run once: `./setup.sh` |
| `deployment/midi-ha.service` | Systemd service definition | Installed to `/etc/systemd/system/` |
| `deployment/install-service.sh` | Service installer | Run with sudo: `sudo ./deployment/install-service.sh` |

## Data Flow

```
┌─────────────┐
│ piano.py    │ ← Empty file (can delete)
└─────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     Main Application Flow                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │    src/bridge.py        │ ← Entry point (main())
              │  - Loads YAML configs   │
              │  - Initializes modules  │
              │  - Main event loop      │
              └──────────┬──────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
  ┌──────────────┐ ┌───────────┐ ┌──────────────┐
  │ src/midi.py  │ │  Config   │ │src/ha_client │
  │              │ │  Files    │ │    .py       │
  │ - Read MIDI  │ │           │ │              │
  │ - Detect     │ │ app.yaml  │ │ - Connect HA │
  │   chords     │ │ mapping   │ │ - Call       │
  │ - Track      │ │   .yaml   │ │   services   │
  │   double-tap │ │           │ │ - Announce   │
  └──────────────┘ └───────────┘ └──────────────┘
         │                               │
         ▼                               ▼
  ┌──────────────┐              ┌──────────────┐
  │ Digital Piano│              │ Home         │
  │ (USB MIDI)   │              │ Assistant    │
  └──────────────┘              └──────────────┘
                                        │
                                        ▼
                                ┌──────────────┐
                                │ Picnic API   │
                                │ + Assist     │
                                │   Satellite  │
                                └──────────────┘
```

## Configuration Flow

```
1. User edits:
   config/app.yaml       ← HA URL, device ID, arming sequence
   config/mapping.yaml   ← Note mappings to products

2. bridge.py loads configs:
   - Validates YAML syntax
   - Applies defaults
   - Initializes state machines

3. Runtime:
   - MIDI events → Check arming state
   - Note press → Check mapping
   - Double-tap confirmed → Call HA service
   - Service success → Announce product
```

## State Machine Flow

```
┌───────────┐
│ DISARMED  │ ◄─────────────┐
└─────┬─────┘                │
      │                      │
      │ Play sequence        │ Timeout or
      │ (C-D-E)              │ disarm_after_add
      │                      │
      ▼                      │
┌───────────┐                │
│  ARMED    │ ───────────────┘
└─────┬─────┘
      │
      │ Play mapped note (1st tap)
      ▼
┌───────────────────┐
│ Waiting 2nd tap   │
└─────┬─────────────┘
      │
      │ Play same note (2nd tap)
      │ within 800ms
      ▼
┌───────────────────┐
│ Add product       │
│ + Announce        │
└───────────────────┘
```

## Logging Flow

```
Application startup:
  INFO: Loading configuration
  INFO: Components initialized
  INFO: Connected to Home Assistant
  INFO: Listening for MIDI events

Arming:
  DEBUG: Sequence started: [60]
  DEBUG: Sequence progress: [60, 62]
  INFO: Arming sequence completed
  INFO: System ARMED (sequence)

Adding product:
  DEBUG: MIDI event: note_on note=60 velocity=64
  DEBUG: Double-tap first press note=60
  INFO: Note 60: waiting for second tap
  DEBUG: Double-tap confirmed note=60
  INFO: Triggering action: note=60 product=Picnic cola zero
  INFO: Adding product: s1018231 x1
  DEBUG: Sent service call: picnic.add_product
  INFO: Service call succeeded: picnic.add_product
  INFO: Product added successfully: Picnic cola zero
  INFO: Announcing: 'Picnic cola zero was added to basket'
  INFO: Announcement sent
```

## What to Customize

### For Your Setup (Required)

1. **`config/app.yaml`** line 3: Your Home Assistant URL
2. **`config/app.yaml`** line 58: Your Assist Satellite device ID
3. **`config/mapping.yaml`**: Your Picnic product IDs and names
4. **Environment**: Set `HA_TOKEN` (in systemd service or ~/.bashrc)

### For Your Preferences (Optional)

1. **`config/app.yaml`** line 34: Arming sequence (different notes)
2. **`config/app.yaml`** line 49: Double-tap window (faster/slower)
3. **`config/app.yaml`** line 17: MIDI port name (if multiple devices)
4. **`config/app.yaml`** line 60: Announcement message template

### For Development (Advanced)

1. **`src/bridge.py`**: Add new features or state logic
2. **`src/midi.py`**: Add support for more MIDI events (pitch bend, etc.)
3. **`src/ha_client.py`**: Add more HA service calls
4. **`deployment/midi-ha.service`**: Change user, paths, or environment

## Dependencies

### Python Packages (from requirements.txt)

```
mido>=1.3.0              # MIDI message parsing
python-rtmidi>=1.5.0     # Real-time MIDI I/O (ALSA/JACK backend)
PyYAML>=6.0              # YAML configuration parsing
homeassistant-api>=4.2.2 # HA client (currently unused, using websockets)
websockets>=12.0         # WebSocket client for HA
asyncio>=3.4.3           # Async I/O (built-in Python 3.7+)
```

### System Packages (Raspbian)

```
libasound2-dev           # ALSA development files (for python-rtmidi)
python3-pip              # Python package installer
```

## Size & Complexity

- **Total files**: 18
- **Python code**: ~1,500 lines
- **Documentation**: ~2,500 lines
- **Configuration**: ~400 lines
- **Total project**: ~4,500 lines

**Module complexity**:
- `midi.py`: Medium (hardware interface, timing-sensitive)
- `ha_client.py`: Medium (network I/O, error handling)
- `bridge.py`: High (state machine, orchestration, async)

## Testing Strategy

1. **Unit testing**: Each module has `__main__` section for standalone testing
2. **Integration testing**: `bridge.py` coordinates all modules
3. **Manual testing**: Run on Raspberry Pi with real hardware
4. **Production**: Systemd service with logging and restart policies

---

**Last updated**: 2025-12-11  
**Version**: 1.0.0
