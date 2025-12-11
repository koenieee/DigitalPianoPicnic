// Global variables
let currentProductIndex = -1;
let currentProductId = '';
let currentProductName = '';
let currentImageId = '';
let mappedKeys = new Set(); // Store mapped MIDI note numbers

// Piano keyboard data
const notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
const blackKeyPositions = [1, 3, 6, 8, 10]; // C#, D#, F#, G#, A# positions in octave

// Load mapped keys from config on page load
async function loadMappedKeys() {
    try {
        const response = await fetch('/api/mappings');
        if (response.ok) {
            const data = await response.json();
            mappedKeys = new Set(data.mapped_notes || []);
            console.log('Loaded mapped keys:', Array.from(mappedKeys));
        }
    } catch (e) {
        console.log('Could not load mappings:', e);
    }
}

function initPianoKeys() {
    const container = document.getElementById('pianoDisplay');
    
    // Create full 88-key keyboard (A0 to C8) in one horizontal line
    let html = '<div class="piano-container">';
    html += '<div style="text-align: center; color: #999; margin-bottom: 10px;">88 Keys • A0 (21) to C8 (108) • Scroll horizontally → <span style="color: #4caf50;">■ Green = Already Mapped</span><br><span style="color: #667eea; font-weight: bold;">⌨️ Use your keyboard: QWERTY rows = different octaves, ZXC/ASD/QWE keys = white keys</span></div>';
    html += '<div class="piano-keys">';
    
    // Count total white keys (52 for 88-key piano: A0-B0 + 7 octaves + C8)
    const whiteKeys = [];
    for (let midi = 21; midi <= 108; midi++) {
        const noteIndex = midi % 12;
        const isWhiteKey = [0, 2, 4, 5, 7, 9, 11].includes(noteIndex);
        if (isWhiteKey) {
            whiteKeys.push(midi);
        }
    }
    const totalWhiteKeys = whiteKeys.length; // Should be 52
    
    // Render all white keys with equal spacing
    const debugKeys = [];
    const allKeys = [];
    for (let midi = 21; midi <= 108; midi++) {
        const noteIndex = midi % 12;
        const isWhiteKey = [0, 2, 4, 5, 7, 9, 11].includes(noteIndex);
        
        if (isWhiteKey) {
            const octave = Math.floor(midi / 12) - 1;
            const noteName = notes[noteIndex] + octave;
            const isMiddleC = midi === 60;
            const isMapped = mappedKeys.has(midi);
            
            // Debug: Store first 10 keys for logging
            if (debugKeys.length < 10) {
                debugKeys.push(`${noteName}=${midi}`);
            }
            
            // Store ALL keys for additional debugging
            allKeys.push({midi, noteName, noteIndex, octave});
            
            html += `<div class="white-key ${isMiddleC ? 'middle-c' : ''} ${isMapped ? 'mapped' : ''}" onclick="selectKey(${midi})" data-note="${midi}" title="MIDI ${midi} = ${noteName} - ${isMapped ? 'Already mapped' : 'Click to assign'}">
                <span class="key-label">${noteName}</span>
            </div>`;
        }
    }
    
    console.log('First 10 white keys rendered:', debugKeys.join(', '));
    console.log('Keys around Middle C:', allKeys.slice(20, 28).map(k => `${k.noteName}=${k.midi}`).join(', '));
    
    // Black keys disabled for now (only white keys can be assigned)
    // Then, render black keys positioned on top
    for (let midi = 21; midi <= 108; midi++) {
        const noteIndex = midi % 12;
        const isBlackKey = [1, 3, 6, 8, 10].includes(noteIndex);
        
        if (isBlackKey) {
            const octave = Math.floor(midi / 12) - 1;
            const noteName = notes[noteIndex] + octave;
            const isMapped = mappedKeys.has(midi);
            
            // Calculate which white key this black key comes after
            // For black keys, we need to count white keys up to and including the previous white key
            let whiteKeysBefore = 0;
            for (let note = 21; note <= midi; note++) {
                const nIdx = note % 12;
                if ([0, 2, 4, 5, 7, 9, 11].includes(nIdx)) {
                    whiteKeysBefore++;
                }
            }
            // Subtract 1 because we want the white key BEFORE this black key
            whiteKeysBefore = whiteKeysBefore - 1;
            
            // Position black key based on real piano layout
            // Each white key is 40px + 2px margin = 42px
            const whiteKeyWidth = 42;
            const blackKeyWidth = 28;
            
            // Black keys are positioned to create visual groups: [C# D#] gap [F# G# A#] gap
            // C# is between C-D, D# between D-E, F# between F-G, G# between G-A, A# between A-B
            let positionOffset;
            if (noteIndex === 1) { // C# - slightly left of center between C and D
                positionOffset = whiteKeyWidth * 0.75;
            } else if (noteIndex === 3) { // D# - slightly right of center between D and E
                positionOffset = whiteKeyWidth * 0.85;
            } else if (noteIndex === 6) { // F# - slightly left in the group of 3
                positionOffset = whiteKeyWidth * 0.72;
            } else if (noteIndex === 8) { // G# - center of the group of 3
                positionOffset = whiteKeyWidth * 0.80;
            } else { // A# (10) - slightly right in the group of 3
                positionOffset = whiteKeyWidth * 0.88;
            }
            
            const leftPosition = (whiteKeysBefore * whiteKeyWidth) + positionOffset;
            
            html += `<div class="black-key ${isMapped ? 'mapped' : ''}" style="left: ${leftPosition}px; pointer-events: none; opacity: 0.5;" title="Black keys disabled for now">
                <span class="key-label">${noteName}</span>
            </div>`;
        }
    }
    
    html += '</div>';
    html += '<div class="octave-label">Complete 88-key keyboard • Middle C (C4, note 60) highlighted in red</div>';
    html += '</div>';
    container.innerHTML = html;
}

