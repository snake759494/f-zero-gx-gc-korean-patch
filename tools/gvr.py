"""GVR (GVRT chunk) texture decode/encode for GameCube formats (vectorised)."""
import struct, re
import numpy as np
from PIL import Image

BLK = {0: (8, 8, 4), 1: (8, 4, 8), 2: (8, 4, 8), 3: (4, 4, 16), 4: (4, 4, 16), 5: (4, 4, 16), 6: (4, 4, 32),
       8: (8, 8, 4), 9: (8, 4, 8), 14: (8, 8, 4)}

def find(b):
    """yield (offset_of_GVRT, fmt, w, h, data_offset, data_len, pal_info)"""
    for m in re.finditer(b'GVRT', b):
        o = m.start()
        size = struct.unpack('<I', b[o + 4:o + 8])[0]
        pf, fmt = b[o + 10], b[o + 11]
        w, h = struct.unpack('>HH', b[o + 12:o + 16])
        if fmt not in BLK or not (0 < w <= 1024 and 0 < h <= 1024): continue
        yield dict(off=o, fmt=fmt, pf=pf, w=w, h=h, data=o + 16, size=size - 8)

def _tiles(arr, W, H, bw, bh):
    # arr: (H,W,...) -> tile order (H/bh, W/bw, bh, bw, ...)
    s = arr.shape[2:]
    return arr.reshape(H // bh, bh, W // bw, bw, *s).swapaxes(1, 2)

def _untile(t, W, H, bw, bh):
    s = t.shape[4:]
    return t.swapaxes(1, 2).reshape(H, W, *s)

def decode(b, t):
    fmt, w, h = t['fmt'], t['w'], t['h']
    bw, bh, bpp = BLK[fmt]
    W = (w + bw - 1) // bw * bw; H = (h + bh - 1) // bh * bh
    n = W * H * bpp // 8
    d = np.frombuffer(b[t['data']:t['data'] + n], np.uint8)
    if fmt == 0:
        v = np.stack([d >> 4, d & 15], 1).reshape(-1) * 17
        t4 = v.reshape(H // bh, W // bw, bh, bw)
        g = _untile(t4, W, H, bw, bh)
        rgba = np.stack([g, g, g, g], -1)
    elif fmt == 1:
        g = _untile(d.reshape(H // bh, W // bw, bh, bw), W, H, bw, bh)
        rgba = np.stack([g, g, g, g], -1)
    elif fmt == 2:
        g = _untile(d.reshape(H // bh, W // bw, bh, bw), W, H, bw, bh)
        i = (g & 15) * 17; a = (g >> 4) * 17
        rgba = np.stack([i, i, i, a], -1)
    elif fmt == 3:
        g = _untile(d.reshape(H // bh, W // bw, bh, bw, 2), W, H, bw, bh)
        rgba = np.stack([g[..., 1], g[..., 1], g[..., 1], g[..., 0]], -1)
    elif fmt in (4, 5):
        v = d.view('>u2').astype(np.int32)
        g = _untile(v.reshape(H // bh, W // bw, bh, bw), W, H, bw, bh)
        if fmt == 4:
            r = (g >> 11 & 31) * 255 // 31; gg = (g >> 5 & 63) * 255 // 63; bb = (g & 31) * 255 // 31; a = np.full_like(g, 255)
        else:
            op = g & 0x8000
            r = np.where(op, (g >> 10 & 31) * 255 // 31, (g >> 8 & 15) * 17)
            gg = np.where(op, (g >> 5 & 31) * 255 // 31, (g >> 4 & 15) * 17)
            bb = np.where(op, (g & 31) * 255 // 31, (g & 15) * 17)
            a = np.where(op, 255, (g >> 12 & 7) * 255 // 7)
        rgba = np.stack([r, gg, bb, a], -1)
    elif fmt == 6:
        blk = d.reshape(H // 4, W // 4, 2, 16, 2)  # AR block then GB block
        a = blk[:, :, 0, :, 0]; r = blk[:, :, 0, :, 1]; g = blk[:, :, 1, :, 0]; bl = blk[:, :, 1, :, 1]
        px = np.stack([r, g, bl, a], -1).reshape(H // 4, W // 4, 4, 4, 4)
        rgba = _untile(px, W, H, 4, 4)
    elif fmt == 14:
        blk = d.reshape(-1, 8)
        c0 = blk[:, 0].astype(np.int32) << 8 | blk[:, 1]; c1 = blk[:, 2].astype(np.int32) << 8 | blk[:, 3]
        bits = (blk[:, 4].astype(np.uint32) << 24 | blk[:, 5].astype(np.uint32) << 16 | blk[:, 6].astype(np.uint32) << 8 | blk[:, 7])
        def rgb(c): return np.stack([(c >> 11 & 31) * 255 // 31, (c >> 5 & 63) * 255 // 63, (c & 31) * 255 // 31, np.full_like(c, 255)], -1)
        A, B = rgb(c0), rgb(c1)
        gt = (c0 > c1)[:, None]
        C2 = np.where(gt, (2 * A + B) // 3, (A + B) // 2)
        C3 = np.where(gt, (A + 2 * B) // 3, 0)
        pal = np.stack([A, B, C2, C3], 1)  # (n,4,4)
        idx = np.stack([(bits >> (30 - 2 * k)) & 3 for k in range(16)], 1).astype(np.int64)
        px = np.take_along_axis(pal, idx[:, :, None], 1)  # (n,16,4)
        px = px.reshape(H // 8, W // 8, 2, 2, 4, 4, 4)  # by,bx,sy,sx,y,x,c
        rgba = px.transpose(0, 2, 4, 1, 3, 5, 6).reshape(H, W, 4)
    else:
        return None
    return Image.fromarray(rgba[:h, :w].astype(np.uint8), 'RGBA')

def encode(img, t):
    """encode RGBA PIL image (size w,h) into bytes for texture t's format"""
    fmt, w, h = t['fmt'], t['w'], t['h']
    bw, bh, bpp = BLK[fmt]
    W = (w + bw - 1) // bw * bw; H = (h + bh - 1) // bh * bh
    a = np.zeros((H, W, 4), np.int32); a[:h, :w] = np.array(img.convert('RGBA'), np.int32)
    r, g, b_, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    if fmt == 5:
        op = al >= 224
        v_op = 0x8000 | ((r * 31 + 127) // 255) << 10 | ((g * 31 + 127) // 255) << 5 | ((b_ * 31 + 127) // 255)
        v_tr = ((al * 7 + 127) // 255) << 12 | ((r * 15 + 127) // 255) << 8 | ((g * 15 + 127) // 255) << 4 | ((b_ * 15 + 127) // 255)
        v = np.where(op, v_op, v_tr).astype('>u2')
        return _tiles(v, W, H, bw, bh).tobytes()
    if fmt == 4:
        v = (((r * 31 + 127) // 255) << 11 | ((g * 63 + 127) // 255) << 5 | ((b_ * 31 + 127) // 255)).astype('>u2')
        return _tiles(v, W, H, bw, bh).tobytes()
    if fmt == 3:
        i = (r * 30 + g * 59 + b_ * 11) // 100
        v = np.stack([al, i], -1).astype(np.uint8)
        return _tiles(v, W, H, bw, bh).tobytes()
    if fmt == 2:
        i = (r * 30 + g * 59 + b_ * 11) // 100
        v = (((al * 15 + 127) // 255) << 4 | ((i * 15 + 127) // 255)).astype(np.uint8)
        return _tiles(v, W, H, bw, bh).tobytes()
    if fmt == 1:
        i = ((r * 30 + g * 59 + b_ * 11) // 100).astype(np.uint8)
        return _tiles(i, W, H, bw, bh).tobytes()
    if fmt == 0:
        i = (r * 30 + g * 59 + b_ * 11) // 100
        q = ((i * 15 + 127) // 255).astype(np.uint8)
        tl = _tiles(q, W, H, bw, bh).reshape(-1)
        return (tl[0::2] << 4 | tl[1::2]).astype(np.uint8).tobytes()
    if fmt == 6:
        px = _tiles(a.astype(np.uint8), W, H, 4, 4).reshape(H // 4, W // 4, 16, 4)
        ar = np.stack([px[..., 3], px[..., 0]], -1); gb = np.stack([px[..., 1], px[..., 2]], -1)
        return np.stack([ar, gb], 2).tobytes()
    if fmt == 14 and t.get('rgba'):
        return cmpr_rgba(a.astype(np.float64), W, H)
    if fmt == 14 and t.get('color'):
        return cmpr_color(a[..., :3].astype(np.float64), W, H)
    if fmt == 14:  # CMPR, grayscale-oriented: fixed palette white/black/2-3/1-3 per block
        i = (r * 30 + g * 59 + b_ * 11) // 100
        lv = np.array([255, 0, 170, 85])
        idx = np.abs(i[..., None] - lv).argmin(-1)  # (H,W)
        t = idx.reshape(H // 8, 2, 4, W // 8, 2, 4).transpose(0, 3, 1, 4, 2, 5).reshape(-1, 16)
        bits = np.zeros(len(t), np.uint32)
        for k in range(16): bits |= (t[:, k].astype(np.uint32) << (30 - 2 * k))
        out = np.zeros((len(t), 8), np.uint8)
        out[:, 0] = 0xff; out[:, 1] = 0xff
        out[:, 4] = bits >> 24; out[:, 5] = bits >> 16 & 255; out[:, 6] = bits >> 8 & 255; out[:, 7] = bits & 255
        return out.tobytes()
    raise ValueError('unsupported fmt %d' % fmt)


def _565(c):
    c = np.clip(np.rint(c), 0, 255).astype(np.int32)
    return (c[..., 0] * 31 + 127) // 255 << 11 | (c[..., 1] * 63 + 127) // 255 << 5 | (c[..., 2] * 31 + 127) // 255

def _un565(v):
    return np.stack([(v >> 11 & 31) * 255 // 31, (v >> 5 & 63) * 255 // 63, (v & 31) * 255 // 31], -1).astype(np.float64)

def cmpr_color(rgb, W, H):
    """DXT1 4-colour blocks, CMPR tile order (8x8 of 2x2 sub-blocks)."""
    blk = rgb.reshape(H // 8, 2, 4, W // 8, 2, 4, 3).transpose(0, 3, 1, 4, 2, 5, 6).reshape(-1, 16, 3)
    mean = blk.mean(1, keepdims=True)
    cen = blk - mean
    cov = np.einsum('nki,nkj->nij', cen, cen)
    v = np.ones((len(blk), 3))
    for _ in range(8):
        v = np.einsum('nij,nj->ni', cov, v); v /= np.linalg.norm(v, axis=1, keepdims=True) + 1e-9
    proj = np.einsum('nki,ni->nk', cen, v)
    lo = mean[:, 0] + v * proj.min(1, keepdims=True); hi = mean[:, 0] + v * proj.max(1, keepdims=True)
    c0, c1 = _565(hi), _565(lo)
    sw = c0 < c1; c0, c1 = np.where(sw, c1, c0), np.where(sw, c0, c1)
    eq = c0 == c1
    c1 = np.where(eq & (c1 > 0), c1 - 1, c1); c0 = np.where(eq & (c1 == 0) & (c0 == 0), 1, c0)
    A, B = _un565(c0), _un565(c1)
    pal = np.stack([A, B, (2 * A + B) / 3, (A + 2 * B) / 3], 1)
    idx = ((blk[:, :, None, :] - pal[:, None, :, :]) ** 2).sum(-1).argmin(-1).astype(np.uint32)
    bits = np.zeros(len(blk), np.uint32)
    for k in range(16): bits |= idx[:, k] << (30 - 2 * k)
    out = np.zeros((len(blk), 8), np.uint8)
    out[:, 0] = c0 >> 8; out[:, 1] = c0 & 255; out[:, 2] = c1 >> 8; out[:, 3] = c1 & 255
    out[:, 4] = bits >> 24; out[:, 5] = bits >> 16 & 255; out[:, 6] = bits >> 8 & 255; out[:, 7] = bits & 255
    return out.tobytes()


def cmpr_rgba(rgba, W, H):
    """CMPR with 1-bit alpha: blocks containing transparent texels use 3-colour mode (index 3 = clear)."""
    blk = rgba.reshape(H // 8, 2, 4, W // 8, 2, 4, 4).transpose(0, 3, 1, 4, 2, 5, 6).reshape(-1, 16, 4)
    out = bytearray(len(blk) * 8)
    col = np.frombuffer(cmpr_color(rgba[..., :3].copy(), W, H), np.uint8).reshape(-1, 8)
    for n, bk in enumerate(blk):
        op = bk[:, 3] >= 128
        if op.all(): out[n * 8:n * 8 + 8] = col[n].tobytes(); continue
        if not op.any(): out[n * 8:n * 8 + 8] = bytes([0, 0, 0, 0, 255, 255, 255, 255]); continue
        c = bk[op, :3]; m = c.mean(0); cen = c - m
        u, s_, vt = np.linalg.svd(cen, full_matrices=False); v = vt[0]
        pr = cen @ v; lo, hi = m + v * pr.min(), m + v * pr.max()
        c0, c1 = int(_565(lo)), int(_565(hi))
        if c0 > c1: c0, c1 = c1, c0
        p0, p1 = _un565(np.array(c0)), _un565(np.array(c1)); pal = np.stack([p0, p1, (p0 + p1) / 2])
        bits = 0
        for k in range(16):
            ix = 3 if not op[k] else int(np.argmin(((pal - bk[k, :3]) ** 2).sum(1)))
            bits |= ix << (30 - 2 * k)
        out[n * 8:n * 8 + 8] = bytes([c0 >> 8, c0 & 255, c1 >> 8, c1 & 255]) + bits.to_bytes(4, 'big')
    return bytes(out)
