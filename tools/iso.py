"""GameCube ISO rebuild helper: copy orig.iso then rewrite changed files (relocating to free space if grown)."""
import struct, shutil

def read_fst(f):
    f.seek(0x420); dol_off, fst_off, fst_sz = struct.unpack('>III', f.read(12))
    f.seek(fst_off); fst = bytearray(f.read(fst_sz))
    n = struct.unpack('>I', fst[8:12])[0]
    strt = n * 12
    def nm(o): return fst[strt + o:fst.index(b'\0', strt + o)].decode('cp932')
    paths = {}
    def walk(i, end, pre):
        while i < end:
            w0, a, s = struct.unpack('>III', fst[i * 12:i * 12 + 12])
            name = nm(w0 & 0xffffff)
            if w0 >> 24:
                walk(i + 1, s, pre + name + '/'); i = s
            else:
                paths[pre + name] = i; i += 1
    walk(1, n, '')
    return dol_off, fst_off, fst, paths

def layout(fst, paths):
    return sorted((struct.unpack('>II', fst[i * 12 + 4:i * 12 + 12]), p) for p, i in paths.items())

def build(orig, dst, files, dol_bytes=None, disc_size=1459978240):
    shutil.copyfile(orig, dst)
    f = open(dst, 'r+b')
    dol_off, fst_off, fst, paths = read_fst(f)
    ents = layout(fst, paths)
    # free gaps between files (and the dol region if dol relocated)
    occupied = [(o, o + s) for (o, s), p in ents if p not in files]
    occupied.append((0, fst_off + len(fst)))
    if dol_bytes is None:
        pass
    occupied.sort()
    gaps = []
    cur = 0
    for a, b in occupied:
        if a > cur: gaps.append([cur, a])
        cur = max(cur, b)
    if cur < disc_size: gaps.append([cur, disc_size])
    def alloc(size):
        for g in gaps:
            st = (g[0] + 31) & ~31
            if g[1] - st >= size:
                g[0] = st + size
                return st
        raise RuntimeError('no space for %d' % size)
    # place big files first
    for p, data in sorted(files.items(), key=lambda kv: -len(kv[1])):
        i = paths[p]
        w0 = struct.unpack('>I', fst[i * 12:i * 12 + 4])[0]
        o = alloc(len(data))
        f.seek(o); f.write(data)
        struct.pack_into('>III', fst, i * 12, w0, o, len(data))
    if dol_bytes is not None:
        f.seek(dol_off); f.write(dol_bytes)  # dol size unchanged (in-place edits)
    f.seek(fst_off); f.write(fst)
    f.close()
