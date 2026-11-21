import sys,os;sys.path.insert(0,'tools');import avlz,tpl
from PIL import Image,ImageDraw
for f in sys.argv[1:]:
  d=avlz.decompress(open('ext/files/bmp/'+f,'rb').read())
  open('tex/'+f[:-3],'wb').write(d)
  es=[e for e in tpl.entries(d) if e]
  ims=[]
  for e in es:
    try: ims.append((e,Image.fromarray(tpl.decode(d,e),'RGBA')))
    except Exception as x: print(f,e,x)
  W=1024;x=y=rh=0;pos=[]
  for e,im in ims:
    w,h=min(im.width,512),min(im.height,256)
    if x+w>W: x=0;y+=rh+14;rh=0
    pos.append((x,y));x+=w+4;rh=max(rh,h)
  sh=Image.new('RGB',(W,y+rh+14),(60,60,90));dr=ImageDraw.Draw(sh)
  for (e,im),(x,y) in zip(ims,pos):
    sh.paste(im.crop((0,0,min(im.width,512),min(im.height,256))),(x,y+12),im.crop((0,0,min(im.width,512),min(im.height,256))));dr.text((x,y),str(e['i']),fill=(255,255,0))
  sh.save('tex/'+f[:-7]+'.png');print(f,len(es),sh.size)
