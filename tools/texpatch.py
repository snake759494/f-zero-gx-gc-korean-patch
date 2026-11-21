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

# ---------------- AX mode (bmp_selaf / bmp_selac / bmp_advac) ----------------
SH = 'fonts/SeoulHangangEB.ttf'
NBd = NB

def _fitfont(path, lines, w, h, maxs=60, spacing=0):
    for s in range(maxs, 6, -1):
        f = F(path, s); d = ImageDraw.Draw(Image.new('L', (1, 1)))
        bb = [d.textbbox((0, 0), l, font=f) for l in lines]
        tw = max(b[2] - b[0] for b in bb); th = sum(b[3] - b[1] for b in bb) + spacing * (len(lines) - 1)
        if tw <= w and th <= h: return f
    return F(path, 7)

def _textmask(size, lines, font, shear=0.0, spacing=0, align='center'):
    W, H = size; m = Image.new('L', (W * 2, H), 0); d = ImageDraw.Draw(m)
    bb = [d.textbbox((0, 0), l, font=font) for l in lines]
    th = sum(b[3] - b[1] for b in bb) + spacing * (len(lines) - 1); y = (H - th) / 2
    for l, b in zip(lines, bb):
        lw = b[2] - b[0]; x = W / 2 + (W - lw) / 2 if align == 'center' else W / 2
        d.text((x - b[0], y - b[1]), l, font=font, fill=255); y += b[3] - b[1] + spacing
    if shear: m = m.transform(m.size, Image.AFFINE, (1, shear, -shear * H / 2, 0, 1, 0), Image.BICUBIC)
    return m.crop((W // 2, 0, W // 2 + W, H))

def glowlabel(a, lines, glow, font=NH, shear=0.25, core=(255, 255, 255), outline=None, ow=2, pad=2, spacing=0, gr=2):
    h, w = a.shape[:2]
    f = _fitfont(font, lines, (w - 2 * pad) * (0.88 if shear else 1), h - 2 * pad, spacing=spacing)
    big = _textmask((w * 3, h * 3), lines, F(font, f.size * 3), shear, spacing * 3)
    bx = big.getbbox(); big = big.crop(bx)
    tw, th = w - 2 * pad - 2, h - 2 * pad - 2
    sc = min(th / big.height, tw / big.width * 1.0); sx = min(tw / big.width, sc * 1.45)
    nw, nh = max(1, int(big.width * sx)), max(1, int(big.height * sc))
    m = Image.new('L', (w, h), 0); m.paste(big.resize((nw, nh), Image.LANCZOS), ((w - nw) // 2, (h - nh) // 2))
    mn = np.array(m).astype(np.float32) / 255
    g = cv2.GaussianBlur(cv2.dilate(mn, np.ones((3, 3), np.uint8), iterations=gr // 2 + 1), (0, 0), gr)
    out = np.zeros((h, w, 4), np.float32)
    ga = np.clip(g * 2.2, 0, 1) * 170
    out[..., :3] = glow; out[..., 3] = ga
    if outline is not None:
        o = cv2.dilate(mn, np.ones((2 * ow + 1, 2 * ow + 1), np.uint8))
        out[..., :3] = out[..., :3] * (1 - o[..., None]) + np.array(outline) * o[..., None]
        out[..., 3] = np.maximum(out[..., 3], o * 240)
    out[..., :3] = out[..., :3] * (1 - mn[..., None]) + np.array(core) * mn[..., None]
    out[..., 3] = np.maximum(out[..., 3], mn * 240)
    return np.clip(out, 0, 255).astype(np.uint8)

CY, YE = (2, 255, 255), (255, 238, 5)
def t_saf0(a): return glowlabel(a, ['액셀 온'], CY)
def t_saf8(a): return glowlabel(a, ['카드 인'], CY)
def t_saf18(a): return glowlabel(a, ['이어받지 않음'], CY)
def t_saf19(a): return glowlabel(a, ['이어받기'], YE)
def t_saf27(a): return glowlabel(a, ['라이선스', '카드'], YE, spacing=4)
def t_saf28(a): return glowlabel(a, ['라이선스', '카드'], CY, spacing=4)
def t_saf33(a): return glowlabel(a, ['사용 안 함'], CY)
def t_saf34(a): return glowlabel(a, ['만들기'], YE)
def t_saf35(a): return glowlabel(a, ['메모리 카드도 접수 중!'], (190, 72, 144), font=SH, shear=0, outline=(176, 64, 128), ow=2, pad=5)
def t_sac26(a): return glowlabel(a, ['대전 상대 모집 중'], (223, 174, 205), font=SH, shear=0, outline=(200, 76, 165), ow=3, pad=10)

def t_adv6(a):  # "N人対戦可能" (after digit texture) -> "인 대전 가능": white text, black outline, thin white rim, on black
    h, w = a.shape[:2]; f = _fitfont(SH, ['인 대전 가능'], w - 14, h - 16)
    m = np.array(_textmask((w, h), ['인 대전 가능'], f)).astype(np.float32) / 255
    o = cv2.dilate(m, np.ones((5, 5), np.uint8)); r = cv2.dilate(m, np.ones((7, 7), np.uint8))
    v = np.clip((r - o) + m, 0, 1) * 255
    return np.dstack([v, v, v, np.full((h, w), 255.)]).astype(np.uint8)

def t_adv13(a):  # blurred shadow of the same
    h, w = a.shape[:2]; f = _fitfont(SH, ['인 대전 가능'], w - 12, h - 14)
    m = np.array(_textmask((w, h), ['인 대전 가능'], f)).astype(np.float32)
    m = cv2.GaussianBlur(cv2.dilate(m, np.ones((7, 7), np.uint8)), (0, 0), 3) * 0.8
    return np.dstack([m, m, m, np.full((h, w), 255.)]).clip(0, 255).astype(np.uint8)

def t_sac3(a):  # small radar labels, center ~ (505, 87)
    h, w = a.shape[:2]; cx, cy = 505, 87
    br = (a[..., :3].min(-1) > 190) & (a[..., 3] > 100)
    yy, xx = np.mgrid[:h, :w]
    region = (xx > 455) & (xx < 555) & ((yy < 58) | (yy > 116) | (np.abs(xx - cx) > 32)) & (yy > 40) & (yy < 132)
    m = cv2.dilate((br & region).astype(np.uint8), np.ones((5, 5), np.uint8))
    im = Image.fromarray(inpaint(a, m), 'RGBA'); g = F(GAL, 12)
    W, K = (255, 255, 255, 255), (0, 0, 0, 255)
    text(im, (cx, 44), '바디', g, W, K, anchor='ma')
    text(im, (cx, 117), '코너링', g, W, K, anchor='ma')
    vtext(im, 467, 68, '가속력', g, W, K, step=13)
    vtext(im, 542, 68, '최고속', g, W, K, step=13)
    return np.array(im)

MG, CYp, YEp, WH = (255, 0, 255, 255), (0, 255, 255, 255), (255, 255, 0, 255), (255, 255, 255, 255)
BG = (0, 0, 0, 145)

def rich(im, x, y, segs):
    d = ImageDraw.Draw(im); base = max(f.getmetrics()[0] for _, _, f in segs)
    for s, c, f in segs:
        asc = f.getmetrics()[0]; d.text((x, y + base - asc), s, font=f, fill=c)
        x += d.textlength(s, font=f)
    return x

def _clear(a, box, col=BG):
    x0, y0, x1, y1 = box; a[y0:y1, x0:x1] = col

def _title_over(a, box, s):
    x0, y0, x1, y1 = box; sub = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
    g = glowlabel(sub, [s], (200, 200, 200), pad=3)
    bg = Image.new('RGBA', (x1 - x0, y1 - y0), BG); bg.alpha_composite(Image.fromarray(g, 'RGBA'))
    a[y0:y1, x0:x1] = np.array(bg)

def t_saf3(a):  # "before you play" safety panel 592x432
    a = a.copy()
    for b in [(14, 58, 578, 90), (282, 104, 578, 188), (282, 338, 578, 424)]: _clear(a, b)
    _title_over(a, (150, 7, 445, 43), '플레이하기 전에')
    im = Image.fromarray(a, 'RGBA'); s = F(GAL, 12); m = F(NBd, 17); L = F(NH, 19)
    rich(im, 20, 64, [('안전벨트', MG, L), ('를 반드시 착용해 주세요. ', YEp, L), ('바르게 매지 않으면 시트가 움직이지 않습니다.', YEp, s)])
    rich(im, 290, 110, [('플레이 중 시트를 멈추고 싶을 때는', CYp, s)])
    rich(im, 290, 126, [('모션 스톱 버튼', MG, m), ('을 눌러 주세요.', CYp, s)])
    rich(im, 290, 150, [('플레이 전에 ', CYp, s), ('버튼', YEp, s), ('의 위치를 ', CYp, s), ('확인', YEp, s), ('해 주세요.', CYp, s)])
    rich(im, 290, 344, [('이 게임기에는 사고 방지를 위해 센서가', CYp, s)])
    rich(im, 290, 360, [('달려 있습니다. 사람이나 물체에', CYp, s)])
    rich(im, 290, 378, [('센서', MG, m), ('가 반응하면 시트가 멈춥니다.', YEp, m)])
    return np.array(im)

def t_saf4(a):  # memory card notice 268x112
    a = a.copy(); a[:] = BG; im = Image.fromarray(a, 'RGBA'); s = F(GAL, 12); L = F(NBd, 15)
    rich(im, 3, 2, [('메모리 카드', MG, s), ('를 꽂기 전에 슬롯에 이상이', CYp, s)])
    rich(im, 3, 16, [('없는지 확인해 주세요.', CYp, s)])
    rich(im, 3, 30, [('「F-ZERO GX」 외의 데이터는 넣지 않고', CYp, s)])
    rich(im, 3, 44, [('쓰는 것을 권장합니다.', CYp, s)])
    rich(im, 3, 62, [('플레이 중에 카드를 꽂거나 빼는 것은', YEp, L)])
    rich(im, 3, 84, [('절대 하지 마세요.', YEp, L)])
    return np.array(im)

def t_saf5(a):  # "GC memory card unavailable now" 268x112
    a = a.copy(); a[:] = BG; im = Image.fromarray(a, 'RGBA'); s = F(GAL, 12)
    text(im, (134, 44), '지금은 닌텐도 게임큐브', s, WH, anchor='ma')
    text(im, (134, 60), '메모리 카드를 사용할 수 없습니다.', s, WH, anchor='ma')
    return np.array(im)

def _ghost(a, rows):
    h, w = a.shape[:2]; im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); s = F(GAL, 11)
    d = ImageDraw.Draw(im); d.fontmode = '1'
    for y, l1, l2 in rows:
        d.text((w // 2, y), l1, font=s, fill=WH, anchor='ma'); d.text((w // 2, y + 12), l2, font=s, fill=WH, anchor='ma')
    return np.array(im)
def t_saf63(a): return _ghost(a, [(2, '고스트', 'OFF'), (34, '라이벌', '고스트'), (66, '머신별', '고스트'), (98, '챔피언', '고스트')])
def t_saf64(a): return _ghost(a, [(3, '스태프', '고스트')])

JOBS.update({
    'bmp_selaf.tpl.lz': {0: t_saf0, 3: t_saf3, 4: t_saf4, 5: t_saf5, 8: t_saf8, 18: t_saf18, 19: t_saf19, 27: t_saf27, 28: t_saf28, 33: t_saf33, 34: t_saf34, 35: t_saf35, 63: t_saf63, 64: t_saf64},
    'bmp_selac.tpl.lz': {3: t_sac3, 26: t_sac26},
    'bmp_advac.tpl.lz': {6: t_adv6, 13: t_adv13},
})
