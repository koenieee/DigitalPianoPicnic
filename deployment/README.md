# Systemd Services

This directory contains systemd service files for running Digital Piano Picnic components as system services.

## Services

### 1. MIDI Bridge (`midi-ha.service`)
Bridges MIDI piano input to Home Assistant automations.

### 2. Web Interface (`picnic-web.service`)
Product search web interface for mapping products to piano keys.

## Installation

### Quick Install (Both Services)
```bash
sudo chmod +x deployment/install-all-services.sh
sudo deployment/install-all-services.sh
```

### Install Individual Services
```bash
sudo chmod +x deployment/install-service.sh
sudo deployment/install-service.sh
```

## Configuration

### MIDI Bridge
Edit `deployment/midi-ha.service` and set:
- `HA_TOKEN`: Your Home Assistant long-lived access token

### Web Interface
Edit `deployment/picnic-web.service` and set:
- `PICNIC_USERNAME`: Your Picnic account email
- `PICNIC_PASSWORD`: Your Picnic account password

## Manual Installation

```bash
# Copy service files
sudo cp deployment/midi-ha.service /etc/systemd/system/
sudo cp deployment/picnic-web.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services (start on boot)
sudo systemctl enable midi-ha.service
sudo systemctl enable picnic-web.service

# Start services
sudo systemctl start midi-ha.service
sudo systemctl start picnic-web.service
```

## Management Commands

### Status
```bash
sudo systemctl status midi-ha.service
sudo systemctl status picnic-web.service
```

### Start/Stop/Restart
```bash
sudo systemctl start midi-ha.service
sudo systemctl stop midi-ha.service
sudo systemctl restart midi-ha.service

sudo systemctl start picnic-web.service
sudo systemctl stop picnic-web.service
sudo systemctl restart picnic-web.service
```

### View Logs
```bash
# Follow logs in real-time
sudo journalctl -u midi-ha.service -f
sudo journalctl -u picnic-web.service -f

# View recent logs
sudo journalctl -u midi-ha.service -n 100
sudo journalctl -u picnic-web.service -n 100

# View logs since today
sudo journalctl -u midi-ha.service --since today
sudo journalctl -u picnic-web.service --since today
```

### Disable Service (prevent auto-start)
```bash
sudo systemctl disable midi-ha.service
sudo systemctl disable picnic-web.service
```

## Accessing the Web Interface

After starting `picnic-web.service`:
- Local: http://localhost:8080
- Network: http://YOUR_PI_IP:8080 (e.g., http://192.168.1.100:8080)

Find your Pi's IP: `hostname -I`

## Troubleshooting

### Service won't start
```bash
# Check service status for errors
sudo systemctl status picnic-web.service

# View detailed logs
sudo journalctl -u picnic-web.service -n 50

# Check if port 8080 is already in use
sudo netstat -tulpn | grep 8080
```

### MIDI Bridge not responding
```bash
# Check if MIDI device is connected
aconnect -l

# Restart the service
sudo systemctl restart midi-ha.service

# Check logs
sudo journalctl -u midi-ha.service -f
```

### Update credentials
```bash
# Edit the service file
sudo nano /etc/systemd/system/picnic-web.service
# or
sudo nano /etc/systemd/system/midi-ha.service

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart picnic-web.service
sudo systemctl restart midi-ha.service
```

## Uninstall

```bash
# Stop and disable services
sudo systemctl stop midi-ha.service picnic-web.service
sudo systemctl disable midi-ha.service picnic-web.service

# Remove service files
sudo rm /etc/systemd/system/midi-ha.service
sudo rm /etc/systemd/system/picnic-web.service

# Reload systemd
sudo systemctl daemon-reload
```