function openKeyPicker(index, productId, productName, imageId) {
    currentProductIndex = index;
    currentProductId = productId;
    currentProductName = productName;
    currentImageId = imageId || '';
    
    // Load mapped keys and then show modal
    loadMappedKeys().then(() => {
        initPianoKeys();
        document.getElementById('keyPickerModal').style.display = 'flex';
        
        // Enable keyboard listening
        enableKeyboardListener();
    });
}

function closeKeyPicker() {
    document.getElementById('keyPickerModal').style.display = 'none';
    
    // Disable keyboard listening
    disableKeyboardListener();
}

// MIDI note mapping for keyboard keys
const keyToMidiMap = {
    // White keys - bottom row (C to B)
    'z': 48,  // C3
    'x': 50,  // D3
    'c': 52,  // E3
    'v': 53,  // F3
    'b': 55,  // G3
    'n': 57,  // A3
    'm': 59,  // B3
    ',': 60,  // C4 (Middle C)
    '.': 62,  // D4
    '/': 64,  // E4
    
    // White keys - middle row (C to B, one octave higher)
    'a': 60,  // C4 (Middle C)
    's': 62,  // D4
    'd': 64,  // E4
    'f': 65,  // F4
    'g': 67,  // G4
    'h': 69,  // A4
    'j': 71,  // B4
    'k': 72,  // C5
    'l': 74,  // D5
    ';': 76,  // E5
    
    // White keys - top row (C to B, two octaves higher)
    'q': 72,  // C5
    'w': 74,  // D5
    'e': 76,  // E5
    'r': 77,  // F5
    't': 79,  // G5
    'y': 81,  // A5
    'u': 83,  // B5
    'i': 84,  // C6
    'o': 86,  // D6
    'p': 88,  // E6
    
    // Black keys - numbers row
    '2': 49,  // C#3
    '3': 51,  // D#3
    '5': 54,  // F#3
    '6': 56,  // G#3
    '7': 58,  // A#3
    '9': 61,  // C#4
    '0': 63,  // D#4
};

let keyboardListenerActive = false;
let keyboardHandler = null;

function enableKeyboardListener() {
    if (keyboardListenerActive) return;
    
    keyboardHandler = function(event) {
        // Ignore if typing in an input field
        if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
            return;
        }
        
        const key = event.key.toLowerCase();
        const midiNote = keyToMidiMap[key];
        
        if (midiNote) {
            event.preventDefault();
            console.log('Keyboard press:', key, '→ MIDI note:', midiNote);
            
            // Highlight the key briefly
            const keyElement = document.querySelector(`.white-key[data-note="${midiNote}"]`);
            if (keyElement) {
                keyElement.style.background = '#ffd700';
                setTimeout(() => {
                    keyElement.style.background = '';
                }, 200);
            }
            
            // Select the key
            selectKey(midiNote);
        }
    };
    
    document.addEventListener('keydown', keyboardHandler);
    keyboardListenerActive = true;
    console.log('Keyboard listener enabled - press keys to select piano notes');
}

function disableKeyboardListener() {
    if (keyboardHandler) {
        document.removeEventListener('keydown', keyboardHandler);
        keyboardHandler = null;
    }
    keyboardListenerActive = false;
}

function closePrintOverlay() {
    document.getElementById('printOverlayModal').style.display = 'none';
}

