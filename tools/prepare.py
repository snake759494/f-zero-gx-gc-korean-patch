"""Prepare work files from the user's own Japanese disc (GFZJ01).
python tools/prepare.py <F-Zero GX (Japan).rvz|iso> <DolphinTool.exe>
-> orig.iso, ext/, fzmain.rel, text/fontchars.txt, text/strings_f.json, text/jp/*.txt"""
import sys, os, subprocess, hashlib, json, shutil
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(W)
sys.path.insert(0, 'tools')
MD5 = '38249b82be648aaf08b42909064a957d'
src, tool = sys.argv[1], sys.argv[2]
if not os.path.exists('orig.iso'):
    if src.lower().endswith('.iso'): shutil.copyfile(src, 'orig.iso')
    else: subprocess.check_call([tool, 'convert', '-i', src, '-o', 'orig.iso', '-f', 'iso'])
h = hashlib.md5()
with open('orig.iso', 'rb') as f:
    for b in iter(lambda: f.read(1 << 22), b''): h.update(b)
if h.hexdigest() != MD5: raise SystemExit('orig.iso MD5 mismatch: ' + h.hexdigest())
if not os.path.isdir('ext'):
    subprocess.check_call([tool, 'extract', '-i', 'orig.iso', '-o', 'ext'])
import linebin
open('fzmain.rel', 'wb').write(linebin.unpack(open('ext/files/enemy_line/line__.bin', 'rb').read()))
d = open('fzmain.rel', 'rb').read()
open('text/fontchars.txt', 'w', encoding='utf-8').write(d[0x1844c0:d.index(b'\0', 0x1844c0)].decode('cp932'))
idx = json.load(open('text/index.json'))
out = {}
for name, ents in idx.items():
    p = 'fzmain.rel' if name == 'fzmain.rel' else 'ext/files/' + name
    b = open(p, 'rb').read() if os.path.exists(p) else b''
    out[name] = [{'off': o, 'slot': s, 'len': l, 'jp': b[o:o + l].decode('cp932')} for o, s, l in ents]
json.dump(out, open('text/strings_f.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
os.makedirs('text/jp', exist_ok=True)
subprocess.check_call([sys.executable, 'tools/dump_extra.py'])
print('ready')
