#!/usr/bin/env python3
"""
Fast Picnic Product Search Web Interface using Flask

Install: pip install flask
Usage: python3 tools/search_web_fast.py
"""

import os
import sys
import json
from pathlib import Path
from flask import Flask, request, jsonify, send_file
import gzip
import io

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # Cache static content for 1 year
app.config['TEMPLATES_AUTO_RELOAD'] = False

# Global variables
picnic_api = None
picnic_username = None
picnic_password = None
config_path = Path(__file__).parent.parent / 'config' / 'mapping.yaml'

# Cache the HTML template
HTML_CACHE = None
TEMPLATE_FILE = Path(__file__).parent / 'search_template.html'

def get_html_template():
    """Load HTML template from file"""
    # Always reload to get latest changes during development
    print("   → Loading template from templates/index.html...")
    template_path = Path(__file__).parent / 'templates' / 'index.html'
    if template_path.exists():
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        return "<html><body><h1>Template not found</h1></body></html>"


@app.after_request
def compress_response(response):
    """Automatically compress large responses"""
    accept_encoding = request.headers.get('Accept-Encoding', '')
    
    if 'gzip' not in accept_encoding:
        return response
    
    if response.status_code < 200 or response.status_code >= 300:
        return response
    
    if 'Content-Encoding' in response.headers:
        return response
    
    # Skip compression for file responses (passthrough mode)
    if response.direct_passthrough:
        return response
    
    # Skip small responses
    try:
        if len(response.data) < 1024:
            return response
    except (RuntimeError, AttributeError):
        # Response doesn't support data access
        return response
    
    gzip_buffer = io.BytesIO()
    with gzip.GzipFile(mode='wb', fileobj=gzip_buffer) as gzip_file:
        gzip_file.write(response.data)
    
    response.data = gzip_buffer.getvalue()
    response.headers['Content-Encoding'] = 'gzip'
    response.headers['Content-Length'] = len(response.data)
    
    return response


