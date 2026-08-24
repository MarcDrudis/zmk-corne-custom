#!/usr/bin/env python3
"""
Render a keyboard-layout PNG straight from config/corne_custom.keymap.

For every layer it draws the 6-column split Corne, and for each layer it also
shows WHAT the layer is for and HOW YOU GET THERE (which Base key reaches it).
Re-run after editing the keymap and the image regenerates from source.

    python3 scripts/generate_keymap_layout.py            # -> keymap-diagram.png
    python3 scripts/generate_keymap_layout.py --keymap X --out Y.png

Only dependency is Pillow (pip install pillow).
"""

import argparse
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# How a raw binding token becomes a legend. (main label, hold label, kind)
# kind drives colour: '' plain, 'mod' hold=modifier, 'lt' hold=layer,
# 'tog' layer switch/toggle, 'boot' bootloader, 'none' unused.
# ---------------------------------------------------------------------------

# Single-token / macro bindings -> (main, hold, kind)
MACROS = {
    "&none": ("", "", "none"),
    "U_UND": ("UNDO", "", ""), "U_CUT": ("CUT", "", ""), "U_CPY": ("COPY", "", ""),
    "U_PST": ("PASTE", "", ""), "U_RDO": ("REDO", "", ""),
    "U_BTN1": ("MB1", "", ""), "U_BTN2": ("MB2", "", ""), "U_BTN3": ("MB3", "", ""),
    "U_MS_L": ("MS←", "", ""), "U_MS_R": ("MS→", "", ""),
    "U_MS_U": ("MS↑", "", ""), "U_MS_D": ("MS↓", "", ""),
    "U_WH_L": ("WH←", "", ""), "U_WH_R": ("WH→", "", ""),
    "U_WH_U": ("WH↑", "", ""), "U_WH_D": ("WH↓", "", ""),
}

# &kp <CODE> -> label
KP = {
    "SQT": "'", "COMMA": ",", "DOT": ".", "SLASH": "/", "SEMI": ";", "COLON": ":",
    "GRAVE": "`", "TILDE": "~", "BSLH": "\\", "PIPE": "|", "MINUS": "−",
    "UNDER": "_", "EQUAL": "=", "PLUS": "+", "LBKT": "[", "RBKT": "]",
    "LBRC": "{", "RBRC": "}", "LPAR": "(", "RPAR": ")", "AMPS": "&", "ASTRK": "*",
    "DLLR": "$", "PRCNT": "%", "CARET": "^", "EXCL": "!", "AT": "@", "HASH": "#",
    "SPACE": "SPC", "RET": "RET", "BSPC": "BSP", "DEL": "DEL", "ESC": "ESC",
    "TAB": "TAB", "CAPS": "CAPS", "INS": "INS", "HOME": "HOME", "END": "END",
    "PG_UP": "PGUP", "PG_DN": "PGDN", "LEFT": "←", "RIGHT": "→",
    "UP": "↑", "DOWN": "↓", "PSCRN": "PSCR", "SLCK": "SLCK",
    "PAUSE_BREAK": "BRK", "K_APP": "APP",
    "C_PREV": "PREV", "C_NEXT": "NEXT", "C_VOL_DN": "VOL−", "C_VOL_UP": "VOL+",
    "C_STOP": "STOP", "C_PP": "PLAY", "C_MUTE": "MUTE",
    "LGUI": "LGUI", "LALT": "LALT", "LCTRL": "LCTRL", "LSHFT": "LSHFT",
    "RALT": "RALT", "N0": "0", "N1": "1", "N2": "2", "N3": "3", "N4": "4",
    "N5": "5", "N6": "6", "N7": "7", "N8": "8", "N9": "9",
}
for _c in "QWERTYUIOPASDFGHJKLZXCVBNM":
    KP[_c] = _c
for _n in range(1, 13):
    KP[f"F{_n}"] = f"F{_n}"

# Home-row mod-tap hold label, per modifier code
MOD_HOLD = {"LGUI": "LGUI", "LALT": "LALT", "LCTRL": "LCTRL", "LSHFT": "RSHFT",
            "RALT": "RALT"}

