"""Non-REL text: dlg interviews, story subtitles."""
import glob, os, struct
from dlg import *
def _load(name):
    jp = [l.split('\t', 1)[1] for l in open('text/jp/%s.txt' % name, encoding='utf-8').read().split('\n')]
    m = {}
    for l in open('text/ko/%s.txt' % name, encoding='utf-8').read().split('\n'):
        if '	' not in l: continue
        n, ko = l.split('\t', 1)
        if ko: m[jp[int(n) - 1]] = ko
    return m
def _all():
    return _load('dlg_seg'), _load('dlg_label'), _load('story_sub')
def texts(tr):
    import gmo
    a, b, c = _all(); return list(a.values()) + list(b.values()) + list(c.values()) + gmo.texts()
def build(tr, enc, report):
    import gmo
    seg, lab, sub = _all(); out = gmo.build(enc, report)
    for f in sorted(glob.glob('ext/files/dlg/*_int.bin')):
        if 'bak' in f: continue
        d = bytearray(open(f, 'rb').read()); nm = os.path.basename(f)
        for o, s, t in label_fields(d):
            k = lab.get(strip(t)[:-3])
            if k is None: continue
            b = enc.enc(k) + b'<n>'
            if len(b) + 1 > s: report.append('OVER dlg label %s %s' % (nm, k)); continue
            d[o:o + s] = b + b'\0' * (s - len(b))
        recs = parse(d); body = bytearray(); base = 0x1380
        for i, r in enumerate(recs):
            lines = []
            for ln in r['ans'].split('\n'):
                parts = []
                for sg in segments(ln):
                    if sg.startswith('\\'): parts.append(sg.encode('cp932')); continue
                    k = seg.get(strip(sg))
                    if k is None:
                        report.append('MISS dlg %s %s' % (nm, sg)); parts.append(sg.encode('cp932')); continue
                    parts.append(enc.enc(k))
                lines.append(b''.join(parts))
            struct.pack_into('>H', d, i * R + 0x136, base + len(body))
            body += b'\n'.join(lines) + b'\0'
        out['dlg/' + nm] = bytes(d[:base]) + bytes(body)
    for f in sorted(glob.glob('ext/files/movie/story*.txt')):
        if f.endswith('e.txt'): continue
        res = []
        for ln in open(f, 'rb').read().decode('cp932').split('\n'):
            p = ln.split('\t'); bp = [x.encode('cp932') for x in p]
            if len(p) >= 5 and p[4].strip():
                k = sub.get(strip(p[4].rstrip('*')))
                if k is None: report.append('MISS sub %s' % ln)
                else: bp[4] = enc.enc(k) + b'*'
            res.append(b'\t'.join(bp))
        out['movie/' + os.path.basename(f)] = b'\n'.join(res)
    return out