async function viewCart() {
    const modal = document.getElementById('cartModal');
    const content = document.getElementById('cartContent');
    modal.style.display = 'flex';
    content.innerHTML = '<p style="text-align: center; color: #666;">Loading cart...</p>';
    
    try {
        const response = await fetch('/api/cart');
        if (!response.ok) throw new Error('Failed to load cart');
        
        const cart = await response.json();
        
        if (!cart.items || cart.items.length === 0) {
            content.innerHTML = '<p style="text-align: center; color: #999; padding: 40px;">🛒 Your cart is empty</p>';
            return;
        }
        
        let html = '<div style="display: flex; flex-direction: column; gap: 10px;">';
        
        for (const orderLine of cart.items) {
            if (orderLine.items) {
                for (const article of orderLine.items) {
                    console.log('Cart article:', article.name, 'image_ids:', article.image_ids);
                    html += '<div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px; display: flex; align-items: center; gap: 15px;">';
                    
                    // Product image - check image_ids array first, then decorators
                    let imageId = null;
                    if (article.image_ids && article.image_ids.length > 0) {
                        imageId = article.image_ids[0];
                        console.log('Found image_id:', imageId);
                    } else if (article.decorators) {
                        for (const decorator of article.decorators) {
                            if (decorator.type === 'IMAGE' && decorator.image_id) {
                                imageId = decorator.image_id;
                                console.log('Found image_id in decorator:', imageId);
                                break;
                            }
                        }
                    }
                    
                    if (imageId) {
                        const imgUrl = 'https://storefront-prod.nl.picnicinternational.com/static/images/' + imageId + '/small.png';
                        console.log('Image URL:', imgUrl);
                        html += '<img src="' + imgUrl + '" alt="' + article.name + '" style="width: 60px; height: 60px; object-fit: contain; border: 1px solid #e0e0e0; border-radius: 4px;" onerror="console.error(\'Image failed to load:\', this.src); this.style.display=\'none\';" />';
                    } else {
                        console.log('No image_id found for:', article.name);
                        html += '<div style="width: 60px; height: 60px; background: #f0f0f0; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 24px;">📦</div>';
                    }
                    
                    // Product details
                    html += '<div style="flex: 1;">';
                    html += '<div style="font-weight: bold; color: #333; margin-bottom: 5px;">' + article.name + '</div>';
                    html += '<div style="color: #666; font-size: 0.9em;">Product ID: ' + article.id + '</div>';
                    // Find quantity from decorators
                    let quantity = 1;
                    if (article.decorators) {
                        for (const decorator of article.decorators) {
                            if (decorator.type === 'QUANTITY' && decorator.quantity) {
                                quantity = decorator.quantity;
                                break;
                            }
                        }
                    }
                    html += '<div style="color: #666; font-size: 0.9em;">Quantity: ' + quantity + '</div>';
                    html += '</div>';
                    
                    // Price
                    if (article.unit_price) {
                        const price = (article.unit_price / 100).toFixed(2);
                        html += '<div style="font-weight: bold; color: #2ecc71; font-size: 1.1em; margin-right: 15px;">€' + price + '</div>';
                    }
                    
                    // Assign Piano Key button
                    // Store image_id for later use - ensure we use the imageId from this iteration
                    const buttonImageId = imageId || '';
                    console.log('Creating button with imageId:', buttonImageId, 'for product:', article.name);
                    html += `<button class="assign-key-btn" data-product-id="${article.id}" data-product-name="${btoa(unescape(encodeURIComponent(article.name)))}" data-quantity="${quantity}" data-image-id="${buttonImageId}" style="
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 6px;
                        font-size: 14px;
                        cursor: pointer;
                        white-space: nowrap;
                    ">🎹 Assign Piano Key</button>`;
                    
                    html += '</div>';
                }
            }
        }
        
        html += '</div>';
        
        // Total price
        if (cart.total_price) {
            const total = (cart.total_price / 100).toFixed(2);
            html += '<div style="margin-top: 20px; padding-top: 20px; border-top: 2px solid #333; text-align: right; font-size: 1.3em; font-weight: bold;">Total: €' + total + '</div>';
        }
        
        content.innerHTML = html;
        
        // Add event listeners to assign key buttons
        document.querySelectorAll('.assign-key-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const productId = this.dataset.productId;
                const productName = decodeURIComponent(escape(atob(this.dataset.productName)));
                const quantity = parseInt(this.dataset.quantity);
                const imageId = this.dataset.imageId;
                console.log('Button clicked - data attributes:', {
                    productId,
                    productName,
                    quantity,
                    imageId,
                    rawImageId: this.dataset.imageId
                });
                assignKeyFromCart(productId, productName, quantity, imageId);
            });
        });
        
    } catch (error) {
        console.error('Error loading cart:', error);
        content.innerHTML = '<p style="text-align: center; color: #e74c3c; padding: 40px;">❌ Error loading cart: ' + error.message + '</p>';
    }
}

function closeCart() {
    document.getElementById('cartModal').style.display = 'none';
}

async function viewConfiguredKeys() {
    const modal = document.getElementById('configuredKeysModal');
    const content = document.getElementById('configuredKeysContent');
    modal.style.display = 'flex';
    content.innerHTML = '<p style="text-align: center; color: #666;">Loading configured keys...</p>';
    
    try {
        const response = await fetch('/api/print-data');
        if (!response.ok) throw new Error('Failed to load configured keys');
        
        const data = await response.json();
        const mappings = data.mappings || [];
        
        if (mappings.length === 0) {
            content.innerHTML = '<p style="text-align: center; color: #999; padding: 40px;">🎹 No keys configured yet</p>';
            return;
        }
        
        // Sort by MIDI note number
        mappings.sort((a, b) => a.note - b.note);
        
        let html = '<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px;">';
        
        for (const mapping of mappings) {
            html += '<div style="border: 2px solid #667eea; border-radius: 12px; padding: 15px; background: linear-gradient(to bottom, #ffffff, #f8f9ff); position: relative;">';
            
            // Key info header
            html += '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">';
            html += '<div style="font-weight: bold; color: #667eea; font-size: 1.1em;">🎹 ' + mapping.note_name + ' (MIDI ' + mapping.note + ')</div>';
            html += '<button onclick="deleteMapping(' + mapping.note + ')" style="background: #e74c3c; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: bold;">🗑️ Delete</button>';
            html += '</div>';
            
            // Product image
            if (mapping.image) {
                html += '<div style="text-align: center; margin: 10px 0;">';
                html += '<img src="' + mapping.image + '" alt="' + mapping.product_name + '" style="width: 100px; height: 100px; object-fit: contain; border: 1px solid #e0e0e0; border-radius: 8px; background: white;" />';
                html += '</div>';
            }
            
            // Product details
            html += '<div style="margin-top: 10px;">';
            html += '<div style="font-weight: bold; color: #333; margin-bottom: 5px;">' + mapping.product_name + '</div>';
            html += '<div style="color: #666; font-size: 0.85em;">Product ID: ' + mapping.product_id + '</div>';
            html += '<div style="color: #666; font-size: 0.85em; margin-top: 3px;">Amount: ' + mapping.amount + '</div>';
            html += '</div>';
            
            html += '</div>';
        }
        
        html += '</div>';
        content.innerHTML = html;
        
    } catch (error) {
        console.error('Error loading configured keys:', error);
        content.innerHTML = '<p style="text-align: center; color: #e74c3c; padding: 40px;">❌ Error loading configured keys: ' + error.message + '</p>';
    }
}

