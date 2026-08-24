#!/usr/bin/env python3
"""
Generate visual keyboard layouts from ZMK keymap files.
Outputs SVG diagrams for each layer showing all key bindings.
"""

import re
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Key name mappings for display
KEY_DISPLAY_NAMES = {
    # Letters
    'kp Q': 'Q', 'kp W': 'W', 'kp E': 'E', 'kp R': 'R', 'kp T': 'T',
    'kp Y': 'Y', 'kp U': 'U', 'kp I': 'I', 'kp O': 'O', 'kp P': 'P',
    'kp A': 'A', 'kp S': 'S', 'kp D': 'D', 'kp F': 'F', 'kp G': 'G',
    'kp H': 'H', 'kp J': 'J', 'kp K': 'K', 'kp L': 'L', 'kp SQT': "'",
    'kp Z': 'Z', 'kp X': 'X', 'kp C': 'C', 'kp V': 'V', 'kp B': 'B',
    'kp N': 'N', 'kp M': 'M', 'kp COMMA': ',', 'kp DOT': '.', 'kp SLASH': '/',
    
    # Numbers
    'kp N0': '0', 'kp N1': '1', 'kp N2': '2', 'kp N3': '3', 'kp N4': '4',
    'kp N5': '5', 'kp N6': '6', 'kp N7': '7', 'kp N8': '8', 'kp N9': '9',
    
    # Modifiers
    'kp LCTRL': 'Ctrl', 'kp LSHIFT': 'Shift', 'kp LALT': 'Alt', 'kp LGUI': 'Gui',
    'kp LSHFT': 'Shift', 'kp RALT': 'RAlt',
    
    # Special Keys
    'kp SPACE': 'Space', 'kp TAB': 'Tab', 'kp RET': 'Enter', 'kp BSPC': 'Bksp',
    'kp DEL': 'Del', 'kp ESC': 'Esc', 'kp ENTER': 'Enter',
    'kp LEFT': '←', 'kp RIGHT': '→', 'kp UP': '↑', 'kp DOWN': '↓',
    'kp HOME': 'Home', 'kp END': 'End', 'kp PG_UP': 'PgUp', 'kp PG_DN': 'PgDn',
    'kp INS': 'Ins', 'kp CAPS': 'Caps',
    
    # Symbols
    'kp LBKT': '[', 'kp RBKT': ']', 'kp LBRC': '{', 'kp RBRC': '}',
    'kp SEMI': ';', 'kp COLON': ':', 'kp EQUAL': '=', 'kp PLUS': '+',
    'kp MINUS': '-', 'kp UNDER': '_', 'kp BSLH': '\\', 'kp PIPE': '|',
    'kp GRAVE': '`', 'kp TILDE': '~', 'kp AMPS': '&', 'kp ASTRK': '*',
    'kp LPAR': '(', 'kp RPAR': ')', 'kp DLLR': '$', 'kp PRCNT': '%',
    'kp CARET': '^', 'kp EXCL': '!', 'kp AT': '@', 'kp HASH': '#',
    
    # Function Keys
    'kp F1': 'F1', 'kp F2': 'F2', 'kp F3': 'F3', 'kp F4': 'F4', 'kp F5': 'F5',
    'kp F6': 'F6', 'kp F7': 'F7', 'kp F8': 'F8', 'kp F9': 'F9', 'kp F10': 'F10',
    'kp F11': 'F11', 'kp F12': 'F12',
    
    # Media
    'kp C_PLAY': '▶', 'kp C_PAUSE': '⏸', 'kp C_PP': '⏯', 'kp C_STOP': '⏹',
    'kp C_NEXT': 'Next', 'kp C_PREV': 'Prev', 'kp C_VOL_UP': 'Vol↑', 'kp C_VOL_DN': 'Vol↓',
    'kp C_MUTE': 'Mute',
    
    # Special markers
    'none': '∅', '&none': '∅', 'U_UND': 'Undo', 'U_CUT': 'Cut', 'U_CPY': 'Copy',
    'U_PST': 'Paste', 'U_RDO': 'Redo', 'U_BTN1': 'MB1', 'U_BTN2': 'MB2', 'U_BTN3': 'MB3',
    'U_MS_U': 'M↑', 'U_MS_D': 'M↓', 'U_MS_L': 'M←', 'U_MS_R': 'M→',
    'U_WH_U': 'W↑', 'U_WH_D': 'W↓', 'U_WH_L': 'W←', 'U_WH_R': 'W→',
    
    # Layers
    '&tog GAME': 'Game↔', '&bootloader': 'Boot',
    
    # Other
    'kp PSCRN': 'PrtSc', 'kp SLCK': 'SLck', 'kp PAUSE_BREAK': 'Pause',
    'kp K_APP': 'Menu',
    
    # Mod-tap (simplified to show modifier)
    '&u_mt LGUI': 'G/…', '&u_mt LALT': 'A/…', '&u_mt LCTRL': 'C/…', '&u_mt LSHFT': 'S/…',
    '&u_mt RALT': 'RA/…',
    
    # Layer-tap (simplified to show base key)
    '&u_lt BUTTON': 'Btn/…', '&u_lt MEDIA': 'Med/…', '&u_lt NAV': 'Nav/…',
    '&u_lt MOUSE': 'Mou/…', '&u_lt SYM': 'Sym/…', '&u_lt NUM': 'Num/…',
    '&u_lt FUN': 'Fun/…',
}

