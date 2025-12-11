# Test Mode Guide

Test mode allows you to verify MIDI/keyboard functionality **without** connecting to Home Assistant. This is perfect for:
- Testing your piano/MIDI setup
- Verifying arming sequences
- Confirming double-tap timing
- Checking note mappings
- Debugging rate limiting

## Running Test Mode

```bash
cd ~/DigitalPianoPicnic
source venv/bin/activate
python3 src/bridge.py --test
```

## What Test Mode Does

✅ **Enabled:**
- MIDI input reading
- Port detection and selection
- Arming sequence detection
- Chord detection (if configured)
- Double-tap confirmation tracking
- Rate limiting enforcement
- Configuration file loading
- Note-to-product mapping lookups
- Full logging of all actions

❌ **Disabled:**
- Home Assistant WebSocket connection
- Actual `picnic.add_product` service calls
- Actual `assist_satellite.announce` service calls
- HA_TOKEN requirement

## Test Mode Output

When you trigger an action in test mode, you'll see:

```
2025-12-11 14:32:45 [INFO] bridge: Bridge starting in TEST MODE (no Home Assistant connection)
2025-12-11 14:32:45 [INFO] bridge: Listening for MIDI events...
2025-12-11 14:32:50 [INFO] bridge: Arming sequence completed: [60, 62, 64]
2025-12-11 14:32:50 [INFO] bridge: System ARMED (sequence)
2025-12-11 14:32:55 [INFO] bridge: Note 60: waiting for second tap
2025-12-11 14:32:56 [INFO] bridge: Triggering action: note=60 product=Picnic cola zero amount=1
2025-12-11 14:32:56 [INFO] bridge: [TEST MODE] Would add product: s1018231 x1
2025-12-11 14:32:56 [INFO] bridge: [TEST MODE] Would announce: 'Picnic cola zero was added to basket'
```

## Testing Checklist

### 1. MIDI Connection
- [ ] Piano shows up in port list
- [ ] Events appear when keys pressed
- [ ] Correct note numbers displayed

### 2. Arming Sequence
- [ ] System starts DISARMED
- [ ] Playing sequence arms system
- [ ] "System ARMED" message appears
- [ ] Wrong sequence doesn't arm

### 3. Double-Tap
- [ ] Single press logs "waiting for second tap"
- [ ] Second press within window triggers action
- [ ] Second press outside window resets

### 4. Rate Limiting
- [ ] Rapid presses of same note are blocked
- [ ] "Rate limited" message appears
- [ ] Different notes not affected

### 5. Product Mapping
- [ ] Mapped notes trigger actions
- [ ] Unmapped notes log warning
- [ ] Correct product names shown

### 6. Auto-Disarm
- [ ] System disarms after configured timeout
- [ ] "System DISARMED" message appears
- [ ] Requires re-arming to continue

## Common Test Scenarios

### Test 1: Basic Flow
```
Action: Play C-D-E
Expected: "System ARMED (sequence)"

Action: Play Middle C once
Expected: "waiting for second tap"

Action: Play Middle C again (within 800ms)
Expected: "[TEST MODE] Would add product: ..."
```

### Test 2: Wrong Sequence
```
Action: Play C-E-D (wrong order)
Expected: "Sequence broken, restarting"

Action: System stays DISARMED
Expected: No products triggered
```

### Test 3: Slow Double-Tap
```
Action: Play Middle C
Expected: "waiting for second tap"

Action: Wait 1 second

Action: Play Middle C again
Expected: "Double-tap expired, reset" + "waiting for second tap"
```

### Test 4: Rate Limiting
```
Action: Play C-D-E to arm
Action: Double-tap Middle C successfully
Expected: Product add

Action: Immediately double-tap Middle C again
Expected: "Rate limited"

Action: Wait 1 second, double-tap Middle C
Expected: Product add works
```

## Switching to Real Mode

Once test mode works perfectly:

1. **Set HA_TOKEN:**
   ```bash
   export HA_TOKEN="your-long-lived-token-here"
   ```

2. **Run without --test flag:**
   ```bash
   python3 src/bridge.py
   ```

3. **Verify HA connection:**
   ```
   [INFO] bridge: Connected and authenticated to Home Assistant
   ```

4. **Test one product add:**
   - Arm with sequence
   - Double-tap a mapped key
   - Check Picnic cart in HA
   - Listen for announcement

## Troubleshooting Test Mode

### "No MIDI ports found"
```bash
# Check USB connection
lsusb

# List MIDI devices
amidi -l

# Test with standalone tool
python3 src/midi.py
```

### "Config file not found"
```bash
# Check you're in the right directory
pwd
# Should be: /home/pi/DigitalPianoPicnic

# Copy example configs if needed
cp config/app.yaml.example config/app.yaml
cp config/mapping.yaml.example config/mapping.yaml
```

### "No product mapping for note X"
Edit `config/mapping.yaml` and add the note:
```yaml
notes:
  60:  # Your note number
    product_id: s1234567
    product_name: "Your Product"
    amount: 1
```

### Double-tap too hard/easy
Edit `config/app.yaml`:
```yaml
confirmation:
  double_tap_window_ms: 1000  # Increase for easier timing
```

## Command Reference

```bash
# Test mode (no HA)
python3 src/bridge.py --test

# Real mode (requires HA)
python3 src/bridge.py

# Custom config in test mode
python3 src/bridge.py --test --config /path/to/config.yaml

# Help
python3 src/bridge.py --help
```

## Next Steps

After successful test mode validation:
1. ✅ MIDI functionality confirmed
2. ✅ Arming/disarming works
3. ✅ Double-tap timing tuned
4. ✅ Note mappings verified
5. ➡️ Switch to real mode with `HA_TOKEN`
6. ➡️ Test one product add manually
7. ➡️ Install as systemd service

---

**Test mode is your friend!** Use it whenever you change config or debug issues. No risk of accidentally ordering 100 bananas! 🍌