function closeConfiguredKeys() {
    document.getElementById('configuredKeysModal').style.display = 'none';
}

let removeMappingData = {};

async function openRemoveMappingMode() {
    const modal = document.getElementById('removeMappingModal');
    const container = document.getElementById('removePianoDisplay');
    modal.style.display = 'flex';
    container.innerHTML = '<p style="text-align: center; color: #666;">Loading mappings...</p>';
    
    try {
        const response = await fetch('/api/print-data');
        if (!response.ok) throw new Error('Failed to load mappings');
        
        const data = await response.json();
        const mappings = data.mappings || [];
        
        // Create a map of note -> mapping
        removeMappingData = {};
        mappings.forEach(m => {
            removeMappingData[m.note] = {
                product_name: m.product_name,
                product_id: m.product_id,
                image: m.image,
                amount: m.amount
            };
        });
        
        // Build piano keyboard - EXACT SAME LAYOUT AS KEY ASSIGNMENT VIEW
        let html = '<div class="piano-container">';
        html += '<div style="text-align: center; color: #999; margin-bottom: 10px;">88 Keys • A0 (21) to C8 (108) • Scroll horizontally → <span style="color: #27ae60;">■ Green = Mapped (click to remove)</span></div>';
        html += '<div class="piano-keys">';
        
        // Render all white keys with equal spacing
        for (let midi = 21; midi <= 108; midi++) {
            const noteIndex = midi % 12;
            const isWhiteKey = [0, 2, 4, 5, 7, 9, 11].includes(noteIndex);
            
            if (isWhiteKey) {
                const octave = Math.floor(midi / 12) - 1;
                const noteName = notes[noteIndex] + octave;
                const isMiddleC = midi === 60;
                const hasMapp = removeMappingData[midi] !== undefined;
                
                let tooltip = `MIDI ${midi} = ${noteName}`;
                if (hasMapp) {
                    const mapping = removeMappingData[midi];
                    tooltip += ` - ${mapping.product_name} (${mapping.amount}) - Click to remove`;
                }
                
                html += `<div class="white-key ${isMiddleC ? 'middle-c' : ''} ${hasMapp ? 'mapped' : ''}" 
                    onclick="removeMappingFromKey(${midi})" 
                    data-note="${midi}" 
                    title="${tooltip}"
                    onmouseenter="showRemoveMappingPreview(${midi}, event)"
                    onmouseleave="hideRemoveMappingPreview()">
                    <span class="key-label">${noteName}</span>
                </div>`;
            }
        }
        
        // Render black keys positioned on top - EXACT SAME AS KEY ASSIGNMENT VIEW
        for (let midi = 21; midi <= 108; midi++) {
            const noteIndex = midi % 12;
            const isBlackKey = [1, 3, 6, 8, 10].includes(noteIndex);
            
            if (isBlackKey) {
                const octave = Math.floor(midi / 12) - 1;
                const noteName = notes[noteIndex] + octave;
                const hasMapp = removeMappingData[midi] !== undefined;
                
                // Calculate which white key this black key comes after
                let whiteKeysBefore = 0;
                for (let note = 21; note <= midi; note++) {
                    const nIdx = note % 12;
                    if ([0, 2, 4, 5, 7, 9, 11].includes(nIdx)) {
                        whiteKeysBefore++;
                    }
                }
                whiteKeysBefore = whiteKeysBefore - 1;
                
                // Position black key based on real piano layout
                const whiteKeyWidth = 42;
                
                let positionOffset;
                if (noteIndex === 1) { // C#
                    positionOffset = whiteKeyWidth * 0.75;
                } else if (noteIndex === 3) { // D#
                    positionOffset = whiteKeyWidth * 0.85;
                } else if (noteIndex === 6) { // F#
                    positionOffset = whiteKeyWidth * 0.72;
                } else if (noteIndex === 8) { // G#
                    positionOffset = whiteKeyWidth * 0.80;
                } else { // A# (10)
                    positionOffset = whiteKeyWidth * 0.88;
                }
                
                const leftPosition = (whiteKeysBefore * whiteKeyWidth) + positionOffset;
                
                let tooltip = `MIDI ${midi} = ${noteName}`;
                if (hasMapp) {
                    const mapping = removeMappingData[midi];
                    tooltip += ` - ${mapping.product_name} (${mapping.amount}) - Click to remove`;
                }
                
                html += `<div class="black-key ${hasMapp ? 'mapped' : ''}" 
                    onclick="removeMappingFromKey(${midi})" 
                    data-note="${midi}" 
                    title="${tooltip}"
                    onmouseenter="showRemoveMappingPreview(${midi}, event)"
                    onmouseleave="hideRemoveMappingPreview()"
                    style="left: ${leftPosition}px;">
                    <span class="key-label">${noteName}</span>
                </div>`;
            }
        }
        
        html += '</div>';
        html += '<div class="octave-label">Complete 88-key keyboard • Middle C (C4, note 60) highlighted in red</div>';
        html += '</div>';
        
        // Add preview tooltip container
        html += '<div id="removeMappingPreview" style="display: none; position: fixed; background: white; border: 2px solid #333; border-radius: 8px; padding: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.3); z-index: 10000; max-width: 250px;"></div>';
        
        container.innerHTML = html;
        
    } catch (error) {
        console.error('Error loading remove mapping mode:', error);
        container.innerHTML = '<p style="text-align: center; color: #e74c3c; padding: 40px;">❌ Error: ' + error.message + '</p>';
    }
}

