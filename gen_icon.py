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
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n')
        f.write(chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)))
        f.write(chunk(b'IDAT', zlib.compress(bytes(raw), 9)))
        f.write(chunk(b'IEND', b''))

def hex2rgba(h, a=255):
    h = h.lstrip('#')
    return (int(h[0:2],16), int(h[2:4],16), int(h[4:6],16), a)

def blend(src, dst):
    sa, da = src[3]/255, dst[3]/255
    oa = sa + da*(1-sa)
    if oa == 0: return (0,0,0,0)
    return (int((src[0]*sa+dst[0]*da*(1-sa))/oa),
            int((src[1]*sa+dst[1]*da*(1-sa))/oa),
            int((src[2]*sa+dst[2]*da*(1-sa))/oa),
            int(oa*255))

NAVY  = hex2rgba('#0d1940')
WHITE = (255, 255, 255, 255)
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
            if a > 0: put(px, py, (*color[:3], int(color[3]*a)))

def circ(cx, cy, r, color):
    for py in range(max(0,int(cy-r)-1), min(H,int(cy+r)+2)):
        for px in range(max(0,int(cx-r)-1), min(W,int(cx+r)+2)):
            d = math.dist((px,py),(cx,cy))
            a = max(0.0, min(1.0, r-d+0.5))
            if a > 0: put(px, py, (*color[:3], int(color[3]*a)))

def tline(x1, y1, x2, y2, t, color):
    dx, dy = x2-x1, y2-y1
    ln = math.sqrt(dx*dx+dy*dy)
    if ln == 0: return
    for i in range(int(ln*2.5)+1):
        s = i/(ln*2.5)
        circ(x1+dx*s, y1+dy*s, t/2, color)

def fill_poly(pts, color):
    ys = [p[1] for p in pts]
    y0, y1 = max(0,int(min(ys))), min(H-1,int(max(ys)))
    n = len(pts)
    for y in range(y0, y1+1):
        xs = []
        for i in range(n):
            ax,ay = pts[i]; bx,by = pts[(i+1)%n]
            if ay==by: continue
            if min(ay,by)<=y<max(ay,by):
                xs.append(ax+(y-ay)*(bx-ax)/(by-ay))
        xs.sort()
        for i in range(0,len(xs)-1,2):
            for x in range(max(0,int(xs[i])),min(W,int(xs[i+1])+1)):
                pixels[y][x] = blend(color, pixels[y][x])

def ring(cx, cy, ro, ri, color, ex_s=None, ex_e=None):
    for py in range(max(0,int(cy-ro)-1), min(H,int(cy+ro)+2)):
        for px in range(max(0,int(cx-ro)-1), min(W,int(cx+ro)+2)):
            d = math.dist((px,py),(cx,cy))
            a = max(0.0,min(1.0,ro-d+0.5)) * max(0.0,min(1.0,d-ri+0.5))
            if a == 0: continue
            if ex_s is not None:
                ang = math.degrees(math.atan2(-(py-cy), px-cx)) % 360
                es, ee = ex_s%360, ex_e%360
                if es<=ee:
                    if es<=ang<=ee: continue
                else:
                    if ang>=es or ang<=ee: continue
            put(px, py, (*color[:3], int(color[3]*a)))

def bezier(p0,p1,p2,p3,steps=40):
    pts=[]
    for i in range(steps+1):
        t=i/steps
        pts.append(((1-t)**3*p0[0]+3*(1-t)**2*t*p1[0]+3*(1-t)*t**2*p2[0]+t**3*p3[0],
                     (1-t)**3*p0[1]+3*(1-t)**2*t*p1[1]+3*(1-t)*t**2*p2[1]+t**3*p3[1]))
    return pts

# ── Background ───────────────────────────────────────────────────────────────
rrect(0, 0, W, H, 38, NAVY)

# ── Book: bottom fan (drawn first so pages overlay it) ───────────────────────
for i, cy in enumerate([117, 111, 105]):
    pts = bezier((36,107+i), (62,cy), (118,cy), (144,107+i))
    for j in range(len(pts)-1):
        tline(pts[j][0],pts[j][1],pts[j+1][0],pts[j+1][1], 2.5, WHITE)

# ── Book: right page solid fill ──────────────────────────────────────────────
fill_poly([(90,110),(150,50),(116,36),(90,108)], WHITE)

# ── Book: left page lines ────────────────────────────────────────────────────
T = 3.8
tline(90,110, 30,52, T, WHITE)     # outer left edge
tline(90,110, 54,38, T, WHITE)     # middle
tline(90,110, 76,34, T, WHITE)     # inner (near spine)
tline(90,110, 150,50, T, WHITE)    # outer right edge

# ── Book: outer cover brackets ───────────────────────────────────────────────
B = 3.2
tline(27,50, 27,108, B, WHITE)
tline(27,50, 42,50, B, WHITE)
tline(27,108, 42,108, B, WHITE)
tline(153,50, 153,108, B, WHITE)
tline(153,50, 138,50, B, WHITE)
tline(153,108, 138,108, B, WHITE)

# spine dot
circ(90, 113, 3.5, WHITE)

# ── VOCAB text ────────────────────────────────────────────────────────────────
# y: 129-149 (20px tall), centered horizontally
# widths: V=14, O=18, C=18, A=14, B=17, gaps=4 → total=89
# start = (180-89)/2 = 45.5

TT = 3.0
sy, ey, my = 129, 149, 139

# V (45–59, apex 52)
tline(45, sy, 52, ey, TT, WHITE)
tline(59, sy, 52, ey, TT, WHITE)

# O center 72 (63–81)
ring(72, my, 9.5, 5.5, WHITE)

# C center 91 (82–100), open right ~70°
ring(91, my, 9.5, 5.5, WHITE, ex_s=320, ex_e=40)

# A (104–118, apex 111)
tline(104, ey, 111, sy, TT, WHITE)
tline(118, ey, 111, sy, TT, WHITE)
tline(106.5, 142, 115.5, 142, TT, WHITE)

# B (122–139)
tline(122, sy, 122, ey, TT, WHITE)
tline(122, sy, 129, sy, TT, WHITE)
tline(122, my, 131, my, TT, WHITE)
tline(122, ey, 129, ey, TT, WHITE)
ring(129, 134, 7.5, 4.0, WHITE, ex_s=90, ex_e=270)
ring(129, 144, 7.5, 4.0, WHITE, ex_s=90, ex_e=270)

write_png('apple-touch-icon.png', W, H, pixels)
print("Done")
