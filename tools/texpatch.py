"""Korean replacements for Japanese UI textures (bmp/*.tpl.lz)."""
import os, sys, math
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(__file__))
import avlz, tpl
GAL = 'fonts/Galmuri11.ttf'
NB = 'fonts/NanumSquareNeo-cBd.ttf'
NH = 'fonts/NanumSquareNeo-eHv.ttf'

def F(p, s): return ImageFont.truetype(p, s)

def text(im, xy, s, font, fill, ol=None, ow=1, anchor='la'):
    d = ImageDraw.Draw(im)
    d.text(xy, s, font=font, fill=fill, anchor=anchor, stroke_width=ow if ol else 0, stroke_fill=ol)

def vtext(im, x, y, s, font, fill, ol, ow=1, step=None):
    step = step or font.size
    for i, c in enumerate(s): text(im, (x, y + i * step), c, font, fill, ol, ow, 'ma')

def inpaint(a, mask, r=3):
    rgb = cv2.inpaint(np.ascontiguousarray(a[..., :3]), mask.astype(np.uint8) * 255, r, cv2.INPAINT_TELEA)
    al = cv2.inpaint(np.ascontiguousarray(a[..., 3]), mask.astype(np.uint8) * 255, r, cv2.INPAINT_TELEA)
    return np.dstack([rgb, al])

def t_sel35(a):  # accel / top speed labels (72x40)
    im = Image.new('RGBA', (a.shape[1], a.shape[0]), (0, 0, 0, 0)); g = F(GAL, 12)
    text(im, (2, 1), '가속', g, (255, 255, 255, 255), (0, 0, 0, 255))
    text(im, (70, 21), '최고속', g, (255, 255, 255, 255), (0, 0, 0, 255), anchor='ra')
    return np.array(im)