function showRemoveMappingPreview(midiNote, event) {
    const mapping = removeMappingData[midiNote];
    if (!mapping) return;
    
    const preview = document.getElementById('removeMappingPreview');
    if (!preview) return;
    
    let html = '<div style="text-align: center;">';
    if (mapping.image) {
        html += `<img src="${mapping.image}" style="width: 100px; height: 100px; object-fit: contain; margin-bottom: 8px;" />`;
    }
    html += `<div style="font-weight: bold; margin-bottom: 4px;">${mapping.product_name}</div>`;
    html += `<div style="font-size: 0.9em; color: #666;">Amount: ${mapping.amount}</div>`;
    html += '<div style="margin-top: 8px; color: #e74c3c; font-weight: bold;">Click to remove</div>';
    html += '</div>';
    
    preview.innerHTML = html;
    preview.style.display = 'block';
    preview.style.left = (event.pageX + 15) + 'px';
    preview.style.top = (event.pageY - 50) + 'px';
}

function hideRemoveMappingPreview() {
    const preview = document.getElementById('removeMappingPreview');
    if (preview) {
        preview.style.display = 'none';
    }
}

async function removeMappingFromKey(midiNote) {
    const mapping = removeMappingData[midiNote];
    if (!mapping) return;
    
    if (!confirm(`Remove "${mapping.product_name}" from this key?`)) {
        return;
    }
    
    try {
        const response = await fetch('/api/mapping/' + midiNote, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to delete mapping');
        }
        
        // Reload the remove mapping view
        openRemoveMappingMode();
        
    } catch (error) {
        console.error('Error deleting mapping:', error);
        alert('Error deleting mapping: ' + error.message);
    }
}

function closeRemoveMappingMode() {
    document.getElementById('removeMappingModal').style.display = 'none';
    hideRemoveMappingPreview();
}

async function deleteMapping(midiNote) {
    if (!confirm('Are you sure you want to delete this key mapping?')) {
        return;
    }
    
    try {
        const response = await fetch('/api/mapping/' + midiNote, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to delete mapping');
        }
        
        // Reload the configured keys view
        viewConfiguredKeys();
        
    } catch (error) {
        console.error('Error deleting mapping:', error);
        alert('Error deleting mapping: ' + error.message);
    }
}

function assignKeyFromCart(productId, productName, quantity, imageId) {
    console.log('assignKeyFromCart:', productId, productName, quantity, imageId);
    // Close cart modal and open key picker
    closeCart();
    // Use index -1 to indicate this is from cart (no specific result index)
    openKeyPicker(-1, productId, productName, imageId || '');
    // Store the quantity for saving
    window.currentCartQuantity = quantity;
}