# Corne keyboard layout (42 keys, 6 columns each hand)
# Position indices: 0-11 (top row), 12-23 (home row), 24-35 (bottom row), 36-41 (thumbs)
CORNE_LAYOUT = [
    # Top row (6 keys per hand)
    [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0),  # Left
     (7, 0), (8, 0), (9, 0), (10, 0), (11, 0), (12, 0)],  # Right
    # Home row
    [(0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1),  # Left
     (7, 1), (8, 1), (9, 1), (10, 1), (11, 1), (12, 1)],  # Right
    # Bottom row
    [(0, 2), (1, 2), (2, 2), (3, 2), (4, 2), (5, 2),  # Left
     (7, 2), (8, 2), (9, 2), (10, 2), (11, 2), (12, 2)],  # Right
    # Thumb cluster
    [(2, 3), (3, 3), (4, 3),  # Left
     (8, 3), (9, 3), (10, 3)],  # Right
]

def simplify_key_name(key: str) -> str:
    """Convert complex key binding to display name."""
    key = key.strip().rstrip(',;')
    
    # Direct lookup
    if key in KEY_DISPLAY_NAMES:
        return KEY_DISPLAY_NAMES[key]
    
    # Partial matching for mod-taps and layer-taps
    for pattern, display in KEY_DISPLAY_NAMES.items():
        if pattern in key:
            return display
    
    # Extract just the key part if it's a kp command
    if '&kp ' in key:
        parts = key.replace('&kp ', '').split()
        return parts[0] if parts else key
    
    # Fallback: return shortened version
    if len(key) > 12:
        return key[:10] + '…'
    return key

def parse_keymap_file(filepath: str) -> Dict[str, List[str]]:
    """Parse ZMK keymap file and extract layer definitions."""
    layers = {}
    current_layer = None
    bindings = []
    in_bindings = False
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Find layer definitions
    layer_pattern = r'(\w+)\s*{\s*display-name\s*=\s*["\']([^"\']+)["\'];'
    for match in re.finditer(layer_pattern, content):
        layer_name = match.group(1)
        display_name = match.group(2)
        
        # Extract bindings for this layer
        start = match.end()
        # Find the matching closing brace
        brace_count = 0
        end = start
        for i, char in enumerate(content[start:]):
            if char == '{':
                brace_count += 1
            elif char == '}':
                if brace_count == 0:
                    end = start + i
                    break
                brace_count -= 1
        
        layer_content = content[start:end]
        
        # Extract bindings line
        bindings_match = re.search(r'bindings\s*=\s*<([^>]+)>', layer_content, re.DOTALL)
        if bindings_match:
            bindings_text = bindings_match.group(1)
            # Split by whitespace but keep multi-word keys together
            keys = re.findall(r'[\w&_\[\]\(\)\.]+|[^\s&\[\]()\.]+', bindings_text)
            keys = [k.strip() for k in keys if k.strip()]
            layers[layer_name] = {
                'display_name': display_name,
                'keys': keys
            }
    
    return layers

