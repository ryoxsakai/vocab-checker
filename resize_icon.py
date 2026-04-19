import struct, zlib, math

def read_png(path):
    with open(path, 'rb') as f:
        data = f.read()
    assert data[:8] == b'\x89PNG\r\n\x1a\n', "Not a valid PNG"
    pos, idat = 8, b''
    ihdr = plte = None
    while pos < len(data):
        length = struct.unpack('>I', data[pos:pos+4])[0]
        tag = data[pos+4:pos+8]
        body = data[pos+8:pos+8+length]
        pos += 12 + length
        if tag == b'IHDR': ihdr = body
        elif tag == b'PLTE': plte = body
        elif tag == b'IDAT': idat += body
        elif tag == b'IEND': break
    w, h = struct.unpack('>II', ihdr[:8])
    bit_depth, color_type = ihdr[8], ihdr[9]
    spp = {0:1, 2:3, 3:1, 4:2, 6:4}[color_type]
    bpp = max(1, (bit_depth * spp) // 8)
    stride = w * bpp
    raw = zlib.decompress(idat)
    rows, prev = [], bytes(stride)
    for y in range(h):
        ft = raw[y*(stride+1)]
        row = bytearray(raw[y*(stride+1)+1 : y*(stride+1)+1+stride])
        if ft == 1:
            for i in range(bpp, len(row)): row[i] = (row[i] + row[i-bpp]) & 0xFF
        elif ft == 2:
            for i in range(len(row)): row[i] = (row[i] + prev[i]) & 0xFF
        elif ft == 3:
            for i in range(len(row)):
                a = row[i-bpp] if i >= bpp else 0
                row[i] = (row[i] + (a + prev[i]) // 2) & 0xFF
        elif ft == 4:
            for i in range(len(row)):
                a = row[i-bpp] if i >= bpp else 0
                b = prev[i]; c = prev[i-bpp] if i >= bpp else 0
                p = a+b-c; pa,pb,pc = abs(p-a),abs(p-b),abs(p-c)
                pr = a if pa<=pb and pa<=pc else (b if pb<=pc else c)
                row[i] = (row[i] + pr) & 0xFF
        rows.append(bytes(row)); prev = bytes(row)
    return w, h, bit_depth, color_type, bpp, rows, plte

def get_rgba(x, y, w, h, bd, ct, bpp, rows, plte):
    x = max(0, min(w-1, x)); y = max(0, min(h-1, y))
    row = rows[y]
    if bd == 8:
        if ct == 2:   i=x*3; return row[i],row[i+1],row[i+2],255
        elif ct == 6: i=x*4; return row[i],row[i+1],row[i+2],row[i+3]
        elif ct == 0: v=row[x]; return v,v,v,255
        elif ct == 4: i=x*2; v=row[i]; return v,v,v,row[i+1]
        elif ct == 3:
            i = row[x]*3
            return plte[i],plte[i+1],plte[i+2],255
    elif bd == 16:
        if ct == 2:   i=x*6; return row[i],row[i+2],row[i+4],255
        elif ct == 6: i=x*8; return row[i],row[i+2],row[i+4],row[i+6]
    return 128,128,128,255

def resize(src, dst, nw, nh):
    w, h, bd, ct, bpp, rows, plte = read_png(src)
    print(f"Source: {w}x{h}, color_type={ct}, bit_depth={bd}")

    # Center-crop to square
    if w > h:
        cx, cy, cs = (w-h)//2, 0, h
    else:
        cx, cy, cs = 0, (h-w)//2, w

    out = []
    for dy in range(nh):
        row_out = []
        for dx in range(nw):
            sx = (dx+0.5)*cs/nw - 0.5 + cx
            sy = (dy+0.5)*cs/nh - 0.5 + cy
            x0,y0 = int(math.floor(sx)), int(math.floor(sy))
            fx,fy = sx-x0, sy-y0
            p00 = get_rgba(x0,  y0,  w,h,bd,ct,bpp,rows,plte)
            p10 = get_rgba(x0+1,y0,  w,h,bd,ct,bpp,rows,plte)
            p01 = get_rgba(x0,  y0+1,w,h,bd,ct,bpp,rows,plte)
            p11 = get_rgba(x0+1,y0+1,w,h,bd,ct,bpp,rows,plte)
            r=int(p00[0]*(1-fx)*(1-fy)+p10[0]*fx*(1-fy)+p01[0]*(1-fx)*fy+p11[0]*fx*fy)
            g=int(p00[1]*(1-fx)*(1-fy)+p10[1]*fx*(1-fy)+p01[1]*(1-fx)*fy+p11[1]*fx*fy)
            b=int(p00[2]*(1-fx)*(1-fy)+p10[2]*fx*(1-fy)+p01[2]*(1-fx)*fy+p11[2]*fx*fy)
            a=int(p00[3]*(1-fx)*(1-fy)+p10[3]*fx*(1-fy)+p01[3]*(1-fx)*fy+p11[3]*fx*fy)
            row_out.append((r,g,b,a))
        out.append(row_out)
        if dy % 30 == 0: print(f"  {dy}/{nh}...")

    def chunk(tag, data):
        crc = zlib.crc32(tag+data) & 0xffffffff
        return struct.pack('>I',len(data))+tag+data+struct.pack('>I',crc)
    raw = bytearray()
    for row in out:
        raw.append(0)
        for r,g,b,a in row: raw.extend([r,g,b,a])
    with open(dst,'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n')
        f.write(chunk(b'IHDR', struct.pack('>IIBBBBB',nw,nh,8,6,0,0,0)))
        f.write(chunk(b'IDAT', zlib.compress(bytes(raw),9)))
        f.write(chunk(b'IEND', b''))
    print(f"Done: {dst} ({nw}x{nh})")

resize('IMG_5804.png', 'apple-touch-icon.png', 180, 180)
