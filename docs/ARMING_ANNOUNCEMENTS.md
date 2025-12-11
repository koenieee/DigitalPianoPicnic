# Arming System Voice Announcements

The MIDI bridge now announces when the piano system is armed or disarmed using Home Assistant's Assist Satellite service.

## Features

### Armed Announcement
When the system becomes armed (via sequence, chord, or both), it announces:
- **Default message**: "Piano is now armed and ready for shopping"
- Plays after successful sequence or chord completion
- Only announces when transitioning from disarmed to armed

### Disarmed Announcement  
When the system disarms (timeout, manual reset), it announces:
- **Default message**: "Piano has been disarmed"
- Only announces when transitioning from armed to disarmed

## Configuration

Add these settings to your `config/app.yaml` under the `arming` section:

```yaml
arming:
  enabled: true
  sequence: [60, 62, 64]  # Your arming sequence
  
  # Voice announcements
  announce_on_arm: true
  announce_on_disarm: true
  arm_message: "Piano is now armed and ready for shopping"
  disarm_message: "Piano has been disarmed"
```

### Configuration Options

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `announce_on_arm` | boolean | `true` | Enable announcement when system arms |
| `announce_on_disarm` | boolean | `true` | Enable announcement when system disarms |
| `arm_message` | string | See above | Message spoken when arming |
| `disarm_message` | string | See above | Message spoken when disarming |

## How It Works

1. **Arming Detection**: The `ArmingStateMachine` tracks state transitions
2. **Announcement Trigger**: When state changes to `ARMED`, announcement is queued
3. **HA Client**: Uses `assist_satellite.announce` service via the HA REST API
4. **Async Execution**: Announcements run in background without blocking MIDI processing

## Technical Details

### Code Changes

Modified `src/bridge.py`:
- Added `announce_on_arm`, `announce_on_disarm`, `arm_message`, `disarm_message` config
- Added `set_ha_client()` method to pass HA client to arming state machine
- Added `_announce()` async method to send announcements
- Added announcement calls in `on_note()` when arming via sequence
- Added announcement calls in `on_chord()` when arming via chord
- Added announcement call in `reset()` when disarming

### Device Selection

The announcement uses the device_id from the `announce` section of your config:

```yaml
announce:
  enabled: true
  device_id: 4f17bb6b7102f82e8a91bf663bcb76f9  # Your satellite device ID
```

If `device_id` is `None`, the announcement goes to all available satellites.

## Testing

1. Start the MIDI bridge: `sudo systemctl start midi-ha`
2. Play your arming sequence or chord
3. Listen for "Piano is now armed and ready for shopping"
4. Wait for auto-disarm timeout or press disarm keys
5. Listen for "Piano has been disarmed"

## Customization Examples

### Simple Messages
```yaml
arm_message: "System armed"
disarm_message: "System disarmed"
```

### Playful Messages
```yaml
arm_message: "Let's go shopping! Piano is ready."
disarm_message: "Shopping mode deactivated"
```

### Security-Style Messages
```yaml
arm_message: "Security sequence accepted. System armed."
disarm_message: "System has been secured"
```

### Multi-Language Support
Use your Home Assistant's language settings - the satellite will use its configured TTS language.

## Troubleshooting

### No Announcements Heard

1. **Check HA connection**: Look for "System ARMED" in logs
2. **Check satellite device**: Verify device_id in config
3. **Check satellite status**: Ensure satellite is online in HA
4. **Check announce config**: `announce.enabled: true` in config
5. **Check logs**: Look for "Arming announcement sent" messages

### Announcement Delayed

- Announcements are async and may have slight delay
- Network latency to Home Assistant
- TTS processing time on satellite

### Wrong Device Announces

- Verify `device_id` in config matches your satellite
- Find correct ID in HA: Settings → Devices → Your Satellite → Device ID in URL

## See Also

- [TEST_MODE.md](../TEST_MODE.md) - Testing without Home Assistant
- [QUICKSTART.md](../QUICKSTART.md) - Initial setup guide
- [PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md) - Architecture overview