def create_svg_layout(layer_name: str, display_name: str, keys: List[str]) -> str:
    """Create SVG visualization of a keyboard layer."""
    # Use first 42 keys (Corne layout)
    keys = keys[:42]
    while len(keys) < 42:
        keys.append('&none')
    
    key_width = 40
    key_height = 40
    gap = 5
    left_margin = 20
    top_margin = 20
    
    # Generate SVG
    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="300">',
        '<style>',
        '.key { fill: #e8e8e8; stroke: #333; stroke-width: 1; }',
        '.key-text { font-family: monospace; font-size: 10px; text-anchor: middle; dominant-baseline: middle; }',
        '.layer-title { font-family: sans-serif; font-size: 18px; font-weight: bold; }',
        '</style>',
        f'<text class="layer-title" x="10" y="20">{display_name}</text>',
    ]
    
    # Draw keys in grid layout
    key_index = 0
    for row_idx, row in enumerate(CORNE_LAYOUT):
        for col_idx, (x_grid, y_grid) in enumerate(row):
            if key_index >= len(keys):
                break
            
            key = keys[key_index]
            display = simplify_key_name(key)
            
            x = left_margin + x_grid * (key_width + gap)
            y = top_margin + 40 + y_grid * (key_height + gap)
            
            # Color coding for different key types
            fill_color = '#e8e8e8'
            if '&none' in key or 'none' == key:
                fill_color = '#f0f0f0'
            elif any(x in key for x in ['SHIFT', 'CTRL', 'ALT', 'GUI', 'LSHFT']):
                fill_color = '#ffcccc'
            elif any(x in key for x in ['&u_lt', 'layer']):
                fill_color = '#ccddff'
            
            svg_lines.append(f'<rect class="key" x="{x}" y="{y}" width="{key_width}" height="{key_height}" fill="{fill_color}"/>')
            
            # Wrap text if too long
            if len(display) > 8:
                parts = display.split('/')
                for i, part in enumerate(parts[:2]):
                    text_y = y + 12 + (i - 0.5) * 12
                    svg_lines.append(f'<text class="key-text" x="{x + key_width//2}" y="{text_y}">{part}</text>')
            else:
                svg_lines.append(f'<text class="key-text" x="{x + key_width//2}" y="{y + key_height//2}">{display}</text>')
            
            key_index += 1
    
    svg_lines.append('</svg>')
    return '\n'.join(svg_lines)

def main():
    keymap_file = 'config/corne_custom.keymap'
    output_dir = 'keymap_layouts'
    
    if not os.path.exists(keymap_file):
        print(f"Error: {keymap_file} not found")
        sys.exit(1)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Parse keymap
    print(f"Parsing {keymap_file}...")
    layers = parse_keymap_file(keymap_file)
    
    if not layers:
        print("No layers found in keymap file")
        sys.exit(1)
    
    print(f"Found {len(layers)} layers")
    
    # Generate SVG for each layer
    for layer_name, layer_data in layers.items():
        display_name = layer_data['display_name']
        keys = layer_data['keys']
        
        svg_content = create_svg_layout(layer_name, display_name, keys)
        output_file = os.path.join(output_dir, f'{display_name.lower()}.svg')
        
        with open(output_file, 'w') as f:
            f.write(svg_content)
        
        print(f"  Generated {output_file}")
    
    # Create index HTML
    html_content = '''<!DOCTYPE html>
<html>
<head>
    <title>ZMK Keymap Layers</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background: #f5f5f5; }
        h1 { color: #333; }
        .layer { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .layer h2 { margin-top: 0; color: #0066cc; }
        svg { max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px; }
    </style>
</head>
<body>
    <h1>ZMK Corne Custom - Keymap Layers</h1>
    <p>Visual layout of all keyboard layers. Each layer shows key bindings.</p>
'''
    
    for layer_name in sorted(layers.keys(), key=lambda x: layers[x]['display_name']):
        display_name = layers[layer_name]['display_name']
        svg_file = f'{display_name.lower()}.svg'
        html_content += f'''    <div class="layer">
        <h2>{display_name}</h2>
        <img src="{svg_file}" alt="{display_name}">
    </div>
'''
    
    html_content += '''</body>
</html>'''
    
    index_file = os.path.join(output_dir, 'index.html')
    with open(index_file, 'w') as f:
        f.write(html_content)
    print(f"Generated {index_file}")
    
    print("\nDone!")

if __name__ == '__main__':
    main()