// Generate printable piano overlay
async function openPrintableOverlay() {
    // Open in new window
    const printWindow = window.open('', '_blank', 'width=1200,height=800');
    if (!printWindow) {
        alert('Please allow pop-ups to generate the printable overlay');
        return;
    }
    
    printWindow.document.write('<html><head><title>Piano Overlay - 122cm</title>');
    printWindow.document.write('<style>');
    printWindow.document.write(`
        @page { size: A4 landscape; margin: 10mm; }
        body { margin: 0; padding: 20px; font-family: Arial, sans-serif; }
        .print-page { width: 297mm; height: 210mm; padding: 10mm; box-sizing: border-box; border: 1px solid #ccc; margin-bottom: 20px; background: white; position: relative; overflow: hidden; page-break-after: always; }
        .print-page:last-child { page-break-after: auto; }
        .piano-strip { position: relative; height: 30mm; background: linear-gradient(to bottom, #f5f5f5, #e8e8e8); border: 2px solid #333; }
        .cut-line-top { position: absolute; width: 100%; height: 0; border-top: 2px dashed #ff0000; top: 0; left: 0; z-index: 1; }
        .cut-line-bottom { position: absolute; width: 100%; height: 0; border-top: 2px dashed #ff0000; bottom: 0; left: 0; z-index: 1; }
        .key-marker { position: absolute; width: 1px; height: 100%; border-left: 1px dotted #999; top: 0; z-index: 2; }
        .key-marker-label { position: absolute; bottom: 2px; left: 50%; transform: translateX(-50%); font-size: 6px; color: #666; background: white; padding: 1px 2px; border-radius: 2px; }
        .product-box { position: absolute; display: flex; flex-direction: column; align-items: center; padding: 0.5mm; background: white; border: 1.5px solid #333; border-radius: 2mm; box-shadow: 0 1px 3px rgba(0,0,0,0.2); width: 13mm; top: 2mm; transform: translateX(-50%); z-index: 3; }
        .product-box .product-name { font-size: 6px; color: #333; margin-bottom: 0.3mm; word-wrap: break-word; line-height: 1.0; font-weight: bold; text-align: center; max-height: 4mm; overflow: hidden; }
        .product-box img { width: 12mm; height: 12mm; object-fit: contain; display: block; }
        .connector-line { position: absolute; background: #333; z-index: 2; }
        .connector-vertical { width: 1px; height: 3mm; top: 18mm; }
        .connector-horizontal { height: 1px; top: 21mm; }
        .controls { text-align: center; margin: 20px 0; }
        .controls button { background: #28a745; color: white; border: none; padding: 12px 25px; border-radius: 6px; font-size: 14px; cursor: pointer; margin: 0 5px; }
        @media print {
            body { padding: 0; }
            .controls { display: none; }
            .print-page { border: none; margin: 0; }
        }
    `);
    printWindow.document.write('</style></head><body>');
    printWindow.document.write('<div class="controls"><button onclick="window.print()">🖨️ Print All Pages</button><button onclick="window.close()">Close</button></div>');
    printWindow.document.write('<div id="content"></div></body></html>');
    
    try {
        // Load mappings and product info
        const response = await fetch('/api/print-data');
        if (!response.ok) throw new Error('Failed to load print data');
        
        const data = await response.json();
        const mappings = data.mappings || [];
        
        // Create a map of note -> mapping for quick lookup
        const mappingsByNote = {};
        mappings.forEach(m => {
            mappingsByNote[m.note] = m;
        });
        
        const totalWidth = 1220; // mm (122cm)
        const pageWidth = 277; // mm usable width per A4 page
        const numPages = Math.ceil(totalWidth / pageWidth);
        
        let htmlContent = '';
        
        for (let pageNum = 0; pageNum < numPages; pageNum++) {
            const pageStartMm = pageNum * pageWidth;
            const pageEndMm = Math.min(pageStartMm + pageWidth, totalWidth);
            
            htmlContent += '<div class="print-page">';
            htmlContent += '<div style="text-align: center; font-size: 10px; margin-bottom: 3px; color: #666;">';
            htmlContent += 'Page ' + (pageNum + 1) + ' of ' + numPages + ' • ' + pageStartMm + 'mm - ' + pageEndMm + 'mm';
            htmlContent += '</div>';
            
            // Collect products for this page
            const productsOnPage = [];
            const keyPositionsOnPage = [];
            
            for (let midiNote = 21; midiNote <= 108; midiNote++) {
                const keyPositionMm = getKeyPositionMm(midiNote);
                if (keyPositionMm === null) continue;
                
                if (keyPositionMm >= pageStartMm && keyPositionMm < pageEndMm) {
                    const mapping = mappingsByNote[midiNote];
                    if (mapping && mapping.image) {
                        const relativePos = keyPositionMm - pageStartMm;
                        const positionPercent = (relativePos / pageWidth) * 100;
                        
                        productsOnPage.push({
                            note: midiNote,
                            name: mapping.product_name,
                            image: mapping.image,
                            keyPositionPercent: positionPercent
                        });
                    }
                    
                    // Store all key positions for markers
                    const relativePos = keyPositionMm - pageStartMm;
                    const positionPercent = (relativePos / pageWidth) * 100;
                    const notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
                    const octave = Math.floor(midiNote / 12) - 1;
                    const noteIndex = midiNote % 12;
                    const noteName = notes[noteIndex] + octave;
                    
                    keyPositionsOnPage.push({
                        note: midiNote,
                        noteName: noteName,
                        positionPercent: positionPercent
                    });
                }
            }
            
            // Piano strip with products and key markers inside the 30mm strip
            htmlContent += '<div class="piano-strip">';
            htmlContent += '<div class="cut-line-top"></div>';
            htmlContent += '<div class="cut-line-bottom"></div>';
            
            // Add products positioned at their keys INSIDE the strip
            productsOnPage.forEach(product => {
                const escapedName = product.name.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
                let shortName = product.name;
                const words = shortName.split(' ');
                if (words.length > 3) {
                    shortName = words.slice(0, 3).join(' ');
                } else if (shortName.length > 20) {
                    shortName = shortName.substring(0, 17) + '...';
                }
                const escapedShortName = shortName.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
                
                htmlContent += '<div class="product-box" style="left: ' + product.keyPositionPercent + '%;">';
                htmlContent += '<div class="product-name">' + escapedShortName + '</div>';
                htmlContent += '<img src="' + product.image + '" alt="' + escapedName + '" title="' + escapedName + '">';
                htmlContent += '</div>';
                
                // Add L-shaped connector: vertical line down from box, then horizontal to key
                htmlContent += '<div class="connector-line connector-vertical" style="left: ' + product.keyPositionPercent + '%;"></div>';
                
                // Horizontal line from box position to key position
                const boxPercent = product.keyPositionPercent;
                const keyPercent = product.keyPositionPercent;
                const minPercent = Math.min(boxPercent, keyPercent);
                const lineWidth = Math.abs(boxPercent - keyPercent);
                htmlContent += '<div class="connector-line connector-horizontal" style="left: ' + minPercent + '%; width: ' + lineWidth + '%;"></div>';
            });
            
            // Add key markers
            keyPositionsOnPage.forEach(key => {
                htmlContent += '<div class="key-marker" style="left: ' + key.positionPercent + '%;">';
                htmlContent += '<span class="key-marker-label">' + key.noteName + '</span>';
                htmlContent += '</div>';
            });
            
            htmlContent += '</div></div>';
        }
        
        printWindow.document.getElementById('content').innerHTML = htmlContent;
        
    } catch (error) {
        printWindow.document.write('<div style="padding: 20px; color: red;">Error: ' + error.message + '</div>');
    }
}