def t_conf0(a):  # radar labels
    h, w = a.shape[:2]
    br = (a[..., :3].min(-1) > 205) & (a[..., 3] > 100)
    yy, xx = np.mgrid[:h, :w]; c = (w / 2, h / 2)
    region = (yy < 17) | (yy > 128) | (xx < 27) | (xx > w - 27)
    m = cv2.dilate((br & region).astype(np.uint8), np.ones((5, 5), np.uint8))
    im = Image.fromarray(inpaint(a, m), 'RGBA'); g = F(GAL, 12)
    W, K = (255, 255, 255, 255), (40, 0, 40, 255)
    text(im, (w // 2, 2), '바디', g, W, K, anchor='ma')
    text(im, (w // 2, 131), '코너링', g, W, K, anchor='ma')
    vtext(im, 10, 55, '가속력', g, W, K, step=13)
    vtext(im, w - 10, 55, '최고속', g, W, K, step=13)
    return np.array(im)

def t_rac12(a):  # course-out banner
    b = a.copy(); b[:, 62:] = 0
    im = Image.fromarray(b, 'RGBA'); f = F(NH, 38)
    glow = Image.new('RGBA', im.size, (0, 0, 0, 0))
    text(glow, (182, 27), '코스 아웃!', f, (255, 0, 30, 255), (255, 0, 30, 255), 6, 'mm')
    glow = glow.filter(ImageFilter.GaussianBlur(2))
    im.alpha_composite(glow)
    text(im, (182, 27), '코스 아웃!', f, (225, 10, 35, 255), (255, 235, 235, 255), 2, 'mm')
    return np.array(im)

def t_pas1(a):  # AX course names
    h, w = a.shape[:2]; im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); f = F(NH, 19)
    names = ['소닉 오벌', '스크루 드라이브', '메테오 스트림', '실린더 웨이브', '선더 로드', '스파이럴']
    for i, s in enumerate(names):
        text(im, (w // 2, 14 + i * 28), s, f, (225, 232, 236, 255), (40, 62, 72, 255), 2, 'mm')
    return np.array(im)

def _ring(a, top, stamp):
    h, w = a.shape[:2]
    lum = a[..., :3].astype(int).mean(-1)
    blur = cv2.GaussianBlur(lum.astype(np.float32), (0, 0), 3)
    dark = (lum < blur - 14) & (a[..., 3] > 200)
    yy, xx = np.mgrid[:h, :w]
    reg = (yy < 44) & (xx > 30) & (xx < 140)
    rgb = a[..., :3].astype(int)
    x0, y0, x1, y1 = stamp
    red = (rgb[..., 0] - rgb[..., 2] > 28) & (rgb[..., 0] - rgb[..., 1] > 12) & (a[..., 3] > 200) & (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)
    m = cv2.dilate((dark & reg).astype(np.uint8), np.ones((3, 3), np.uint8)) | cv2.dilate(red.astype(np.uint8), np.ones((3, 3), np.uint8))
    out = inpaint(a, m, 4)
    im = Image.fromarray(out, 'RGBA'); f = F(NH, 15); cx, cy, R = 84, 86, 66
    n = len(top); span = 14 * (n - 1)
    for i, c in enumerate(top):
        ang = math.radians(-90 - span / 2 + 14 * i)
        x, y = cx + R * math.cos(ang), cy + R * math.sin(ang)
        g = Image.new('RGBA', (24, 24), (0, 0, 0, 0))
        text(g, (12, 12), c, f, (70, 64, 58, 255), anchor='mm')
        hl = Image.new('RGBA', (24, 24), (0, 0, 0, 0)); text(hl, (12, 13), c, f, (230, 225, 215, 170), anchor='mm')
        rot = -(math.degrees(ang) + 90)
        for layer in (hl, g):
            r = layer.rotate(rot, resample=Image.BICUBIC)
            im.alpha_composite(r, (int(x - 12), int(y - 12)))
    return np.array(im)

def t_ring_m(a): return _ring(a, '선택머신', (25, 115, 95, 155))
def t_ring_c(a): return _ring(a, '선택인물', (5, 80, 35, 135))

def t_gar3(a):  # garage radar (center ~476,50)
    h, w = a.shape[:2]; cx, cy = 476, 50
    br = (a[..., :3].min(-1) > 205) & (a[..., 3] > 100)
    yy, xx = np.mgrid[:h, :w]; r = np.hypot(xx - cx, yy - cy)
    region = (xx > 420) & (xx < 535) & ((yy < 13) | (yy > 80) | (np.abs(xx - cx) > 30))
    m = cv2.dilate((br & region).astype(np.uint8), np.ones((5, 5), np.uint8))
    im = Image.fromarray(inpaint(a, m), 'RGBA'); g = F(GAL, 12)
    W, K = (255, 255, 255, 255), (40, 0, 40, 255)
    text(im, (cx, 1), '바디', g, W, K, anchor='ma')
    text(im, (cx, 84), '코너링', g, W, K, anchor='ma')
    vtext(im, cx - 39, 36, '가속', g, W, K, step=13)
    vtext(im, cx + 39, 30, '최고속', g, W, K, step=13)
    return np.array(im)

JOBS = {
    'bmp_gar.tpl.lz': {3: t_gar3},
    'bmp_sel.tpl.lz': {35: t_sel35},
    'bmp_conf.tpl.lz': {0: t_conf0},
    'bmp_rac.tpl.lz': {12: t_rac12},
    'bmp_pas.tpl.lz': {1: t_pas1},
    'bmp_sel1w.tpl.lz': {2: t_ring_m, 3: t_ring_c},
}

SKIP = os.environ.get('TEXSKIP', '').split(',')
def build(preview=None):
    out = {}
    for fn, jobs in JOBS.items():
        if fn in SKIP: continue
        d = bytearray(avlz.decompress(open('ext/files/bmp/' + fn, 'rb').read()))
        es = tpl.entries(d)
        for i, fx in jobs.items():
            e = es[i]; a = tpl.decode(bytes(d), e); n = fx(a)
            if preview is not None: preview.append((fn, i, a, n))
            b = tpl.encode(n, e); d[e['off']:e['off'] + len(b)] = b
        import hashlib; os.makedirs('tex', exist_ok=True); hk = 'tex/cache_' + hashlib.md5(bytes(d)).hexdigest()
        if os.path.exists(hk): c = open(hk, 'rb').read()
        else: c = avlz.compress_opt(bytes(d)); open(hk, 'wb').write(c)
        o = os.path.getsize('ext/files/bmp/' + fn)
        if len(c) > o: raise SystemExit('tex too big %s %d>%d' % (fn, len(c), o))
        out['bmp/' + fn] = c
    return out

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    pv = []
    for fn, jobs in JOBS.items():
        d = open('tex/' + fn[:-3], 'rb').read(); es = tpl.entries(d)
        for i, fx in jobs.items():
            a = tpl.decode(d, es[i]); n = fx(a)
            n2 = tpl.decode(tpl.encode(n, es[i]).rjust(0) and (b'\0' * es[i]['off'] + tpl.encode(n, es[i])), dict(es[i]))
            pv.append((a, n2))
    pv = [p for p in pv if p[0].shape[0] > 100 or p[0].shape[1] > 250][:1] + pv[-2:] + [pv[2]]
    W = 1000; x = y = rh = 0; sh = Image.new('RGB', (W, 900), (255, 0, 255))
    for a, n in pv:
        for z in (a, n):
            im = Image.fromarray(z, 'RGBA')
            if x + im.width * 2 > W: x = 0; y += rh + 6; rh = 0
            im2 = im.resize((im.width * 2, im.height * 2), Image.NEAREST)
            bg = Image.new('RGBA', im2.size, (60, 20, 60, 255)); bg.alpha_composite(im2)
            sh.paste(bg.convert('RGB'), (x, y)); x += im2.width + 6; rh = max(rh, im2.height)
    sh.save('tex/preview.png')
