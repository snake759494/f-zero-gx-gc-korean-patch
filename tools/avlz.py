"""Amusement Vision LZ (.lz): 8-byte header (LE comp size incl header? , LE raw size) + Okumura LZSS."""
import struct, sys
def decompress(d):
    csz, rsz = struct.unpack('<II', d[:8])
    src = d[8:]; out = bytearray(); win = bytearray(b'\0'*4096); r = 0xFEE
    i = 0; flags = 0
    while len(out) < rsz and i < len(src):
        flags >>= 1
        if not flags & 0x100:
            flags = src[i] | 0xFF00; i += 1
        if flags & 1:
            c = src[i]; i += 1; out.append(c); win[r] = c; r = (r+1) & 0xFFF
        else:
            a, b = src[i], src[i+1]; i += 2
            p = a | ((b & 0xF0) << 4); l = (b & 0x0F) + 3
            for k in range(l):
                c = win[(p+k) & 0xFFF]; out.append(c); win[r] = c; r = (r+1) & 0xFFF
    return bytes(out[:rsz])

def compress(raw):
    """Greedy LZSS with hash chains; compatible with decompress()."""
    N, F = 4096, 18
    out = bytearray(); n = len(raw)
    # window emulation: initial window zeros at positions; we only reference real data (plus zero prefix handled simply by ignoring)
    i = 0
    from collections import defaultdict
    heads = defaultdict(list)
    while i < n:
        flagpos = len(out); out.append(0); flag = 0
        for bit in range(8):
            if i >= n: break
            best_l, best_p = 0, 0
            if i + 2 < n:
                key = raw[i:i+3]
                cands = heads.get(key)
                if cands:
                    for j in reversed(cands[-64:]):
                        if i - j >= N - F: break
                        l = 3
                        while l < F and i + l < n and raw[j+l] == raw[i+l]: l += 1
                        if l > best_l:
                            best_l, best_p = l, j
                            if l == F: break
            if best_l >= 3:
                p = (best_p + 0xFEE) & 0xFFF
                out += bytes([p & 0xFF, ((p >> 4) & 0xF0) | (best_l - 3)])
                for k in range(best_l):
                    if i + k + 2 < n: heads[raw[i+k:i+k+3]].append(i+k)
                i += best_l
            else:
                flag |= 1 << bit; out.append(raw[i])
                if i + 2 < n: heads[raw[i:i+3]].append(i)
                i += 1
        out[flagpos] = flag
    return struct.pack('<II', len(out), n) + bytes(out)

if __name__ == '__main__':
    d = open(sys.argv[2], 'rb').read()
    open(sys.argv[3], 'wb').write(decompress(d) if sys.argv[1] == 'd' else compress(d))

def compress_opt(raw, chain=256):
    """Optimal-parse LZSS (min bits: literal 9, match 17). Compatible with decompress()."""
    N, F = 4096, 18
    n = len(raw); from collections import defaultdict
    heads = defaultdict(list); ML = [0] * n; MP = [0] * n
    for i in range(n):
        if i + 2 < n:
            key = raw[i:i + 3]; c = heads[key]; bl = bp = 0
            for j in reversed(c[-chain:]):
                if i - j >= N - F: break
                l = 3
                while l < F and i + l < n and raw[j + l] == raw[i + l]: l += 1
                if l > bl:
                    bl, bp = l, j
                    if l == F: break
            ML[i] = bl; MP[i] = bp; c.append(i)
    cost = [0] * (n + 1); ch = [0] * n
    for i in range(n - 1, -1, -1):
        best = 9 + cost[i + 1]; b = 1
        for l in range(3, ML[i] + 1):
            v = 17 + cost[i + l]
            if v < best: best, b = v, l
        cost[i] = best; ch[i] = b
    out = bytearray(); i = 0
    while i < n:
        fp = len(out); out.append(0); flag = 0
        for bit in range(8):
            if i >= n: break
            l = ch[i]
            if l >= 3:
                p = (MP[i] + 0xFEE) & 0xFFF
                out += bytes([p & 0xFF, ((p >> 4) & 0xF0) | (l - 3)]); i += l
            else:
                flag |= 1 << bit; out.append(raw[i]); i += 1
        out[fp] = flag
    return struct.pack('<II', len(out), n) + bytes(out)
