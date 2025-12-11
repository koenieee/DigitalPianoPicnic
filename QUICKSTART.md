# 🎹 Quick Start Guide

Get your digital piano shopping in **5 minutes**!

## Prerequisites Check

✅ Raspberry Pi with Raspbian OS  
✅ Digital piano connected via USB  
✅ Home Assistant running with Picnic integration  
✅ Home Assistant Assist Satellite configured  

## Step 1: Transfer Files

From your Windows machine:

```powershell
# Option A: Using SCP
scp -r C:\intraffic\DigitalPianoPicnic pi@raspberrypi.local:~/

# Option B: Using Git (recommended)
cd C:\intraffic\DigitalPianoPicnic
git init
git add .
git commit -m "Initial setup"
# Push to your repo, then clone on Pi
```

## Step 2: Run Setup (on Raspberry Pi)

```bash
ssh pi@raspberrypi.local
cd ~/DigitalPianoPicnic
chmod +x setup.sh
./setup.sh
```

When prompted, paste your Home Assistant Long-Lived Access Token (get it from `http://homeassistant.local:8123/profile`).

## Step 3: Configure

### Get Your Device ID

In Home Assistant:
1. Settings → Devices & Services
2. Click your Assist Satellite device
3. Copy the ID from the URL (e.g., `4f17bb6b7102f82e8a91bf663bcb76f9`)

### Edit Main Config

```bash
nano config/app.yaml
```

Change line 3 to your HA URL (or keep default):
```yaml
url: ws://homeassistant.local:8123/api/websocket
```

Change line 58 to your Assist Satellite device ID:
```yaml
device_id: YOUR_DEVICE_ID_HERE
```

Save: `Ctrl+X`, `Y`, `Enter`

### Map Your Products

```bash
nano config/mapping.yaml
```

Find Picnic product IDs:
1. Add products to cart in Picnic app
2. In Home Assistant: Developer Tools → States → `sensor.picnic_cart_items`
3. Copy product IDs from attributes

Update note mappings (example):
```yaml
notes:
  60:  # Middle C
    product_id: s1018231
    product_name: "Picnic cola zero"
    amount: 1
```

Save: `Ctrl+X`, `Y`, `Enter`

## Step 4: Test

```bash
# Test mode first (no Home Assistant needed):
python3 src/bridge.py --test

# Then test with Home Assistant:
python3 src/bridge.py
```

**Test sequence:**
1. Play C-D-E (arming sequence) → Should see "System ARMED"
2. Play Middle C twice quickly → Should see product action
   - Test mode: "[TEST MODE] Would add product..."
   - Real mode: Actually adds to cart + hear announcement
3. Press `Ctrl+C` to stop

## Step 5: Install Service

```bash
sudo ./deployment/install-service.sh
```

When prompted:
- Enter your HA token (same as before)
- Choose `Y` to start now

## Step 6: Verify

```bash
sudo systemctl status midi-ha.service
sudo journalctl -u midi-ha.service -f
```

You should see:
- "Connected and authenticated to Home Assistant"
- "Listening for MIDI events..."

## Usage

1. **Arm**: Play C-D-E (or your custom sequence)
2. **Shop**: Play any mapped key **twice** within 800ms
3. **Hear**: Product name announced
4. **Repeat**: Add more items (stays armed for 60s)

## Customize

### Change Arming Password

Edit `config/app.yaml`, line 34:
```yaml
sequence: [60, 64, 67]  # Change to C-E-G (C major chord notes)
```

MIDI note reference: Middle C=60, then +1 per semitone (C#=61, D=62, etc.)

### Change Double-Tap Speed

Edit `config/app.yaml`, line 49:
```yaml
double_tap_window_ms: 1000  # Make it easier (was 800)
```

### Map More Products

Edit `config/mapping.yaml`, add more notes:
```yaml
notes:
  61:  # C#
    product_id: s2222222
    product_name: "Milk"
    amount: 1
```

**After any config change:**
```bash
sudo systemctl restart midi-ha.service
```

## Troubleshooting

### "No MIDI ports found"
```bash
lsusb  # Check USB device connected
amidi -l  # List MIDI ports
```

### "Authentication failed"
- Regenerate token in Home Assistant
- Update in service: `sudo nano /etc/systemd/system/midi-ha.service`
- Restart: `sudo systemctl restart midi-ha.service`

### "Product not added"
- Check product ID is correct (case-sensitive!)
- Test in HA Developer Tools: Services → `picnic.add_product`

### "No announcement"
- Check device ID is correct
- Test in HA Developer Tools: Services → `assist_satellite.announce`
- Verify satellite is online

### "Want to test without Home Assistant?"
```bash
python3 src/bridge.py --test
```
See `TEST_MODE.md` for full testing guide.

## Getting MIDI Note Numbers

Run test mode:
```bash
python3 src/midi.py
```

Press keys on your piano to see their note numbers. Press `Ctrl+C` to stop.

## Tips

- 🎼 Map frequently-used items to white keys near middle C
- 🎵 Use black keys for less common items  
- 🎶 Higher octaves for different product categories
- 🎹 Practice your arming sequence so it's muscle memory
- 🔊 Adjust announcement volume in Home Assistant

## Need Help?

1. **Check logs**: `sudo journalctl -u midi-ha.service -f`
2. **Read full docs**: `cat README.md` or `cat docs/plan.md`
3. **Test modules**: `python3 src/midi.py` or `python3 src/ha_client.py`

---

**Happy musical shopping!** 🎹🛒✨

Made with ❤️ for the laziest grocery list ever invented.
