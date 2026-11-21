"""enemy_line/line__.bin <-> fz.main REL. XOR u32 BE with LCG (seed 0xDEADDEAD, x=x*0xB5FB6483+0x4F107, xor after update) over AV-LZ data."""
import struct, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import avlz
M, C = 0xB5FB6483, 0x4F107
def crypt(d):
    n = len(d) // 4
    w = list(struct.unpack('>%dI' % n, d[:n*4])); x = 0xDEADDEAD
    for i in range(n):
        x = (x * M + C) & 0xffffffff; w[i] ^= x
    return struct.pack('>%dI' % n, *w) + d[n*4:]
def unpack(enc): return avlz.decompress(crypt(enc))
def pack(rel): return crypt(avlz.compress(rel))
if __name__ == '__main__':
    if sys.argv[1] == 'd': open(sys.argv[3], 'wb').write(unpack(open(sys.argv[2], 'rb').read()))
    else: open(sys.argv[3], 'wb').write(pack(open(sys.argv[2], 'rb').read()))
