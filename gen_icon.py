import struct, zlib, math

W = H = 180

def write_png(path, w, h, pixels):
    def chunk(tag, data):
        crc = zlib.crc32(tag + data) & 0xffffffff
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', crc)
    raw = bytearray()
    for row in pixels:
        raw.append(0)
        for r, g, b, a in row:
            raw.extend([r, g, b, a])
    compressed = zlib.compress(bytes(raw), 9)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n')
        f.write(chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)))
        f.write(chunk(b'IDAT', compressed))
        f.write(chunk(b'IEND', b''))

def hex2rgba(h, a=255):
    h = h.lstrip('#')
    return (int(h[0:2],16), int(h[2:4],16), int(h[4:6],16), a)

def blend(src, dst):
    sa = src[3] / 255; da = dst[3] / 255
    oa = sa + da*(1-sa)
    if oa == 0: return (0,0,0,0)
    return (
        int((src[0]*sa + dst[0]*da*(1-sa)) / oa),
        int((src[1]*sa + dst[1]*da*(1-sa)) / oa),
        int((src[2]*sa + dst[2]*da*(1-sa)) / oa),
        int(oa*255),
    )

BG      = hex2rgba('#0f1117')
SURF    = hex2rgba('#1a1d27')
SURF2   = hex2rgba('#222535')
BORDER  = hex2rgba('#2e3248')
ACCENT  = hex2rgba('#5b6af0')
ACCENT_L= hex2rgba('#7c8cf8')
DIM     = hex2rgba('#555a7a')
GREEN   = hex2rgba('#4caf84')
WHITE   = (255, 255, 255, 255)

pixels = [[(0,0,0,0)] * W for _ in range(H)]

def put(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        pixels[y][x] = blend(c, pixels[y][x])

def rrect(x1, y1, w, h, r, color):
    x2, y2 = x1+w, y1+h
    for py in range(max(0,int(y1)-1), min(H,int(y2)+2)):
        for px in range(max(0,int(x1)-1), min(W,int(x2)+2)):
            cx = max(x1+r, min(float(px), x2-r))
            cy = max(y1+r, min(float(py), y2-r))
            d = math.dist((px,py),(cx,cy))
            a = max(0.0, min(1.0, r - d + 0.5))
            if a > 0:
                c = (*color[:3], int(color[3]*a))
                put(px, py, c)

def circle(cx, cy, r, color):
    for py in range(max(0,int(cy-r)-1), min(H,int(cy+r)+2)):
        for px in range(max(0,int(cx-r)-1), min(W,int(cx+r)+2)):
            d = math.dist((px,py),(cx,cy))
            a = max(0.0, min(1.0, r - d + 0.5))
            if a > 0:
                c = (*color[:3], int(color[3]*a))
                put(px, py, c)

def thick_line(x1, y1, x2, y2, t, color):
    dx, dy = x2-x1, y2-y1
    ln = math.sqrt(dx*dx+dy*dy)
    if ln == 0: return
    steps = int(ln*3)
    for i in range(steps+1):
        s = i/steps
        circle(x1+dx*s, y1+dy*s, t/2, color)

# ── Background ──────────────────────────────────────────────────────────────
rrect(0, 0, W, H, 36, BG)

# ── Vocabulary card ──────────────────────────────────────────────────────────
# Slight gradient feel: draw surface layer first, then slightly lighter top
rrect(18, 26, 144, 128, 16, SURF)
rrect(18, 26, 144, 68, 16, SURF2)   # brighter top half

# Top border accent stripe
rrect(18, 26, 144, 6, 4, ACCENT)

# "Word" label bar (accent)
rrect(32, 46, 76, 11, 5, ACCENT)
rrect(32, 46, 76, 11, 5, (*ACCENT_L[:3], 60))  # shimmer

# "Meaning" dim bars
rrect(32, 65, 98, 8, 4, DIM)
rrect(32, 79, 76, 7, 3, (*DIM[:3], 160))

# Divider
for px in range(28, 154):
    a = int(255 * max(0, 1 - abs(px-91)/63))
    put(px, 100, (*BORDER[:3], a))

# Second entry (slightly faded)
rrect(32, 110, 58, 9, 4, (*ACCENT[:3], 180))
rrect(32, 126, 88, 7, 3, (*DIM[:3], 130))
rrect(32, 138, 62, 6, 3, (*DIM[:3], 80))

# ── Checkmark badge ──────────────────────────────────────────────────────────
bx, by = 139, 42   # badge center

# Shadow ring
circle(bx, by, 23, (*BG[:3], 200))
# Green circle
circle(bx, by, 19, GREEN)
# Inner highlight
circle(bx-2, by-3, 8, (*WHITE[:3], 18))

# White checkmark  (short leg then long leg)
thick_line(bx-8, by+1,  bx-2, by+7,  3.6, WHITE)
thick_line(bx-2, by+7,  bx+9, by-6,  3.6, WHITE)

write_png('apple-touch-icon.png', W, H, pixels)
print("apple-touch-icon.png generated")