@app.route('/')
def index():
    """Serve main HTML page"""
    template_path = Path(__file__).parent / 'templates' / 'index.html'
    if template_path.exists():
        return send_file(template_path), 200, {'Cache-Control': 'public, max-age=3600'}
    else:
        # Fallback to embedded template
        return get_html_template(), 200, {'Cache-Control': 'public, max-age=3600'}


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files (CSS, JS)"""
    static_dir = Path(__file__).parent / 'static'
    return send_file(static_dir / filename)


@app.route('/api/search')
def search():
    """Search for products"""
    global picnic_api, picnic_username, picnic_password
    
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    if not picnic_api:
        return jsonify({'error': 'Picnic API not initialized'}), 500
    
    try:
        print(f"\n🔍 Searching for: {query}")
        results = picnic_api.search(query)
        print(f"✓ Raw search completed")
        
        # Handle nested structure
        items = []
        if isinstance(results, list) and len(results) > 0:
            if isinstance(results[0], dict) and 'items' in results[0]:
                print(f"  → Found nested 'items' structure")
                items = results[0]['items']
            else:
                items = results
        else:
            items = results if isinstance(results, list) else []
        
        formatted_results = []
        for item in items[:20]:  # Limit to 20 results
            print(f"  - Processing: {item.get('name', 'Unknown')}")
            print(f"    → Full item keys: {list(item.keys())}")  # Debug: show all keys
            
            product_id = item.get('id')
            if not product_id:
                print(f"    ⚠️ Skipping item without ID")
                continue
            
            # Try multiple possible image field names
            image_id = item.get('image_id') or item.get('imageId') or item.get('image') or ''
            
            # Check decorators for image
            decorators = item.get('decorators', [])
            decorator_image = None
            if decorators:
                print(f"    → Found {len(decorators)} decorators")
                for dec in decorators:
                    if isinstance(dec, dict) and 'image_id' in dec:
                        decorator_image = dec['image_id']
                        print(f"    → Decorator image_id: {decorator_image}")
                        break
            
            # Use decorator image if available, otherwise use main image_id
            final_image_id = decorator_image or image_id
            print(f"    → Final image_id: '{final_image_id}'")  # Debug log
            
            # Try different URL patterns - the image might be directly accessible
            image_url = ''
            if final_image_id:
                # Try both small.png and just the hash
                image_url = f'https://storefront-prod.nl.picnicinternational.com/static/images/{final_image_id}/small.png'
                # Fallback URL if needed
                # image_url = f'https://storefront-prod.nl.picnicinternational.com/static/images/{final_image_id}'
            
            formatted_results.append({
                'id': product_id,
                'name': item.get('name', 'Unknown'),
                'price': f"{item.get('display_price', 0) / 100:.2f}",
                'unit': item.get('unit_quantity', ''),
                'image_id': final_image_id,  # Add image_id to response
                'image_url': image_url
            })
        
        print(f"✓ Formatted {len(formatted_results)} results")
        return jsonify({'results': formatted_results})
    except Exception as e:
        error_str = str(e).lower()
        if 'auth' in error_str or 'login' in error_str or 'session' in error_str:
            print(f"⚠️ Authentication error detected, re-authenticating...")
            print(f"   → Username available: {picnic_username is not None}")
            print(f"   → Password available: {picnic_password is not None}")
            try:
                if picnic_username and picnic_password:
                    print(f"   → Creating new PicnicAPI with username: {picnic_username}")
                    from python_picnic_api2 import PicnicAPI
                    new_api = PicnicAPI(picnic_username, picnic_password)
                    print(f"   → New API instance created successfully")
                    picnic_api = new_api
                    print(f"✓ Re-authenticated successfully, retrying search...")
                    # Retry the search
                    results = picnic_api.search(query)
                    items = []
                    if isinstance(results, list) and len(results) > 0:
                        if isinstance(results[0], dict) and 'items' in results[0]:
                            items = results[0]['items']
                        else:
                            items = results
                    else:
                        items = results if isinstance(results, list) else []
                    
                    formatted_results = []
                    for item in items[:20]:
                        product_id = item.get('id')
                        if not product_id:
                            continue
                        image_id = item.get('image_id', '')
                        formatted_results.append({
                            'id': product_id,
                            'name': item.get('name', 'Unknown'),
                            'price': f"{item.get('display_price', 0) / 100:.2f}",
                            'unit': item.get('unit_quantity', ''),
                            'image_url': f'https://storefront-prod.nl.picnicinternational.com/static/images/{image_id}/small.png' if image_id else ''
                        })
                    return jsonify({'results': formatted_results})
            except Exception as retry_error:
                print(f"❌ Re-authentication failed: {retry_error}")
        
        print(f"❌ Search error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/cart')
def get_cart():
    """Get current shopping cart"""
    global picnic_api
    
    if not picnic_api:
        return jsonify({'error': 'Picnic API not initialized'}), 500
    
    try:
        print("\n🛒 Fetching cart...")
        cart = picnic_api.get_cart()
        print(f"✓ Cart loaded: {len(cart.get('items', []))} items")
        
        # Debug: Print cart structure
        print("\n📦 DEBUG: Cart structure:")
        import json
        print(json.dumps(cart, indent=2, ensure_ascii=False))
        
        # Debug: Check first item in detail
        if cart.get('items') and len(cart['items']) > 0:
            first_order_line = cart['items'][0]
            print("\n🔍 DEBUG: First order line:")
            print(json.dumps(first_order_line, indent=2, ensure_ascii=False))
            
            if first_order_line.get('items') and len(first_order_line['items']) > 0:
                first_article = first_order_line['items'][0]
                print("\n🔍 DEBUG: First article:")
                print(json.dumps(first_article, indent=2, ensure_ascii=False))
                
                if first_article.get('decorators'):
                    print("\n🎨 DEBUG: Decorators found:")
                    for decorator in first_article['decorators']:
                        print(f"  - Type: {decorator.get('type')}, Keys: {list(decorator.keys())}")
        
        return jsonify(cart)
    except Exception as e:
        print(f"✗ Cart error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/mappings')
def get_mappings():
    """Get list of mapped MIDI notes"""
    try:
        import yaml
        if not config_path.exists():
            return jsonify({'mapped_notes': []})
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f) or {}
        
        note_mappings = config.get('note_mappings', {})
        mapped_notes = [int(note) for note in note_mappings.keys()]
        
        return jsonify({'mapped_notes': mapped_notes})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/print-data')
def get_print_data():
    """Get detailed mapping data for printing"""
    try:
        import yaml
        if not config_path.exists():
            return jsonify({'mappings': []})
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f) or {}
        
        note_mappings = config.get('note_mappings', {})
        
        mappings_list = []
        cache_dir = config_path.parent / 'image_cache'
        
        for note_str, mapping in note_mappings.items():
            note_num = int(note_str)
            
            notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            octave = (note_num - 12) // 12
            note_index = (note_num - 12) % 12
            note_name = f"{notes[note_index]}{octave}"
            
            # Try to load cached image (base64 data URL)
            image_url = ''
            product_id = mapping.get('product_id', '')
            if product_id:
                cache_file = cache_dir / f'{product_id}.txt'
                if cache_file.exists():
                    try:
                        image_url = cache_file.read_text(encoding='utf-8')
                    except:
                        pass
            
            mappings_list.append({
                'note': note_num,
                'note_name': note_name,
                'product_id': product_id,
                'product_name': mapping.get('product_name', ''),
                'amount': mapping.get('amount', 1),
                'image': image_url
            })
        
        return jsonify({'mappings': mappings_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/save', methods=['POST'])
def save_mapping():
    """Save product mapping to config"""
    try:
        data = request.get_json()
        
        print(f"\n💾 Saving mapping:")
        print(f"  Note: {data.get('note')}")
        print(f"  Product ID: {data.get('product_id')}")
        print(f"  Product Name: {data.get('product_name')}")
        print(f"  Amount: {data.get('amount')}")
        print(f"  Double Tap: {data.get('double_tap', False)}")
        print(f"  Image ID: {data.get('image_id', '')}")
        
        result = save_to_config(
            data.get('note'),
            data.get('product_id'),
            data.get('product_name'),
            data.get('amount'),
            data.get('double_tap', False),
            data.get('image_id', '')  # Add image_id parameter
        )
        
        print(f"  Result: {result}")
        
        return jsonify(result)
    except Exception as e:
        print(f"✗ Save error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/mapping/<int:note>', methods=['DELETE'])
def delete_mapping(note):
    """Delete a key mapping from config"""
    try:
        import yaml
        
        print(f"\n🗑️ Deleting mapping for note: {note}")
        print(f"Config path: {config_path}")
        
        if not config_path.exists():
            print(f"✗ Config file not found at: {config_path}")
            return jsonify({'error': 'Config file not found'}), 404
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        
        note_mappings = config.get('note_mappings', {})
        note_str = str(note)
        
        print(f"Available mappings: {list(note_mappings.keys())}")
        print(f"Looking for note: '{note_str}' (type: {type(note_str)})")
        
        if note_str not in note_mappings:
            # Try as integer key as well
            if note not in note_mappings:
                print(f"✗ Mapping not found. Keys in file: {list(note_mappings.keys())[:10]}")
                return jsonify({'error': f'No mapping found for note {note}'}), 404
            # Found as integer, use that
            note_key = note
        else:
            note_key = note_str
        
        # Delete the mapping
        print(f"Deleting key: '{note_key}'")
        del note_mappings[note_key]
        config['note_mappings'] = note_mappings
        
        # Save updated config with proper formatting
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False, width=120)
        
        print(f"✓ Deleted mapping for note {note}")
        
        return jsonify({'success': True, 'message': f'Deleted mapping for note {note}'})
        
    except Exception as e:
        print(f"✗ Delete error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

def download_and_cache_image(product_id, image_id):
    """Download product image from Picnic CDN and cache as base64"""
    try:
        import base64
        import urllib.request
        
        # Create image cache directory
        cache_dir = config_path.parent / 'image_cache'
        cache_dir.mkdir(exist_ok=True)
        cache_file = cache_dir / f'{product_id}.txt'
        
        # Check if already cached
        if cache_file.exists():
            return cache_file.read_text(encoding='utf-8')
        
        # Download image from Picnic CDN
        image_url = f'https://storefront-prod.nl.picnicinternational.com/static/images/{image_id}/small.png'
        print(f"  → Downloading image: {image_url}")
        
        with urllib.request.urlopen(image_url, timeout=5) as response:
            image_data = response.read()
            
        # Convert to base64 data URL
        base64_data = base64.b64encode(image_data).decode('utf-8')
        data_url = f'data:image/png;base64,{base64_data}'
        
        # Cache to file
        cache_file.write_text(data_url, encoding='utf-8')
        print(f"  ✓ Image cached: {cache_file}")
        
        return data_url
    except Exception as e:
        print(f"  ⚠️ Image download failed: {e}")
        return None


def save_to_config(note_number, product_id, product_name, amount, double_tap=False, image_id=''):
    """Save product mapping to YAML config"""
    try:
        import yaml
        
        # Ensure config directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing config or create new
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}
        
        # Ensure note_mappings section exists
        if 'note_mappings' not in config:
            config['note_mappings'] = {}
        
        # Build mapping entry
        mapping = {
            'product_id': product_id,
            'product_name': product_name,
            'amount': int(amount)
        }
        
        # Get product image and cache it
        if image_id:
            try:
                print(f"  → Caching image for {product_id} (image_id: {image_id})...")
                image_data_url = download_and_cache_image(product_id, image_id)
                if image_data_url:
                    mapping['image_data'] = image_data_url
            except Exception as e:
                print(f"  ⚠️ Could not cache product image: {e}")
        
        # Only add confirmation if double_tap is True
        if double_tap:
            mapping['confirmation'] = 'double_tap'
        
        # Save mapping
        config['note_mappings'][int(note_number)] = mapping
        
        # Write back to file
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        print(f"✓ Saved: Note {note_number} → {product_name} (x{amount})")
        return {'status': 'success', 'message': 'Mapping saved'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def main():
    global picnic_api, picnic_username, picnic_password
    
    print("🚀 Initializing Fast Picnic Product Search Web Interface")
    print("=" * 60)
    
    # Load credentials
    picnic_username = os.environ.get('PICNIC_USERNAME')
    picnic_password = os.environ.get('PICNIC_PASSWORD')
    
    if not picnic_username or not picnic_password:
        print("❌ Error: PICNIC_USERNAME and PICNIC_PASSWORD must be set")
        print("\nOn Windows PowerShell:")
        print('  $env:PICNIC_USERNAME = "your@email.com"')
        print('  $env:PICNIC_PASSWORD = "yourpassword"')
        print("\nOn Linux/Mac:")
        print('  export PICNIC_USERNAME="your@email.com"')
        print('  export PICNIC_PASSWORD="yourpassword"')
        sys.exit(1)
    
    # Initialize Picnic API
    print(f"🔐 Logging in as: {picnic_username}")
    try:
        from python_picnic_api2 import PicnicAPI
        picnic_api = PicnicAPI(picnic_username, picnic_password)
    except Exception as e:
        print(f"❌ Failed to initialize Picnic API: {e}")
        sys.exit(1)
    
    print("✓ Picnic API initialized\n")
    
    # Pre-load HTML template to avoid slow first page load
    print("📄 Pre-loading HTML template...")
    try:
        get_html_template()
        print("✓ Template loaded and cached\n")
    except Exception as e:
        print(f"⚠️ Template pre-load failed (will load on first request): {e}\n")
    
    port = 8080
    print(f"🌐 Starting FAST web server on port {port}...")
    print(f"\n📱 Open in your browser:")
    print(f"   http://localhost:{port}")
    print(f"   http://127.0.0.1:{port}")
    print(f"\n⚡ Using Flask with Waitress production server")
    print(f"⌨️  Press Ctrl+C to stop\n")
    
    # Use Waitress production WSGI server (much faster than Werkzeug)
    try:
        from waitress import serve
        print("✓ Using Waitress WSGI server (production-ready)")
        serve(app, host='0.0.0.0', port=port, threads=6, channel_timeout=30)
    except ImportError:
        print("⚠️  Waitress not found, using Werkzeug (install: pip install waitress)")
        app.run(host='0.0.0.0', port=port, threaded=True, debug=False)


if __name__ == '__main__':
    main()
