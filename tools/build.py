"""Build Korean ISO.  python tools/build.py [--noiso]"""
import json, glob, os, sys, struct, re, hashlib
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import font as F, linebin, iso
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(W)
FONT = 'fonts/NanumSquareNeo-cBd.ttf'
OUT_ISO = os.environ.get('OUT_ISO', os.path.join(os.path.dirname(W), 'F-Zero GX (Japan) [KOR].iso'))
TAB = open('text/fontchars.txt', encoding='utf-8').read()
# replaceable slots: hiragana, katakana, kanji
def replaceable(c):
    o = ord(c)
    return 0x3041 <= o <= 0x30f6 and c not in (chr(0x30fc), chr(0x309b), chr(0x309c)) or 0x4e00 <= o <= 0x9fff
SLOTS = [i for i, c in enumerate(TAB) if replaceable(c)]
# punctuation normalisation (Korean text -> chars present in font)
NORM = {'~': '～', '…': '…', '·': '・', '‘': '‘', '’': '’', '“': '“', '”': '”', '「': '「', '」': '」'}

def load_tr():
    """text/ko/<relname>.txt : lines 'hexoff<TAB>korean' ('|' = newline). Keyed to jp text so duplicates elsewhere follow."""
    S = json.load(open('text/strings_f.json', encoding='utf-8'))
    tr = {}
    for f in sorted(glob.glob('text/ko/*.txt')):
        name = os.path.basename(f)[:-4]
        if name in ('dlg_seg','dlg_label','story_sub'): continue
        byoff = {e['off']: e['jp'] for e in S.get(name, [])}
        for ln in open(f, encoding='utf-8').read().split('\n'):
            if not ln.strip() or ln.startswith('#'): continue
            off, ko = ln.split('\t', 1)
            ko = ko.replace('|', '\n').replace('\\t', '\t')
            if off.startswith('@'):  # location-only override
                tr['%s:%s' % (name, off[1:])] = ko; continue
            jp = byoff[int(off, 16)]
            tr[jp] = ko
    return tr

class Enc:
    def __init__(self, texts):
        used = {c for t in texts for c in t if 0xac00 <= ord(c) <= 0xd7a3}
        mf = 'text/hangul_order.txt'
        hs = open(mf, encoding='utf-8').read().strip() if os.path.exists(mf) else ''
        hs = list(hs) + sorted(used - set(hs))
        open(mf, 'w', encoding='utf-8').write(''.join(hs))
        if len(hs) > len(SLOTS): raise SystemExit('too many hangul: %d > %d' % (len(hs), len(SLOTS)))
        self.map = {h: TAB[SLOTS[i]] for i, h in enumerate(hs)}
        self.glyph = {SLOTS[i]: h for i, h in enumerate(hs)}
        print('hangul used', len(hs), '/', len(SLOTS))
    def enc(self, t):
        out = []
        for c in t:
            c = NORM.get(c, c)
            c = self.map.get(c, c)
            out.append(c)
        return ''.join(out).encode('cp932')

def patch_strings(data, entries, tr, enc, name, report):
    data = bytearray(data); n = 0
    for e in entries:
        ko = tr.get('%s:%x' % (name, e['off']), tr.get(e['jp']))
        if ko is None: continue
        b = enc.enc(ko)
        if len(b) + 1 > e['slot']:
            report.append('OVER %s:%x %d>%d %s' % (name, e['off'], len(b) + 1, e['slot'], ko)); continue
        data[e['off']:e['off'] + e['slot']] = b + b'\0' * (e['slot'] - len(b))
        n += 1
    return bytes(data), n

def dup_pass(d, entries, tr, enc, name, report):
    """patch untracked copies of already-translated strings (e.g. after 0xff padding)"""
    known = {e['off'] for e in entries}; n = 0
    for m in re.finditer(rb'(?<=[\x00\xff])[^\x00\xff]{4,}\x00+', bytes(d)):
        if m.start() in known: continue
        raw = m.group().rstrip(b'\0')
        try: t = raw.decode('cp932')
        except UnicodeDecodeError: continue
        if t not in tr: continue
        b = enc.enc(tr[t]); slot = len(m.group())
        if len(b) + 1 > slot: report.append('OVER dup %s:%x %s' % (name, m.start(), tr[t])); continue
        d[m.start():m.start() + slot] = b + b'\0' * (slot - len(b)); n += 1
    if n: print('dup', name, n)
    return n

def build_font(enc):
    d = bytearray(open('ext/files/font/fnt_asc_24x24.bin', 'rb').read())
    for idx, h in enc.glyph.items():
        F.put(d, idx, F.render(h, FONT, 22))
    return bytes(d)

def main():
    tr = load_tr()
    S = json.load(open('text/strings_f.json', encoding='utf-8'))
    import extra
    import kana
    texts = list(tr.values()) + extra.texts(tr) + [kana.A, kana.B]
    enc = Enc(texts)
    report = []; files = {}
    # RELs
    for name, entries in S.items():
        if name == 'main.dol' or not entries: continue
        src = 'fzmain.rel' if name == 'fzmain.rel' else 'ext/files/' + name
        d, n = patch_strings(open(src, 'rb').read(), entries, tr, enc, name, report)
        d = bytearray(d); n += dup_pass(d, entries, tr, enc, name, report)
        for o, t in list(kana.patch(d)):
            b = enc.enc(t); assert len(b) == len(t) * 2; d[o:o + len(b)] = b; n += 1
        d = bytes(d)
        if n == 0: continue
        if name == 'fzmain.rel':
            files['enemy_line/line__.bin'] = linebin.pack(d)
        else:
            files[name] = d
        print(name, n, 'strings')
    files.update(extra.build(tr, enc, report))
    import texpatch
    files.update(texpatch.build())
    files['font/fnt_asc_24x24.bin'] = build_font(enc)
    open('report.txt', 'w', encoding='utf-8').write('\n'.join(report))
    print('report lines', len(report))
    if '--noiso' in sys.argv: return
    iso.build('orig.iso', OUT_ISO, files)
    print('wrote', OUT_ISO)

if __name__ == '__main__':
    main()