def kp_label(code):
    return KP.get(code, code)

def render_binding(tok):
    """tok is the whitespace-joined binding, e.g. '&u_mt LGUI A'. -> (main,hold,kind)"""
    tok = tok.strip()
    if tok in MACROS:
        return MACROS[tok]
    parts = tok.split()
    head = parts[0]

    if head == "&kp":
        return (kp_label(parts[1]), "", "")
    if head == "&u_mt":            # mod-tap: tap=key, hold=mod
        mod, key = parts[1], parts[2]
        return (kp_label(key), MOD_HOLD.get(mod, mod), "mod")
    if head == "&u_lt":            # layer-tap: tap=key, hold=layer
        layer, key = parts[1], parts[2]
        return (kp_label(key), layer, "lt")
    if head == "&u_boot":          # guarded bootloader (hold 2s)
        return ("BOOT", "hold 2s", "boot")
    if head == "&bootloader":
        return ("BOOT", "", "boot")
    if head == "&tog":
        return (f"{parts[1]}⇄", "", "tog")
    if head == "&to":
        return (f"→{parts[1]}", "", "tog")
    if head.startswith("&u_to_U_"):
        return ("→" + head[len("&u_to_U_"):], "", "tog")
    if head == "&studio_unlock":
        return ("STUDIO", "unlock", "tog")
    if head == "&u_caps_word":
        return ("CAPS", "", "")
    if head == "&u_out_tog":
        return ("OUT", "", "tog")
    if head.startswith("&u_bt_sel_"):
        return ("BT " + head[-1], "", "tog")
    if head == "&ext_power":
        return ("EXT PW", "", "")
    if head == "&mkp":
        return (parts[1], "", "")
    # Fallback: strip leading & and show it so nothing silently vanishes.
    return (head.lstrip("&")[:6], "", "")

# ---------------------------------------------------------------------------
# What each layer is for. Purpose is editorial; "reach" is DERIVED from Base.
# ---------------------------------------------------------------------------
PURPOSE = {
    "base":   "Letters. Home-row mods GACS (hold A/S/D/F = Gui/Alt/Ctrl/Shift).",
    "game":   "Gaming: left mods off, TAB/SHIFT/CTRL on the outer column, right hand = Base.",
    "button": "Clipboard (undo/cut/copy/paste/redo) + mouse buttons on the thumbs.",
    "nav":    "Arrows (vim h/j/k/l), Home/End/PgUp/PgDn, clipboard, caps-word.",
    "mouse":  "Mouse cursor + wheel; mouse buttons on the thumbs.",
    "media":  "Volume/transport, Bluetooth profiles, output toggle, enter Game.",
    "num":    "Number pad and math symbols on the left hand.",
    "sym":    "Shifted symbols on the left hand.",
    "fun":    "Function keys F1–F12 and system keys.",
}

# ---------------------------------------------------------------------------
# Parse the keymap: layer name -> list of 42 raw binding tokens.
# Also read the layer #define indices and Base thumbs to compute "reach".
# ---------------------------------------------------------------------------
def parse_keymap(path):
    text = Path(path).read_text()

    # layer index defines: "#define NAV 3"
    idx = {}
    for m in re.finditer(r"^#define\s+([A-Z]+)\s+(\d+)\s*$", text, re.M):
        idx[m.group(1)] = int(m.group(2))

    layers = {}
    order = []
    # each layer node:  name { display-name = "X"; ... bindings = < ... >; };
    for m in re.finditer(
        r'(\w+)\s*\{\s*display-name\s*=\s*"([^"]+)";'
        r'.*?bindings\s*=\s*<(.*?)>\s*;',
        text, re.S,
    ):
        name, disp, body = m.group(1), m.group(2), m.group(3)
        # strip /* ... */ comments inside the bindings block
        body = re.sub(r"/\*.*?\*/", " ", body, flags=re.S)
        toks = tokenize(body)
        if len(toks) != 42:
            print(f"  ! {name}: expected 42 bindings, got {len(toks)}", file=sys.stderr)
        layers[name] = {"display": disp, "toks": toks}
        order.append(name)
    return order, layers, idx

