import sys,glob,os,re;sys.path.insert(0,'tools')
from dlg import *
segs={};labels={}
for f in sorted(glob.glob('ext/files/dlg/*_int.bin')):
  if 'bak' in f: continue
  d=open(f,'rb').read(); nm=os.path.basename(f)[:-8]
  for r in parse(d):
    for ln in r['ans'].split('\n'):
      for seg in segments(ln):
        if seg.startswith(chr(92)): continue
        t=strip(seg)
        segs.setdefault(t,nm)
  for o,s,t in label_fields(d): labels.setdefault(strip(t)[:-3],nm)
open('text/jp/dlg_seg.txt','w',encoding='utf-8').write('\n'.join('%s\t%s'%(v,k) for k,v in segs.items()))
open('text/jp/dlg_label.txt','w',encoding='utf-8').write('\n'.join('%s\t%s'%(v,k) for k,v in labels.items()))
st={}
for f in sorted(glob.glob('ext/files/movie/story*.txt')):
  if f.endswith('e.txt'): continue
  for ln in open(f,'rb').read().decode('cp932').splitlines():
    p=ln.split('\t')
    if len(p)>=5 and p[4].strip():
      t=strip(p[4].rstrip('*'))
      st.setdefault(t,os.path.basename(f))
open('text/jp/story_sub.txt','w',encoding='utf-8').write('\n'.join('%s\t%s'%(v,k) for k,v in st.items()))
print(len(segs),len(labels),len(st))
