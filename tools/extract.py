"""Extract SJIS strings from REL data sections / DOL data sections -> text/strings.json"""
import struct, re, json, glob, os, sys
sys.path.insert(0, os.path.dirname(__file__))
JP = re.compile(rb'[\x81-\x9f\xe0-\xef]')
def rel_sections(d):
    ns, si = struct.unpack('>II', d[0xC:0x14])
    out = []
    for k in range(ns):
        off, sz = struct.unpack('>II', d[si+8*k:si+8*k+8])
        if off and sz and not off & 1: out.append((off, sz))
    return out
def dol_sections(d):
    offs = struct.unpack('>18I', d[0x1c:0x64]); szs = struct.unpack('>18I', d[0x9c:0xe4])
    return [(o, s) for o, s in zip(offs, szs) if o and s]
def valid(s):
    try: t = s.decode('cp932')
    except UnicodeDecodeError: return None
    if not JP.search(s): return None
    # reject strings containing control chars other than newline
    if re.search(r'[\x00-\x09\x0b-\x1f\x7f]', t): return None
    # need mostly kana/kanji/ascii printable; reject rare junk: require >= 2 fullwidth chars
    full = sum(1 for c in t if ord(c) > 0xff)
    if full < 1: return None
    if any(0xff61 <= ord(c) <= 0xff9f for c in t): return None  # halfwidth kana = likely junk
    return t
def scan(d, secs):
    res = []
    for off, sz in secs:
        seg = d[off:off+sz]; i = 0
        for m in re.finditer(rb'[^\x00]+\x00', seg):
            s = m.group()[:-1]; st = off + m.start()
            if st % 1: continue
            t = valid(s)
            if t is None: continue
            # slot = bytes until next non-zero
            j = off + m.end()
            while j < off + sz and d[j] == 0: j += 1
            res.append({'off': st, 'slot': j - st, 'len': len(s), 'jp': t})
    return res
if __name__ == '__main__':
    out = {}
    files = {'fzmain.rel': 'fzmain.rel'}
    for f in sorted(glob.glob('ext/files/*.rel')): files[os.path.basename(f)] = f
    for name, path in files.items():
        d = open(path, 'rb').read()
        out[name] = scan(d, rel_sections(d))
    d = open('ext/sys/main.dol', 'rb').read()
    out['main.dol'] = scan(d, [s for s in dol_sections(d)][2:])
    os.makedirs('text', exist_ok=True)
    json.dump(out, open('text/strings_raw.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    for k, v in out.items(): print(k, len(v), sum(len(x['jp']) for x in v))