def tokenize(body):
    """Split a bindings body into per-key tokens. A token starts at '&' or at a
    bare Miryoku macro (U_UND, U_BTN1, ...) and runs until the next such start,
    grouping args like '&u_mt LGUI A' into one token."""
    words = body.split()
    toks, cur = [], []
    for w in words:
        starts = w.startswith("&") or w in MACROS
        if starts:
            if cur:
                toks.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        toks.append(" ".join(cur))
    return toks

def base_reach(base_toks, idx):
    """From every Base &u_lt binding (thumbs AND home keys like Z/SLASH),
    map layer name -> list of keys that reach it by hold. e.g.
    {'MEDIA': ['ESC'], 'BUTTON': ['Z', '/']}."""
    reach = {}
    for t in base_toks:
        p = t.split()
        if p and p[0] == "&u_lt":
            layer, key = p[1], p[2]
            reach.setdefault(layer, []).append(kp_label(key))
    return reach

# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------
THEME = {
    "bg": (20, 22, 26), "panel": (27, 30, 36),
    "key": (38, 42, 51), "key_edge": (13, 15, 18),
    "none": (32, 35, 42), "none_ink": (74, 78, 86),
    "ink": (231, 230, 225), "soft": (146, 151, 161), "faint": (103, 108, 117),
    "mod": (110, 168, 222), "lt": (79, 199, 184), "tog": (177, 137, 230),
    "accent": (232, 163, 61),
}

