"""AV TPL (count, entries{fmt,off,w,h,mips,0x1234}) decode/encode for GC texture formats."""
import struct
import numpy as np
BLK = {0: (8, 8, 4), 1: (8, 4, 8), 2: (8, 4, 8), 3: (4, 4, 16), 4: (4, 4, 16), 5: (4, 4, 16), 6: (4, 4, 32), 14: (8, 8, 4)}

def entries(d):
    n = struct.unpack('>I', d[:4])[0]; out = []
    for i in range(n):
        f, o, w, h, m, k = struct.unpack('>IIHHHH', d[4 + 16 * i:20 + 16 * i])
        if k != 0x1234 or f not in BLK or w == 0: out.append(None); continue
        out.append(dict(i=i, fmt=f, off=o, w=w, h=h, mips=m))
    return out

def size(e):
    bw, bh, bpp = BLK[e['fmt']]
    W = -(-e['w'] // bw) * bw; H = -(-e['h'] // bh) * bh
    return W * H * bpp // 8

def _untile(px, W, H, bw, bh):
    # px: (nblocks, bh, bw, C) in block order -> (H, W, C)
    a = px.reshape(H // bh, W // bw, bh, bw, -1).transpose(0, 2, 1, 3, 4).reshape(H, W, -1)
    return a

def _tile(img, bw, bh):
    H, W, C = img.shape
    return img.reshape(H // bh, bh, W // bw, bw, C).transpose(0, 2, 1, 3, 4).reshape(-1, bh, bw, C)

def _c565(v):
    r = (v >> 11) & 31; g = (v >> 5) & 63; b = v & 31
    return np.stack([r * 255 // 31, g * 255 // 63, b * 255 // 31], -1)

def decode(d, e):
    f = e['fmt']; bw, bh, bpp = BLK[f]
    W = -(-e['w'] // bw) * bw; H = -(-e['h'] // bh) * bh
    raw = np.frombuffer(d, np.uint8, size(e), e['off'])
    if f == 0:
        v = np.stack([raw >> 4, raw & 15], -1).reshape(-1) * 17
        rgba = np.stack([v, v, v, np.full_like(v, 255)], -1)
    elif f == 1:
        v = raw; rgba = np.stack([v, v, v, np.full_like(v, 255)], -1)
    elif f == 2:
        a = (raw >> 4) * 17; i = (raw & 15) * 17; rgba = np.stack([i, i, i, a], -1)
    elif f == 3:
        p = raw.reshape(-1, 2); rgba = np.stack([p[:, 1], p[:, 1], p[:, 1], p[:, 0]], -1)
    elif f == 4:
        v = raw.view('>u2').astype(np.int32); rgba = np.concatenate([_c565(v), np.full((len(v), 1), 255)], -1)
    elif f == 5:
        v = raw.view('>u2').astype(np.int32); op = (v & 0x8000) != 0
        r = np.where(op, ((v >> 10) & 31) * 255 // 31, ((v >> 8) & 15) * 17)
        g = np.where(op, ((v >> 5) & 31) * 255 // 31, ((v >> 4) & 15) * 17)
        b = np.where(op, (v & 31) * 255 // 31, (v & 15) * 17)
        a = np.where(op, 255, ((v >> 12) & 7) * 255 // 7)
        rgba = np.stack([r, g, b, a], -1)
    elif f == 6:
        blk = raw.reshape(-1, 2, 16, 2)
        ar = blk[:, 0]; gb = blk[:, 1]
        rgba = np.stack([ar[..., 1], gb[..., 0], gb[..., 1], ar[..., 0]], -1).reshape(-1, 4)
    elif f == 14:
        return _dcmpr(raw, W, H)[:e['h'], :e['w']]
    px = rgba.astype(np.uint8).reshape(-1, bh, bw, 4)
    return _untile(px, W, H, bw, bh)[:e['h'], :e['w']]

def _dcmpr(raw, W, H):
    out = np.zeros((H, W, 4), np.uint8); k = 0
    for by in range(0, H, 8):
        for bx in range(0, W, 8):
            for sy in (0, 4):
                for sx in (0, 4):
                    c0, c1 = struct.unpack('>HH', raw[k:k + 4].tobytes()); bits = struct.unpack('>I', raw[k + 4:k + 8].tobytes())[0]; k += 8
                    p0 = _c565(np.array(c0)).astype(int); p1 = _c565(np.array(c1)).astype(int)
                    if c0 > c1: pal = [list(p0) + [255], list(p1) + [255], list((2 * p0 + p1) // 3) + [255], list((p0 + 2 * p1) // 3) + [255]]
                    else: pal = [list(p0) + [255], list(p1) + [255], list((p0 + p1) // 2) + [255], [0, 0, 0, 0]]
                    for i in range(16):
                        out[by + sy + i // 4, bx + sx + i % 4] = pal[(bits >> (30 - 2 * i)) & 3]
    return out


def _ecmpr(img, W, H):
    """Simple CMPR encoder: per 4x4 block, 3-colour+transparent mode (c0<=c1) when any pixel has alpha<128."""
    full = np.zeros((H, W, 4), np.uint8); full[:img.shape[0], :img.shape[1]] = img
    out = bytearray()
    def q(c): c = np.clip(c, 0, 255).astype(int); return (c[0] * 31 // 255) << 11 | (c[1] * 63 // 255) << 5 | c[2] * 31 // 255
    for by in range(0, H, 8):
        for bx in range(0, W, 8):
            for sy in (0, 4):
                for sx in (0, 4):
                    b = full[by + sy:by + sy + 4, bx + sx:bx + sx + 4].reshape(16, 4).astype(int)
                    op = b[:, 3] >= 128
                    if not op.any(): out += bytes(4) + bytes([255] * 4); continue
                    cs = b[op, :3]; lum = cs.sum(1)
                    lo, hi = cs[lum.argmin()], cs[lum.argmax()]
                    c0, c1 = q(lo), q(hi)
                    trans = not op.all()
                    if trans or c0 == c1:
                        if c0 > c1: c0, c1 = c1, c0
                        p0 = _c565(np.array(c0)).astype(int); p1 = _c565(np.array(c1)).astype(int)
                        pal = [p0, p1, (p0 + p1) // 2]
                    else:
                        if c0 < c1: c0, c1 = c1, c0
                        p0 = _c565(np.array(c0)).astype(int); p1 = _c565(np.array(c1)).astype(int)
                        pal = [p0, p1, (2 * p0 + p1) // 3, (p0 + 2 * p1) // 3]
                    bits = 0
                    for i in range(16):
                        if not op[i] and (trans or c0 <= c1): idx = 3
                        else: idx = int(np.argmin([((b[i, :3] - pc) ** 2).sum() for pc in pal]))
                        bits |= idx << (30 - 2 * i)
                    out += struct.pack('>HHI', c0, c1, bits)
    return bytes(out)

def encode(img, e):
    """img: (h,w,4) uint8 RGBA -> bytes for fmt"""
    f = e['fmt']
    if f == 14: return _ecmpr(img, -(-e['w'] // 8) * 8, -(-e['h'] // 8) * 8)
    bw, bh, bpp = BLK[f]
    W = -(-e['w'] // bw) * bw; H = -(-e['h'] // bh) * bh
    full = np.zeros((H, W, 4), np.uint8); full[:e['h'], :e['w']] = img
    t = _tile(full, bw, bh).reshape(-1, 4).astype(np.int32)
    r, g, b, a = t.T
    if f == 0:
        i = ((r + g + b) // 3 * 15 + 127) // 255; return (i[0::2] << 4 | i[1::2]).astype(np.uint8).tobytes()
    if f == 1: return ((r + g + b) // 3).astype(np.uint8).tobytes()
    if f == 2:
        i = ((r + g + b) // 3 * 15 + 127) // 255; aa = (a * 15 + 127) // 255; return (aa << 4 | i).astype(np.uint8).tobytes()
    if f == 3: return np.stack([a, (r + g + b) // 3], -1).astype(np.uint8).tobytes()
    if f == 4: return ((r * 31 // 255) << 11 | (g * 63 // 255) << 5 | b * 31 // 255).astype('>u2').tobytes()
    if f == 5:
        op = a >= 0xe0
        v = np.where(op, 0x8000 | (r * 31 // 255) << 10 | (g * 31 // 255) << 5 | b * 31 // 255,
                     (a * 7 // 255) << 12 | (r * 15 // 255) << 8 | (g * 15 // 255) << 4 | b * 15 // 255)
        return v.astype('>u2').tobytes()
    if f == 6:
        p = t.reshape(-1, 16, 4)
        ar = np.stack([p[..., 3], p[..., 0]], -1); gb = np.stack([p[..., 1], p[..., 2]], -1)
        return np.stack([ar, gb], 1).astype(np.uint8).tobytes()
    raise ValueError('fmt %d' % f)
