"""Generate a simple .ico file for Desktop Widgets (no external deps)."""
import struct, io, os

def create_ico(path, sizes=(16, 32, 48, 256)):
    """Create a minimal .ico with white-on-black 'W' squares."""
    images = []
    for sz in sizes:
        images.append(_make_bmp(sz))

    # ICO header
    hdr = struct.pack('<HHH', 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = b''
    for i, (sz, data) in enumerate(zip(sizes, images)):
        w = 0 if sz == 256 else sz
        h = 0 if sz == 256 else sz
        entries += struct.pack('<BBBBHHII', w, h, 0, 0, 1, 32, len(data), offset)
        offset += len(data)

    with open(path, 'wb') as f:
        f.write(hdr + entries)
        for data in images:
            f.write(data)

def _make_bmp(sz):
    """Create a 32-bit BGRA BMP image data (no file header, just DIB)."""
    pixels = bytearray(sz * sz * 4)
    # Black background
    for i in range(sz * sz):
        pixels[i*4:i*4+4] = b'\x0a\x0a\x0a\xff'  # BGRA

    # Draw a simple "W" shape in white
    cx, cy = sz // 2, sz // 2
    t = max(1, sz // 16)  # line thickness

    # W as 5 vertical strokes going down then up
    h_top = sz // 5
    h_bot = sz - sz // 5
    w_left = sz // 5
    w_right = sz - sz // 5
    w_mid = sz // 2

    def draw_line(x0, y0, x1, y1):
        steps = max(abs(x1-x0), abs(y1-y0), 1)
        for s in range(steps + 1):
            frac = s / steps
            px = int(x0 + (x1-x0) * frac)
            py = int(y0 + (y1-y0) * frac)
            for dx in range(-t//2, t//2 + 1):
                for dy in range(-t//2, t//2 + 1):
                    nx, ny = px+dx, py+dy
                    if 0 <= nx < sz and 0 <= ny < sz:
                        # BMP is bottom-up
                        idx = ((sz - 1 - ny) * sz + nx) * 4
                        pixels[idx:idx+4] = b'\xff\xff\xff\xff'

    # "W" shape: left down, left-mid up, mid down, right-mid up, right down
    draw_line(w_left, h_top, w_left + (w_mid-w_left)//2, h_bot)
    draw_line(w_left + (w_mid-w_left)//2, h_bot, w_mid, h_top + (h_bot-h_top)//3)
    draw_line(w_mid, h_top + (h_bot-h_top)//3, w_right - (w_right-w_mid)//2, h_bot)
    draw_line(w_right - (w_right-w_mid)//2, h_bot, w_right, h_top)

    # Add rounded corner border
    r = max(2, sz // 8)
    border_color = b'\x33\x33\x33\xff'
    for x in range(sz):
        for y in range(sz):
            edge = False
            # Check if on border
            if x < t or x >= sz-t or y < t or y >= sz-t:
                # Check rounded corners
                for cx, cy in [(r, r), (sz-1-r, r), (r, sz-1-r), (sz-1-r, sz-1-r)]:
                    dx, dy = x - cx, y - cy
                    if (x < r or x >= sz-r) and (y < r or y >= sz-r):
                        if dx*dx + dy*dy > r*r:
                            # Outside corner - make transparent
                            idx = ((sz-1-y)*sz+x)*4
                            pixels[idx:idx+4] = b'\x00\x00\x00\x00'
                            edge = True
                if not edge and (x < t or x >= sz-t or y < t or y >= sz-t):
                    idx = ((sz-1-y)*sz+x)*4
                    pixels[idx:idx+4] = border_color

    # DIB header (BITMAPINFOHEADER)
    dib = struct.pack('<IiiHHIIiiII',
        40,         # header size
        sz,         # width
        sz * 2,     # height (x2 for ICO format: image + mask)
        1,          # planes
        32,         # bpp
        0,          # compression
        len(pixels) + sz * sz // 8,  # image size
        0, 0, 0, 0)

    # AND mask (all zeros = fully opaque, alpha channel handles transparency)
    mask_row = (sz + 31) // 32 * 4
    mask = b'\x00' * mask_row * sz

    return dib + bytes(pixels) + mask

if __name__ == '__main__':
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'desktop_widgets.ico')
    create_ico(out)
    print(f'Created {out}')
