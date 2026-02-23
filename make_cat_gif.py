"""
Generate a flying cat GIF using pure Python (no external libraries).
"""
import struct


# ---------------------------------------------------------------------------
# Minimal GIF encoder
# ---------------------------------------------------------------------------

def lzw_compress(data, min_code_size):
    """LZW compression used by GIF."""
    clear_code = 1 << min_code_size
    eoi_code = clear_code + 1

    code_table = {(i,): i for i in range(clear_code)}
    next_code = eoi_code + 1
    code_size = min_code_size + 1

    output_bits = []

    def emit(code):
        b = code
        for _ in range(code_size):
            output_bits.append(b & 1)
            b >>= 1

    emit(clear_code)

    index_stream = list(data)
    if not index_stream:
        emit(eoi_code)
    else:
        buffer = (index_stream[0],)
        for idx in index_stream[1:]:
            extended = buffer + (idx,)
            if extended in code_table:
                buffer = extended
            else:
                emit(code_table[buffer])
                if next_code < 4096:
                    code_table[extended] = next_code
                    next_code += 1
                    if next_code > (1 << code_size) and code_size < 12:
                        code_size += 1
                elif next_code == 4096:
                    emit(clear_code)
                    code_table = {(i,): i for i in range(clear_code)}
                    next_code = eoi_code + 1
                    code_size = min_code_size + 1
                buffer = (idx,)
        emit(code_table[buffer])
        emit(eoi_code)

    # Pack bits into bytes (LSB first)
    result = bytearray()
    for i in range(0, len(output_bits), 8):
        byte = 0
        for j, bit in enumerate(output_bits[i:i+8]):
            byte |= bit << j
        result.append(byte)
    return bytes(result)


def pack_sub_blocks(data):
    """Split data into GIF sub-blocks (<= 255 bytes each)."""
    out = bytearray()
    for i in range(0, len(data), 255):
        chunk = data[i:i+255]
        out.append(len(chunk))
        out.extend(chunk)
    out.append(0)  # block terminator
    return bytes(out)


def build_gif(frames, width, height, palette, delay_cs=6, loop=0):
    """
    frames   : list of bytearrays, each width*height palette indices
    palette  : list of (r,g,b) tuples, length must be power of 2
    delay_cs : frame delay in centiseconds
    loop     : 0 = infinite loop
    """
    palette_size = len(palette)
    assert palette_size & (palette_size - 1) == 0, "palette size must be power of 2"
    color_table_flag = 1
    color_res = 7  # 8-bit colour resolution field (informational)
    size_field = {2: 0, 4: 1, 8: 2, 16: 3, 32: 4, 64: 5, 128: 6, 256: 7}[palette_size]
    packed_byte = (color_table_flag << 7) | (color_res << 4) | size_field

    out = bytearray()

    # --- Header ---
    out += b'GIF89a'

    # --- Logical Screen Descriptor ---
    out += struct.pack('<HHBBB', width, height, packed_byte, 0, 0)

    # --- Global Color Table ---
    for r, g, b in palette:
        out += bytes([r, g, b])

    # --- Netscape loop extension ---
    out += b'\x21\xFF\x0B'
    out += b'NETSCAPE2.0'
    out += b'\x03\x01'
    out += struct.pack('<H', loop)
    out += b'\x00'

    min_code_size = max(2, size_field + 1)

    for frame_data in frames:
        # Graphic Control Extension (with delay)
        out += b'\x21\xF9\x04'
        out += struct.pack('<BHB', 0, delay_cs, 0)
        out += b'\x00'

        # Image Descriptor
        out += b'\x2C'
        out += struct.pack('<HHHHB', 0, 0, width, height, 0)

        # Image Data
        compressed = lzw_compress(frame_data, min_code_size)
        out += bytes([min_code_size])
        out += pack_sub_blocks(compressed)

    # Trailer
    out += b'\x3B'
    return bytes(out)


# ---------------------------------------------------------------------------
# Cat sprite (16x16 pixel art) - two wing positions for flapping
# ---------------------------------------------------------------------------
# Colour palette indices
# 0 = transparent/sky blue
# 1 = dark outline
# 2 = orange body
# 3 = light orange / belly
# 4 = pink inner ear / nose
# 5 = white eye / whisker
# 6 = yellow stars
# 7 = sky gradient 1
# 8 = sky gradient 2

PALETTE = [
    (135, 206, 235),  # 0  sky blue
    ( 30,  20,  10),  # 1  dark outline
    (230, 140,  40),  # 2  orange body
    (255, 200, 120),  # 3  light orange
    (255, 160, 160),  # 4  pink
    (255, 255, 255),  # 5  white
    (255, 230,  50),  # 6  yellow star
    (160, 210, 240),  # 7  sky light
    (100, 180, 220),  # 8  sky dark
]
# Pad to 16
while len(PALETTE) < 16:
    PALETTE.append((0, 0, 0))

_ = 0   # sky / transparent
O = 1   # outline
C = 2   # orange cat
L = 3   # light orange
P = 4   # pink
W = 5   # white
S = 6   # star yellow
A = 7   # sky light
B = 8   # sky dark