// Calculate key position in mm based on MIDI note number
function getKeyPositionMm(midiNote) {
    // Check if this is a white key
    const noteInOctave = (midiNote - 12) % 12;
    const whiteNotesInOctave = [0, 2, 4, 5, 7, 9, 11]; // C D E F G A B
    
    if (!whiteNotesInOctave.includes(noteInOctave)) {
        return null; // Skip black keys
    }
    
    // Start at 11.75mm from left (center of A0 key)
    let position = 11.75;
    
    // Calculate by adding spacing between each consecutive white key
    for (let note = 21; note < midiNote; note++) {
        const currentNoteType = (note - 12) % 12;
        
        // Only process if CURRENT note is white (we're moving FROM this key)
        if (whiteNotesInOctave.includes(currentNoteType)) {
            // Find the next white key
            let nextWhiteNote = note + 1;
            while (!whiteNotesInOctave.includes((nextWhiteNote - 12) % 12)) {
                nextWhiteNote++;
            }
            
            const nextWhiteNoteType = (nextWhiteNote - 12) % 12;
            
            // Check if there's a black key between current and next white key
            // E (4) → F (5): no black key between, use TIGHT spacing
            // B (11) → C (0): no black key between, use TIGHT spacing
            // All others: black key between, use REGULAR spacing
            if ((currentNoteType === 4 && nextWhiteNoteType === 5) ||   // E → F
                (currentNoteType === 11 && nextWhiteNoteType === 0)) {  // B → C
                position += 13.0;  // Tight spacing (measured: 13mm)
            } else {
                position += 23.5;  // Regular spacing (measured: ~23-30mm avg)
            }
        }
    }
    
    return position;
}

function selectKey(noteNumber) {
    console.log('selectKey called with noteNumber:', noteNumber, 'type:', typeof noteNumber);
    
    // Calculate note name for debugging
    const noteIndex = noteNumber % 12;
    const octave = Math.floor(noteNumber / 12) - 1;
    const noteName = notes[noteIndex] + octave;
    console.log('This corresponds to:', noteName, '(MIDI', noteNumber + ')');
    
    closeKeyPicker();
    
    // If this is from a search result (index >= 0), update the input field
    if (currentProductIndex !== null && currentProductIndex !== undefined && currentProductIndex >= 0) {
        const noteInput = document.getElementById('note_' + currentProductIndex);
        if (noteInput) {
            noteInput.value = noteNumber;
        }
    }
    
    // Auto-save with confirmation
    if (confirm(`Assign "${currentProductName}" to piano key ${noteName} (MIDI ${noteNumber})?`)) {
        // For cart items, use the stored quantity
        const amount = window.currentCartQuantity || 1;
        const doubleTap = true; // Default to true for safety
        
        console.log('About to save:', {
            noteNumber,
            currentProductId,
            currentProductName,
            amount,
            doubleTap,
            currentImageId
        });
        
        saveToConfigDirect(noteNumber, currentProductId, currentProductName, amount, doubleTap, currentImageId);
    } else {
        console.log('User cancelled assignment');
    }
}

// Direct save function that doesn't rely on DOM elements
async function saveToConfigDirect(noteNumber, productId, productName, amount, doubleTap, imageId) {
    console.log('saveToConfigDirect called with:', {
        noteNumber,
        productId,
        productName,
        amount,
        doubleTap,
        imageId
    });
    
    try {
        const payload = {
            note: noteNumber,
            product_id: productId,
            product_name: productName,
            amount: amount,
            double_tap: doubleTap,
            image_id: imageId || ''
        };
        
        console.log('Sending payload:', payload);
        
        const response = await fetch('/api/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            alert('✓ Saved successfully!\n\n' + result.message);
            // Reload mapped keys
            await loadMappedKeys();
            // Clear cart quantity
            window.currentCartQuantity = undefined;
        } else {
            alert('❌ Error: ' + result.message);
        }
    } catch (error) {
        alert('❌ Network error: ' + error.message);
    }
}

// Close modal on background click
window.addEventListener('load', function() {
    loadMappedKeys();
    
    // Setup modal background click listener
    const keyPickerModal = document.getElementById('keyPickerModal');
    if (keyPickerModal) {
        keyPickerModal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeKeyPicker();
            }
        });
    }
    
    const cartModal = document.getElementById('cartModal');
    if (cartModal) {
        cartModal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeCart();
            }
        });
    }
});

document.getElementById('searchInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        searchProduct();
    }
});

