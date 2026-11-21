"""fnt_asc_24x24.bin: 1387 glyphs, 24x24 I4 tiled (3x3 tiles of 8x8), 288 bytes each."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
G = 288
def get(d, i):
    b = d[i*G:(i+1)*G]; a = np.zeros((24, 24), np.uint8)
    for t in range(9):
        tb = b[t*32:t*32+32]; px = []
        for x in tb: px += [x >> 4, x & 15]
        a[(t//3)*8:(t//3)*8+8, (t%3)*8:(t%3)*8+8] = np.array(px, np.uint8).reshape(8, 8)
    return a
def put(d, i, a):
    out = bytearray()
    for t in range(9):
        blk = a[(t//3)*8:(t//3)*8+8, (t%3)*8:(t%3)*8+8].flatten()
        for k in range(0, 64, 2): out.append((int(blk[k]) << 4) | int(blk[k+1]))
    d[i*G:(i+1)*G] = out
_cache = {}
def render(ch, path, size=21, box=(1, 1, 23, 23), weight_thicken=0, scale=4, yoff=0):
    key = (path, size*scale)
    if key not in _cache: _cache[key] = ImageFont.truetype(path, size*scale)
    f = _cache[key]
    W = 24*scale
    im = Image.new('L', (W, W), 0); dr = ImageDraw.Draw(im)
    l, t, r, b = dr.textbbox((0, 0), ch, font=f)
    x = (W - (r - l))/2 - l; y = (W - (b - t))/2 - t + yoff*scale
    dr.text((x, y), ch, fill=255, font=f)
    im = im.resize((24, 24), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32)/255.0
    a = np.clip(a*1.15, 0, 1)
    return np.round(a*15).astype(np.uint8)