# Cat sprite frame 1 (wings up)  16x16
CAT_F1 = [
    _,_,O,O,_,_,_,_,_,_,O,O,_,_,_,_,
    _,O,C,C,O,_,_,_,_,O,C,C,O,_,_,_,
    _,O,C,P,O,_,_,_,_,O,C,C,O,_,_,_,
    _,_,O,O,_,_,O,O,O,O,O,_,_,_,_,_,
    _,_,_,_,O,C,C,C,C,C,C,O,_,_,_,_,
    _,_,_,O,C,L,W,C,C,W,L,C,O,_,_,_,
    _,_,_,O,C,C,O,C,C,O,C,C,O,_,_,_,
    _,_,_,O,C,C,C,P,C,C,C,C,O,_,_,_,
    _,_,_,O,C,W,C,C,C,C,W,C,O,_,_,_,
    _,_,_,_,O,C,C,C,C,C,C,O,_,_,_,_,
    _,_,O,O,O,C,C,C,C,C,O,O,O,_,_,_,
    _,O,C,C,C,C,C,C,C,C,C,C,C,O,_,_,
    O,C,C,C,C,C,C,C,C,C,C,C,C,C,O,_,
    _,O,O,O,O,O,O,O,O,O,O,O,O,O,_,_,
    _,_,_,O,C,C,O,_,_,O,C,C,O,_,_,_,
    _,_,_,O,C,C,O,_,_,O,C,C,O,_,_,_,
]

# Cat sprite frame 2 (wings down)
CAT_F2 = [
    _,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,
    _,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,
    _,_,_,_,_,_,O,O,O,O,O,_,_,_,_,_,
    _,_,_,_,O,C,C,C,C,C,C,O,_,_,_,_,
    _,O,O,O,C,L,W,C,C,W,L,C,O,_,_,_,
    O,C,C,C,C,C,O,C,C,O,C,C,C,O,_,_,
    _,O,O,O,C,C,C,P,C,C,C,C,O,_,_,_,
    _,_,_,O,C,W,C,C,C,C,W,C,O,_,_,_,
    _,_,_,_,O,C,C,C,C,C,C,O,_,_,_,_,
    _,_,O,O,O,C,C,C,C,C,O,O,O,_,_,_,
    _,O,C,C,C,C,C,C,C,C,C,C,C,O,_,_,
    O,C,C,C,C,C,C,C,C,C,C,C,C,C,O,_,
    _,O,O,O,O,O,O,O,O,O,O,O,O,O,_,_,
    _,_,_,O,C,C,O,_,_,O,C,C,O,_,_,_,
    _,_,_,O,C,C,O,_,_,O,C,C,O,_,_,_,
    _,_,_,O,O,O,O,_,_,O,O,O,O,_,_,_,
]

# ---------------------------------------------------------------------------
# Build animation frames: cat flies across a sky background
# ---------------------------------------------------------------------------

W_IMG = 80   # canvas width
H_IMG = 50   # canvas height
CAT_W = 16
CAT_H = 16
N_FRAMES = 20
SCALE = 1  # sprite scale (1 = 16x16)


def draw_sky(width, height):
    """Simple gradient sky."""
    pixels = []
    for y in range(height):
        for x in range(width):
            # alternating light/dark stripes for sky depth
            if (x // 10 + y // 8) % 2 == 0:
                pixels.append(7)
            else:
                pixels.append(0)
    return pixels


def draw_stars(pixels, width, height, frame_index):
    """Occasional twinkling stars."""
    star_positions = [(5, 3), (20, 8), (60, 5), (75, 12), (40, 4),
                      (15, 45), (55, 40), (70, 38)]
    for sx, sy in star_positions:
        if 0 <= sx < width and 0 <= sy < height:
            if (frame_index // 3 + sx) % 3 != 0:
                pixels[sy * width + sx] = 6


def blit_sprite(pixels, sprite, sx, sy, img_w, img_h, scale=1):
    """Draw a 16x16 sprite at (sx, sy) with optional integer scale."""
    for row in range(CAT_H):
        for col in range(CAT_W):
            color = sprite[row * CAT_W + col]
            if color == _:
                continue  # transparent
            for dy in range(scale):
                for dx in range(scale):
                    px = sx + col * scale + dx
                    py = sy + row * scale + dy
                    if 0 <= px < img_w and 0 <= py < img_h:
                        pixels[py * img_w + px] = color


frames = []
for f in range(N_FRAMES):
    # Horizontal position: cat moves left to right and wraps
    cat_x = int((f / N_FRAMES) * (W_IMG + CAT_W)) - CAT_W
    # Vertical bobbing (sine-like using integer math)
    bob_table = [0, -1, -2, -2, -1, 0, 1, 2, 2, 1,
                 0, -1, -2, -2, -1, 0, 1, 2, 2, 1]
    cat_y = 15 + bob_table[f % len(bob_table)]

    # Choose sprite frame (flap every 3 frames)
    sprite = CAT_F1 if (f // 3) % 2 == 0 else CAT_F2

    pixels = draw_sky(W_IMG, H_IMG)
    draw_stars(pixels, W_IMG, H_IMG, f)
    blit_sprite(pixels, sprite, cat_x, cat_y, W_IMG, H_IMG, scale=SCALE)

    frames.append(bytes(pixels))

gif_data = build_gif(frames, W_IMG, H_IMG, PALETTE, delay_cs=8)

output_path = '/home/user/Boby/flying_cat.gif'
with open(output_path, 'wb') as fh:
    fh.write(gif_data)

print(f"GIF saved to {output_path}  ({len(gif_data)} bytes, {N_FRAMES} frames)")