async function searchProduct() {
    const query = document.getElementById('searchInput').value.trim();
    if (!query) return;

    const loading = document.getElementById('loading');
    const results = document.getElementById('results');

    loading.classList.add('show');
    results.classList.remove('show');
    results.innerHTML = '';

    try {
        const response = await fetch('/api/search?q=' + encodeURIComponent(query));
        const data = await response.json();

        loading.classList.remove('show');

        if (data.error) {
            results.innerHTML = '<div class="no-results">❌ Error: ' + data.error + '</div>';
            results.classList.add('show');
            return;
        }

        if (data.results.length === 0) {
            results.innerHTML = '<div class="no-results">No products found for "' + query + '"</div>';
            results.classList.add('show');
            return;
        }

        let html = '<h2 style="margin-bottom: 20px; color: #333;">Found ' + data.results.length + ' result(s):</h2>';

        data.results.forEach((item, index) => {
            console.log('Item:', item.name, 'image_url:', item.image_url, 'image_id:', item.image_id);
            
            // For display, use plain text (browser will handle it)
            const displayName = item.name;
            // For data attributes, encode to base64 to avoid escaping issues
            const encodedName = btoa(unescape(encodeURIComponent(item.name)));
            const encodedImageId = btoa(item.image_id || '');
            
            const imageHtml = item.image_url ? `<img src="${item.image_url}" alt="${displayName}" style="width: 80px; height: 80px; object-fit: contain; border-radius: 8px; margin-bottom: 10px;">` : '';
            
            html += `
                <div class="result-item">
                    ${imageHtml}
                    <h3>${displayName}</h3>
                    <div class="product-id">ID: ${item.id}</div>
                    <div class="price">€${item.price} ${item.unit}</div>
                    <div style="margin-top: 15px;">
                        <label style="display: block; margin-bottom: 8px; font-weight: bold; color: #333;">
                            🎹 Keyboard Key (MIDI note number):
                        </label>
                        <div style="display: flex; gap: 10px; align-items: center;">
                            <input type="number" id="note_${index}" min="21" max="108" value="${60 + index}" 
                                   style="padding: 10px; border: 2px solid #e0e0e0; border-radius: 6px; width: 100px; font-size: 16px;">
                            <button class="pick-key-btn" data-index="${index}" data-product-id="${item.id}" data-product-name="${encodedName}" data-image-id="${encodedImageId}"
                                    style="padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 14px;">
                                🎹 Pick Key
                            </button>
                            <span style="color: #666; font-size: 0.9em;">Middle C = 60</span>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                            <input type="checkbox" id="double_tap_${index}" checked style="width: 18px; height: 18px; cursor: pointer;">
                            <span style="color: #333; font-weight: 500;">🔁 Require double-tap confirmation</span>
                        </label>
                        <span style="color: #666; font-size: 0.85em; margin-left: 26px;">Prevents accidental additions</span>
                    </div>
                    <button class="copy-btn save-btn" data-index="${index}" data-product-id="${item.id}" data-product-name="${encodedName}" data-image-id="${encodedImageId}">💾 Save to Config</button>
                </div>
            `;
        });

        results.innerHTML = html;
        results.classList.add('show');
        
        // Add event listeners for the buttons
        document.querySelectorAll('.pick-key-btn').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                const index = parseInt(this.dataset.index);
                const productId = this.dataset.productId;
                // Decode base64 product name
                const productName = decodeURIComponent(escape(atob(this.dataset.productName)));
                const imageId = this.dataset.imageId ? atob(this.dataset.imageId) : '';
                openKeyPicker(index, productId, productName, imageId);
            });
        });
        
        document.querySelectorAll('.save-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const index = parseInt(this.dataset.index);
                const productId = this.dataset.productId;
                // Decode base64 product name
                const productName = decodeURIComponent(escape(atob(this.dataset.productName)));
                const imageId = this.dataset.imageId ? atob(this.dataset.imageId) : '';
                saveToConfig(this, index, productId, productName, imageId);
            });
        });
    } catch (error) {
        loading.classList.remove('show');
        results.innerHTML = '<div class="no-results">❌ Error: ' + error.message + '</div>';
        results.classList.add('show');
    }
}

// Helper function to check if a MIDI note is a white key
function isWhiteKey(midiNote) {
    const noteInOctave = (midiNote - 12) % 12;
    const whiteNotesInOctave = [0, 2, 4, 5, 7, 9, 11]; // C D E F G A B
    return whiteNotesInOctave.includes(noteInOctave);
}

async function saveToConfig(button, index, productId, productName, imageId) {
    const noteInput = document.getElementById('note_' + index);
    const doubleTapCheckbox = document.getElementById('double_tap_' + index);
    const noteNumber = parseInt(noteInput.value);
    
    if (isNaN(noteNumber) || noteNumber < 21 || noteNumber > 108) {
        alert('Please enter a valid MIDI note number (21-108)');
        return;
    }
    
    if (!isWhiteKey(noteNumber)) {
        alert('⚠️ Black keys are disabled. Please select a white key only.\n\nWhite keys: C, D, E, F, G, A, B');
        return;
    }
    
    button.disabled = true;
    const originalText = button.textContent;
    button.textContent = '💾 Saving...';
    
    try {
        const response = await fetch('/api/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                note: noteNumber,
                product_id: productId,
                product_name: productName,
                amount: 1,
                double_tap: doubleTapCheckbox.checked,
                image_id: imageId || ''
            })
        });
        
        const result = await response.json();
        
        if (result.error) {
            alert('Error: ' + result.error);
            button.textContent = originalText;
        } else {
            button.textContent = '✓ Saved!';
            button.classList.add('copied');
            button.style.background = '#28a745';
            
            // Reload mapped keys after successful save
            loadMappedKeys();
            
            setTimeout(() => {
                button.textContent = originalText;
                button.classList.remove('copied');
                button.style.background = '';
            }, 3000);
        }
    } catch (error) {
        alert('Error: ' + error.message);
        button.textContent = originalText;
    } finally {
        button.disabled = false;
    }
}
