# Product Search Tools

This directory contains tools to search for Picnic products and manage your keyboard mappings.

## Tools Available

1. **search_web.py** - Web interface (recommended)
2. **search_products.py** - Command-line interface

## Installation

```bash
# Install the optional Picnic API dependency
pip install python-picnic-api
```

Note: PyYAML is already installed as part of the main project requirements.

Or in your virtual environment:

```bash
cd ~/DigitalPianoPicnic
source venv/bin/activate
pip install python-picnic-api
```

## Web Interface (Recommended)

The web interface provides the easiest way to search for products and configure your keyboard mappings.

### Starting the Server

```bash
# Set credentials
export PICNIC_USERNAME='your@email.com'
export PICNIC_PASSWORD='yourpassword'

# Start the web server
python3 tools/search_web.py

# Access from browser at http://localhost:8080
```

### Features

- 🔍 **Real-time search** - Type and press Enter
- 🎹 **Keyboard key selector** - Choose MIDI note number for each product
- 💾 **One-click save** - Automatically saves to `config/mapping.yaml`
- 📱 **Mobile-friendly** - Responsive design
- ✨ **Clean interface** - Modern gradient design with hover effects

### Remote Access

Run on Raspberry Pi and access from your PC:

```bash
# On the Pi
cd ~/DigitalPianoPicnic
source venv/bin/activate
export PICNIC_USERNAME='your@email.com'
export PICNIC_PASSWORD='yourpassword'
python3 tools/search_web.py

# From your PC's browser: http://raspberrypi.local:8080
```

### Custom Port

```bash
python3 tools/search_web.py --port 9000
```

## Command-Line Interface (CLI)

For scripting or terminal-only environments.

## Usage

### Option 1: Environment Variables (Recommended)

For security, store your credentials in environment variables:

```bash
export PICNIC_USERNAME='your@email.com'
export PICNIC_PASSWORD='yourpassword'
export PICNIC_COUNTRY='NL'  # Optional, defaults to NL

# Search for a product
python3 tools/search_products.py "coca cola zero"

# Interactive mode
python3 tools/search_products.py --interactive
```

### Option 2: Command Line Arguments

```bash
python3 tools/search_products.py "coca cola zero" \
  --username your@email.com \
  --password yourpassword \
  --country NL
```

### Interactive Mode

```bash
python3 tools/search_products.py --interactive

# Then type product names:
Search for: coca cola zero
Search for: bananas
Search for: quit
```

## Example Output

```
🔍 Searching for: 'coca cola zero'
============================================================
✓ Found 3 result(s):

1. Coca-Cola Zero sugar 6-pack
   Product ID: s1018231
   Price: €4.99 6 x 330ml
   # Add to mapping.yaml:
   60:
     product_id: s1018231
     product_name: "Coca-Cola Zero sugar 6-pack"
     amount: 1

2. Coca-Cola Zero sugar 12-pack
   Product ID: s1018232
   Price: €8.99 12 x 330ml
   # Add to mapping.yaml:
   61:
     product_id: s1018232
     product_name: "Coca-Cola Zero sugar 12-pack"
     amount: 1
```

## Quick Reference

Common products to search for:
- `coca cola zero`
- `bananas`
- `whole milk`
- `bread`
- `toilet paper`
- `kitchen roll`
- `cucumber`
- `yoghurt`
- `coffee`

## Security Note

**Do NOT commit your credentials to git!**

Use environment variables or create a `.env` file (which is in `.gitignore`):

```bash
# Create .env file
cat > .env << EOF
PICNIC_USERNAME=your@email.com
PICNIC_PASSWORD=yourpassword
PICNIC_COUNTRY=NL
EOF

# Load it
source .env

# Use the tool
python3 tools/search_products.py "bananas"
```

## Troubleshooting

### "python_picnic_api2 is not installed"

Install it:
```bash
pip install python-picnic-api
```

### "Failed to connect"

- Check your username and password
- Make sure you can login to the Picnic app/website
- Try a different country code if you're not in NL

### Search returns no results

- Try different search terms (Dutch names work best for NL)
- Make sure the product exists in your Picnic catalog
- Some products might have different names than you expect
