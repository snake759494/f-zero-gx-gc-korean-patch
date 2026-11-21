import capstone
md=capstone.Cs(capstone.CS_ARCH_PPC,capstone.CS_MODE_32|capstone.CS_MODE_BIG_ENDIAN)
md.skipdata=True
def disasm(code,addr):
    return list(md.disasm(code,addr))
def dol_ins():
    d=open('ext/sys/main.dol','rb').read()
    out=[]
    for off,addr,sz in [(0x100,0x80003100,0x24e0),(0x25e0,0x800055e0,0x89f60)]:
        out+=disasm(d[off:off+sz],addr)
    return out