def load_font(size, bold=False):
    candidates = [
        "/home/marc/.local/share/fonts/JetBrainsMonoNerd/JetBrainsMonoNerdFontMono-Regular.ttf",
        "/usr/share/fonts/jetbrains-mono-fonts/JetBrainsMono-Regular.ttf",
        "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono.ttf",
        "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()

KEY = 58        # key cell size
GAP = 6
HALF_GAP = 34   # gap between the two hands
PAD = 34        # page padding
HDR = 62        # per-layer header height

def key_color(kind):
    return {
        "mod": THEME["mod"], "lt": THEME["lt"], "tog": THEME["tog"],
        "boot": THEME["accent"],
    }.get(kind)

def draw_key(d, x, y, binding, f_main, f_hold):
    main, hold, kind = binding
    if kind == "none" or (not main and not hold):
        d.rounded_rectangle([x, y, x + KEY, y + KEY], radius=8, fill=THEME["none"])
        d.text((x + KEY / 2, y + KEY / 2), "·", font=f_main,
               fill=THEME["none_ink"], anchor="mm")
        return
    edge = THEME["accent"] if kind == "boot" else THEME["key_edge"]
    fill = THEME["key"]
    if kind == "boot":
        fill = (54, 46, 34)
    d.rounded_rectangle([x, y, x + KEY, y + KEY], radius=8, fill=fill,
                        outline=edge, width=2 if kind == "boot" else 1)
    main_fill = THEME["accent"] if kind == "boot" else THEME["ink"]
    if hold:
        d.text((x + KEY / 2, y + KEY * 0.36), main, font=f_main, fill=main_fill, anchor="mm")
        hc = key_color(kind) or THEME["soft"]
        d.text((x + KEY / 2, y + KEY * 0.72), hold, font=f_hold, fill=hc, anchor="mm")
    else:
        d.text((x + KEY / 2, y + KEY / 2), main, font=f_main, fill=main_fill, anchor="mm")

def board_width():
    return 6 * (KEY + GAP) + HALF_GAP + 6 * (KEY + GAP) - GAP

def draw_layer(d, x0, y0, layer, reach, idx, fonts):
    f_name, f_meta, f_main, f_hold, f_small = fonts
    disp = layer["display"]
    key = disp.lower()

    # header: name + purpose + how to reach
    d.text((x0, y0), disp, font=f_name, fill=THEME["ink"])
    name_h = f_name.getbbox("Ag")[3]
    purpose = PURPOSE.get(key, "")
    if purpose:
        d.text((x0, y0 + name_h + 6), purpose, font=f_meta, fill=THEME["soft"])

    # reach line (right-aligned under header)
    lname = disp.upper()
    keys = reach.get(lname)
    if keys:
        txt = f"reach: hold  {'  or  '.join(keys)}"
    elif key == "base":
        txt = "default layer"
    elif key == "game":
        txt = "reach: double-tap →GAME (next to →BASE on any layer)"
    else:
        txt = ""
    if txt:
        w = d.textlength(txt, font=f_meta)
        d.text((x0 + board_width() - w, y0), txt, font=f_meta, fill=THEME["accent"])

    # keys: rows 0-2 are 12 wide, thumb row is 6 (inner three cols each hand)
    toks = layer["toks"]
    gy = y0 + HDR
    for row in range(3):
        for col in range(12):
            t = toks[row * 12 + col]
            x = x0 + col * (KEY + GAP) + (HALF_GAP if col >= 6 else 0)
            draw_key(d, x, gy, render_binding(t), f_main, f_hold)
        gy += KEY + GAP
    # thumbs: positions 36..41 -> under cols 3,4,5 (left) and 6,7,8 (right)
    thumb_cols = [3, 4, 5, 6, 7, 8]
    for i, col in enumerate(thumb_cols):
        t = toks[36 + i]
        x = x0 + col * (KEY + GAP) + (HALF_GAP if col >= 6 else 0)
        draw_key(d, x, gy, render_binding(t), f_main, f_hold)
    return gy + KEY

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keymap", default="config/corne_custom.keymap")
    ap.add_argument("--out", default="keymap-diagram.png")
    ap.add_argument("--scale", type=int, default=2, help="supersample factor")
    args = ap.parse_args()

    if not Path(args.keymap).exists():
        sys.exit(f"keymap not found: {args.keymap}")

    order, layers, idx = parse_keymap(args.keymap)
    if not layers:
        sys.exit("no layers parsed")
    print(f"parsed {len(layers)} layers: {', '.join(order)}")

    reach = base_reach(layers[order[0]]["toks"], idx) if order else {}

    s = args.scale
    global KEY, GAP, HALF_GAP, PAD, HDR
    KEY, GAP, HALF_GAP, PAD, HDR = (v * s for v in (KEY, GAP, HALF_GAP, PAD, HDR))

    fonts = (load_font(22 * s), load_font(12 * s), load_font(13 * s),
             load_font(8 * s), load_font(10 * s))

    bw = board_width()
    layer_h = HDR + 4 * (KEY + GAP) + 26 * s
    width = bw + 2 * PAD
    top = PAD + 116 * s   # room for title + two caption lines + legend
    height = top + len(order) * layer_h + PAD

    img = Image.new("RGB", (int(width), int(height)), THEME["bg"])
    d = ImageDraw.Draw(img)

    # title
    d.text((PAD, PAD), "Miryoku Keymap  —  6-col Corne", font=load_font(26 * s),
           fill=THEME["ink"])
    d.text((PAD, PAD + 34 * s),
           "Small line under a key = what HOLD does.  Amber = bootloader (hold 2s to flash).",
           font=fonts[1], fill=THEME["soft"])
    d.text((PAD, PAD + 52 * s),
           "→X = double-tap to switch to layer X (a stray single tap does nothing).  "
           "X⇄ = tap to toggle layer X on/off.",
           font=fonts[1], fill=THEME["soft"])
    # legend
    lx, ly = PAD, PAD + 84 * s
    for label, col in [("hold=mod", THEME["mod"]), ("hold=layer", THEME["lt"]),
                       ("layer switch", THEME["tog"]), ("bootloader", THEME["accent"]),
                       ("unused", THEME["none_ink"])]:
        d.rounded_rectangle([lx, ly, lx + 13 * s, ly + 13 * s], radius=3 * s, fill=col)
        d.text((lx + 18 * s, ly + 6 * s), label, font=fonts[4], fill=THEME["soft"],
               anchor="lm")
        lx += int(d.textlength(label, font=fonts[4])) + 44 * s

    y = top
    for name in order:
        y = draw_layer(d, PAD, y, layers[name], reach, idx, fonts) + 26 * s

    img.save(args.out)
    print(f"wrote {args.out}  ({img.width}x{img.height})")

if __name__ == "__main__":
    main()
