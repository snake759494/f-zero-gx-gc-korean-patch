"""dlg/*_int.bin : 16 records of 0x138 (label text at fixed field, u16 answer ptr at +0x136), answers = NUL strings."""
import struct, re, glob, os
R = 0x138
CODE = re.compile(r'(\\[a-z][0-9.]*)')
FURI = re.compile(r'\[[^\]]*\]')
def parse(d):
    recs = []
    for r in range(16):
        rec = d[r*R:(r+1)*R]
        p = struct.unpack('>H', rec[0x136:0x138])[0]
        e = d.index(b'\0', p)
        recs.append({'ptr': p, 'ans': d[p:e].decode('cp932')})
    return recs
def label_fields(d):
    """SJIS label text fields inside records: (abs offset, slot, text)"""
    out = []
    for r in range(16):
        rec = d[r*R:(r+1)*R]
        for m in re.finditer(rb'[^\x00]+', rec[:0x136]):
            s = m.group()
            if not re.search(rb'[\x81-\x9f\xe0-\xef][\x40-\xfc]', s) or s.endswith(b'<n>') is False: continue
            try: t = s.decode('cp932')
            except UnicodeDecodeError: continue
            if not t.endswith('<n>') or 'int_' in t: continue
            j = m.end()
            while j < 0x136 and rec[j] == 0: j += 1
            out.append((r*R + m.start(), j - m.start(), t))
    return out
def split_lines(ans):
    """answer -> list of (prefix_codes, text) per display line; text excludes codes"""
    res = []
    for ln in ans.split('\n'):
        res.append(ln)
    return res
def strip(t):
    return FURI.sub('', t)
def segments(line):
    """split a line into code tokens and text tokens"""
    return [x for x in CODE.split(line) if x != '']
