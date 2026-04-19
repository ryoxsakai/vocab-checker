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
    sa = src[3]/255; da = dst[3]/255
    oa = sa + da*(1-sa)
    if oa == 0: return (0,0,0,0)
    return (int((src[0]*sa+dst[0]*da*(1-sa))/oa),
            int((src[1]*sa+dst[1]*da*(1-sa))/oa),
            int((src[2]*sa+dst[2]*da*(1-sa))/oa),
            int(oa*255))

BG     = hex2rgba('#0f1117')
SURF   = hex2rgba('#1a1d27')
SURF2  = hex2rgba('#222535')
BORDER = hex2rgba('#2e3248')
ACCENT = hex2rgba('#5b6af0')
RED    = hex2rgba('#e05555')
WHITE  = (255,255,255,255)

pixels = [[(0,0,0,0)]*W for _ in range(H)]

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
            a = max(0.0, min(1.0, r-d+0.5))
            if a > 0:
                put(px, py, (*color[:3], int(color[3]*a)))

def circle(cx, cy, r, color):
    for py in range(max(0,int(cy-r)-1), min(H,int(cy+r)+2)):
        for px in range(max(0,int(cx-r)-1), min(W,int(cx+r)+2)):
            d = math.dist((px,py),(cx,cy))
            a = max(0.0, min(1.0, r-d+0.5))
            if a > 0:
                put(px, py, (*color[:3], int(color[3]*a)))

def ring(cx, cy, r_out, r_in, color):
    for py in range(max(0,int(cy-r_out)-1), min(H,int(cy+r_out)+2)):
        for px in range(max(0,int(cx-r_out)-1), min(W,int(cx+r_out)+2)):
            d = math.dist((px,py),(cx,cy))
            ao = max(0.0, min(1.0, r_out-d+0.5))
            ai = max(0.0, min(1.0, d-r_in+0.5))
            a = ao * ai
            if a > 0:
                put(px, py, (*color[:3], int(color[3]*a)))

def line(x1, y1, x2, y2, t, color):
    dx, dy = x2-x1, y2-y1
    ln = math.sqrt(dx*dx+dy*dy)
    if ln == 0: return
    steps = max(int(ln*2.5), 2)
    for i in range(steps+1):
        s = i/steps
        circle(x1+dx*s, y1+dy*s, t/2, color)

# ── Background ─────────────────────────────────────────────────────────
rrect(0, 0, W, H, 38, BG)

# ── Card shadow (back card, slightly offset) ────────────────────────────
rrect(34, 38, 116, 106, 14, SURF)

# ── Main card ───────────────────────────────────────────────────────────
rrect(22, 26, 116, 106, 14, SURF2)
# top accent strip
rrect(22, 26, 116, 6, 7, ACCENT)

# ── Vertical divider (center of card) ───────────────────────────────────
for py in range(40, 122):
    a = int(180 * max(0, 1 - abs(py-81)/40))
    put(80, py, (*BORDER[:3], a))

# ── Left side: big "A" in accent color ──────────────────────────────────
# A: apex at (56, 43), base width ~34px, height ~48px
ax, ay = 56, 43          # apex
bl, br = 38, 74          # base y
ll_x, lr_x = 37, 75      # base left / right x

# left leg
line(ll_x, bl, ax, ay, 5.5, ACCENT)
# right leg
line(lr_x, bl, ax, ay, 5.5, ACCENT)
# crossbar (at ~55% height from base)
cb_y = bl - int((bl-ay)*0.45)
cb_half = 11
line(ax-cb_half, cb_y, ax+cb_half, cb_y, 4.5, ACCENT)

# ── Right side: "あ" drawn with strokes ──────────────────────────────────
# Simplified あ: horizontal stroke + vertical + open circle
# positioned center-right of card: cx≈113, top≈44

# 1. Horizontal stroke at top
line(97, 50, 130, 50, 3.2, RED)

# 2. Short vertical descending from center of horizontal
line(113, 50, 113, 63, 3.2, RED)

# 3. Main curved loop (circle ring, open at top-left)
# Draw as partial ring: full circle minus a notch
r_out, r_in = 19, 12
cx_a, cy_a = 113, 88
for py in range(max(0,int(cy_a-r_out)-1), min(H,int(cy_a+r_out)+2)):
    for px in range(max(0,int(cx_a-r_out)-1), min(W,int(cx_a+r_out)+2)):
        d = math.dist((px,py),(cx_a,cy_a))
        ao = max(0.0, min(1.0, r_out-d+0.5))
        ai = max(0.0, min(1.0, d-r_in+0.5))
        a = ao*ai
        if a == 0: continue
        # exclude top-left notch (angle ~100°–160° from right)
        angle = math.degrees(math.atan2(-(py-cy_a), px-cx_a))
        if 105 < angle < 165:
            continue
        put(px, py, (*RED[:3], int(RED[3]*a)))

# 4. Small top-right accent mark of あ (the small hook/dot)
line(124, 58, 130, 64, 2.5, (*RED[:3], 200))

# ── Word/meaning label bars at bottom ───────────────────────────────────
# English word bar (accent)
rrect(30, 118, 46, 7, 3, (*ACCENT[:3], 180))
# Japanese meaning bars (red, two lines)
rrect(84, 118, 46, 7, 3, (*RED[:3], 160))

write_png('apple-touch-icon.png', W, H, pixels)
print("apple-touch-icon.png generated")
