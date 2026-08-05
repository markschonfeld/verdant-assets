#!/usr/bin/env python3
"""Generate source-grounded VERDANT atomic-research reference sheets.

Historical anchors:
- HABS MO-1135-L Climatron photographs and data record (Library of Congress)
- Brookhaven gamma-field imagery and documented five-acre radial methodology
- IAEA mutation-breeding description

The sheets are design-intent references, not engineering or radiation-safety plans.
"""
from pathlib import Path
from math import cos, sin, pi
from random import Random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W,H=2400,1600
BG=(230,224,207); PAPER=(244,240,227); INK=(30,37,37); MUTED=(83,88,81)
RUST=(137,70,38); AMBER=(210,150,55); GREEN=(49,91,55); GREEN2=(90,126,65)
DEAD=(73,65,57); MUTANT=(103,74,92); SOIL=(72,55,39); AL=(165,173,166); AL_D=(86,98,99)
GLASS=(139,182,180,112); ACRYLIC=(178,198,187,120); RUBBER=(35,39,37); PUTTY=(180,171,137)
OUT=Path(__file__).resolve().parents[1]/'references'/'atomic_research'; OUT.mkdir(parents=True,exist_ok=True)
REG='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'; BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'; MONO='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
def font(n,b=False,m=False): return ImageFont.truetype(MONO if m else (BOLD if b else REG),n)
def line(d,pts,fill=INK,width=4): d.line(pts,fill=fill,width=width,joint='curve')
def poly(d,pts,fill,outline=INK,width=3):
 d.polygon(pts,fill=fill); d.line(pts+[pts[0]],fill=outline,width=width,joint='curve') if outline else None
def wrapped(d,xy,text,f,fill,maxw,spacing=5):
 words=text.split(); rows=[]; row=''
 for word in words:
  test=word if not row else row+' '+word
  if d.textbbox((0,0),test,font=f)[2]<=maxw: row=test
  else: rows.append(row); row=word
 if row: rows.append(row)
 x,y=xy
 for r in rows: d.text((x,y),r,font=f,fill=fill); y+=f.size+spacing
 return y
def title(d,k,name,sub):
 d.text((80,48),f'VERDANT / ATOMIC RESEARCH {k}',font=font(25,m=True),fill=RUST)
 d.text((80,88),name,font=font(65,b=True),fill=INK)
 d.text((84,172),sub,font=font(26),fill=MUTED); line(d,[(80,220),(2320,220)],MUTED,3)
def note(d,box,head,body,accent=RUST):
 x0,y0,x1,y1=box; d.rounded_rectangle(box,radius=16,fill=PAPER,outline=accent,width=3)
 d.text((x0+20,y0+17),head.upper(),font=font(21,b=True,m=True),fill=accent)
 wrapped(d,(x0+20,y0+52),body,font(20),INK,x1-x0-40,4)
def leader(d,anchor,elbow,label,number):
 ax,ay=anchor; ex,ey=elbow; line(d,[(ax,ay),(ex,ey)],RUST,4); d.ellipse((ax-9,ay-9,ax+9,ay+9),fill=RUST,outline=PAPER,width=2)
 d.ellipse((ex-19,ey-19,ex+19,ey+19),fill=RUST); tw=d.textbbox((0,0),str(number),font=font(20,b=True))[2]; d.text((ex-tw/2,ey-14),str(number),font=font(20,b=True),fill=PAPER)
 d.text((ex+30,ey-15),label,font=font(20,b=True,m=True),fill=RUST)
def ellipse_pt(cx,cy,rx,ry,a): return (cx+rx*cos(a),cy+ry*sin(a))

def crop(d,x,y,kind,rng,scale=1.0):
 if kind=='dead':
  col=(73,62,50); h=rng.randint(15,35)*scale; line(d,[(x,y),(x+rng.randint(-12,12),y-h)],col,max(2,int(4*scale)))
  if rng.random()<.45: line(d,[(x,y-h*.55),(x+rng.randint(-20,20),y-h*.82)],col,2)
 elif kind=='deformed':
  h=rng.randint(40,90)*scale; stem=(73,92,54); line(d,[(x,y),(x+rng.randint(-20,20),y-h)],stem,max(3,int(6*scale)))
  for q in (.35,.62,.84):
   yy=y-h*q; ww=rng.randint(18,44)*scale*(1.6 if rng.random()<.35 else 1)
   d.ellipse((x-ww,yy-ww*.45,x+ww,yy+ww*.45),fill=MUTANT,outline=stem,width=2)
 elif kind=='select':
  h=rng.randint(65,110)*scale; line(d,[(x,y),(x,y-h)],(54,105,52),max(3,int(6*scale)))
  for q in (.3,.55,.78):
   yy=y-h*q; ww=rng.randint(15,30)*scale; col=(70+rng.randint(0,45),110+rng.randint(0,45),48+rng.randint(0,35)); d.ellipse((x-ww,yy-ww*.35,x+ww,yy+ww*.35),fill=col,outline=GREEN,width=2)
  if rng.random()<.45: d.ellipse((x-9*scale,y-h-10*scale,x+9*scale,y-h+8*scale),fill=AMBER,outline=RUST,width=2)
 else:
  h=rng.randint(65,95)*scale; line(d,[(x,y),(x,y-h)],GREEN,max(3,int(5*scale)))
  for q,s in ((.35,-1),(.58,1),(.78,-1)):
   yy=y-h*q; poly(d,[(x,yy),(x+s*25*scale,yy-12*scale),(x+s*10*scale,yy+8*scale)],GREEN2,GREEN,1)

def gamma_garden():
 im=Image.new('RGB',(W,H),BG); d=ImageDraw.Draw(im); title(d,'03','GAMMA GARDEN — DAMAGE GRADIENT','Wide level-design study / Brookhaven-style radial field / source shown raised')
 d.rounded_rectangle((55,255,1815,1515),radius=26,fill=(190,187,160),outline=(137,137,124),width=3)
 # distant treeline and bunker/control house
 d.rectangle((55,255,1815,520),fill=(169,186,161))
 rng=Random(1961)
 for x in range(50,1820,35):
  hh=rng.randint(50,130); d.ellipse((x-55,470-hh,x+65,560),fill=(44+rng.randint(0,20),74+rng.randint(0,25),45),outline=None)
 d.rectangle((1380,360,1640,540),fill=(203,198,171),outline=INK,width=4); poly(d,[(1350,365),(1510,285),(1675,365)],(118,82,55),INK,4)
 d.rectangle((1440,430,1510,540),fill=(55,64,62),outline=INK,width=3); d.text((1398,552),'SOURCE CONTROL',font=font(18,b=True,m=True),fill=INK)
 # perspective circular field, rings back to front
 cx,cy=890,945
 rings=[(690,385,(67,102,51)),(565,315,(83,109,52)),(420,235,(92,77,70)),(265,148,(79,64,48)),(110,62,(65,58,51))]
 for rx,ry,col in rings:
  d.ellipse((cx-rx,cy-ry,cx+rx,cy+ry),fill=col,outline=(42,47,39),width=4)
 # concentric dirt paths
 for rx,ry in [(625,348),(492,274),(343,191),(185,103)]: d.ellipse((cx-rx,cy-ry,cx+rx,cy+ry),outline=(182,157,113),width=22)
 # radial access lanes
 for a in [i*pi/6 for i in range(12)]: line(d,[ellipse_pt(cx,cy,88,50,a),ellipse_pt(cx,cy,695,388,a)],(180,157,113),12)
 # crops placed by elliptical radius, back first
 entries=[]
 for band,(r0,r1,kind,count) in enumerate([(105,175,'dead',90),(185,320,'deformed',130),(335,500,'select',180),(515,680,'normal',210)]):
  for i in range(count):
   a=rng.random()*2*pi; rr=(r0*r0+(r1*r1-r0*r0)*rng.random())**.5
   x=cx+rr*cos(a); y=cy+rr*.56*sin(a); entries.append((y,x,kind,.72+(y-560)/1100*.55))
 for y,x,k,s in sorted(entries): crop(d,x,y,k,rng,s)
 # central shield well and raised source pole
 d.ellipse((cx-126,cy-63,cx+126,cy+63),fill=(105,107,99),outline=INK,width=5)
 d.ellipse((cx-78,cy-40,cx+78,cy+40),fill=(31,33,32),outline=(186,175,139),width=8)
 d.rectangle((cx-15,435,cx+15,cy),fill=(123,129,121),outline=INK,width=3)
 d.rounded_rectangle((cx-36,410,cx+36,470),radius=12,fill=(218,178,42),outline=INK,width=4)
 # trefoil-like warning mark
 d.ellipse((cx-8,430,cx+8,446),fill=INK); d.text((cx+52,412),'Co-60 SOURCE CAPSULE',font=font(18,b=True,m=True),fill=INK)
 # foreground fence and warning
 line(d,[(90,1370),(1760,1370)],(67,69,62),8)
 for x in range(120,1760,120): line(d,[(x,1290),(x,1460)],(67,69,62),6)
 d.rounded_rectangle((120,1320,430,1430),radius=8,fill=(223,196,61),outline=INK,width=4)
 d.text((150,1340),'RADIATION FIELD',font=font(23,b=True,m=True),fill=INK); d.text((172,1380),'ENTRY INTERLOCKED',font=font(17,b=True,m=True),fill=INK)
 # side notes
 note(d,(1840,270,2335,500),'01 / LETHAL CORE','Nearest the raised cobalt-60 source: bare soil, bleached stalks, dead seedlings, and collapsed plants. This is not monster growth; dose is too high for survival.')
 note(d,(1840,525,2335,755),'02 / DEFORMATION BAND','Gross abnormalities dominate: stunting, fasciated stems, asymmetric leaves, tumors, sterility, and wrong-season flowering. The visual language is biological damage, not magic.')
 note(d,(1840,780,2335,1010),'03 / SELECTION BAND','The useful ring: mostly viable plants with isolated changes in vigor, color, height, fruit, or disease response. Tags, stakes, sample bags, and removed specimens show active selection.')
 note(d,(1840,1035,2335,1265),'04 / CONTROL EDGE','Near-normal crops at the perimeter establish the baseline. Preserve orderly rows and species wedges so the gradient reads immediately from the overlook.')
 note(d,(1840,1290,2335,1515),'SOURCE CYCLE','Raised for exposure; lowered through the central well into a shielded below-grade vault before staff entry. Make the access interlock, warning lamps, and physical exclusion fence readable level landmarks.',AMBER)
 path=OUT/'gamma_garden_damage_gradient_wide_2400x1600.png'; im.save(path,optimize=True); return path

def hexpoly(cx,cy,r): return [(cx+r*cos(pi/6+i*pi/3),cy+r*sin(pi/6+i*pi/3)) for i in range(6)]
def climatron_glazing():
 im=Image.new('RGB',(W,H),BG); d=ImageDraw.Draw(im); title(d,'04','CLIMATRON-DERIVED HEX GLAZING','Vault surface-and-decay study / aluminium lattice + suspended glazing / HABS photographs only')
 d.rounded_rectangle((55,255,1720,1515),radius=26,fill=(205,211,199),outline=(137,137,124),width=3)
 # hex field in perspective-ish staggered grid
 centers=[]; r=175
 for row in range(5):
  for col in range(5):
   x=205+col*285+(142 if row%2 else 0); y=390+row*225
   if x<1640: centers.append((x,y,row,col))
 glass=Image.new('RGBA',im.size,(0,0,0,0)); gd=ImageDraw.Draw(glass)
 for i,(x,y,row,col) in enumerate(centers):
  pts=hexpoly(x,y,r)
  fill=ACRYLIC if (row+col)%4 else GLASS
  gd.polygon(pts,fill=fill,outline=(83,116,112,210),width=4)
 im=Image.alpha_composite(im.convert('RGBA'),glass).convert('RGB'); d=ImageDraw.Draw(im)
 # edges, aluminum tubes, nodes and tension rods
 edges=set()
 for x,y,row,col in centers:
  pts=hexpoly(x,y,r)
  for a,b in zip(pts,pts[1:]+pts[:1]):
   key=tuple(sorted(((round(a[0]),round(a[1])),(round(b[0]),round(b[1]))))); edges.add(key)
 for a,b in edges:
  line(d,[a,b],AL_D,18); line(d,[(a[0]-2,a[1]-3),(b[0]-2,b[1]-3)],AL,7)
 for x,y,row,col in centers:
  # central glazing spider and tension rods to corners
  d.ellipse((x-19,y-19,x+19,y+19),fill=AL,outline=INK,width=3)
  for p in hexpoly(x,y,r*.82): line(d,[(x,y),p],(112,119,112),3)
 # node bosses
 nodes=set()
 for x,y,_,_ in centers:
  for p in hexpoly(x,y,r): nodes.add((round(p[0]),round(p[1])))
 for x,y in nodes:
  d.ellipse((x-22,y-16,x+22,y+16),fill=AL,outline=INK,width=3); d.ellipse((x-7,y-6,x+7,y+6),fill=AL_D)
 # selected panel: crazing, gasket, putty repair, broken section, growth
 sx,sy=1060,840
 for a in range(0,360,28):
  ang=a*pi/180; p0=(sx+30*cos(ang),sy+20*sin(ang)); p1=(sx+105*cos(ang+.12),sy+70*sin(ang+.12)); line(d,[p0,p1],(105,129,124),2)
 # replacement pane gasket and retaining clips
 hx,hy=490,840; hp=hexpoly(hx,hy,r*.88); line(d,hp+[hp[0]],RUBBER,14)
 for i,p in enumerate(hp):
  if i%2==0: d.rounded_rectangle((p[0]-25,p[1]-10,p[0]+25,p[1]+10),radius=5,fill=AL,outline=INK,width=2)
 # broken top-right hex with jagged void
 bx,by=1485,615; jag=[(1375,560),(1430,490),(1505,515),(1545,470),(1610,550),(1580,640),(1500,610),(1450,670),(1385,640)]
 poly(d,jag,(218,226,215), (75,106,102),4)
 for pts in [[(1430,492),(1482,555),(1505,515)],[(1482,555),(1540,590),(1580,640)],[(1482,555),(1450,670)]]: line(d,pts,(66,95,91),3)
 stems=[[(1475,650),(1510,575),(1590,525)],[(1475,650),(1550,720),(1650,700)],[(1480,650),(1410,720),(1360,785)]]
 for pts in stems: line(d,pts,GREEN,11)
 for x,y in [(1590,525),(1650,700),(1360,785),(1538,710),(1430,700)]: d.ellipse((x-28,y-14,x+28,y+14),fill=GREEN2,outline=GREEN,width=2)
 # mineral tracks and algae at lower edges
 for x,y in [(780,1020),(1070,1180),(500,1050),(1330,980)]:
  line(d,[(x,y),(x+8,y+105),(x-2,y+180)],(139,129,89),5); line(d,[(x+10,y),(x+18,y+120)],(102,125,83),3)
 # callout leaders
 leader(d,(370,705),(1770,350),'ALUMINIUM SPACE FRAME',1)
 leader(d,(820,555),(1770,620),'SUSPENDED GLAZING LAYER',2)
 leader(d,(490,840),(1770,890),'REPLACEMENT PANE',3)
 leader(d,(1485,610),(1770,1160),'FAILURE + GROWTH',4)
 note(d,(1800,270,2340,515),'01 / FRAME LANGUAGE','HABS shows large aluminium compression tubes, slender tension rods, circular nodes, and a separate suspended glazing network. Preserve the airy double-layer hierarchy; do not turn it into a heavy steel grid.')
 note(d,(1800,545,2340,790),'02 / PANEL SURFACE','Original-era rigid acrylic: soft reflections, fine crazing, slight milkiness, scratches, and amber UV aging near edges. Later repair panes can be laminated glass: clearer, greener edge, sharper fracture behavior.')
 note(d,(1800,820,2340,1065),'03 / JOINT HISTORY','Compressed black gasket plus irregular surviving putty/sealant and stamped retaining clips. Mix generations of fasteners and seals so maintenance eras remain visible without changing the settled vault geometry.')
 note(d,(1800,1095,2340,1340),'04 / DECAY LOGIC','Moisture hangs at low hex corners, then tracks down rods and tube undersides. Aluminium oxidizes dull grey-white rather than orange; reserve rust for dissimilar-steel screws, brackets, and contaminated runoff.')
 note(d,(1800,1370,2340,1555),'REFERENCE BOUNDARY','HABS MO-1135-L supplies photographs, not measured drawings. Eden Prime is a 466 m lamella vault; this sheet governs surface, repair, failure, and decay.',AMBER)
 path=OUT/'climatron_hex_glazing_decay_reference_2400x1600.png'; im.save(path,optimize=True); return path

if __name__=='__main__':
 for p in (gamma_garden(),climatron_glazing()): print(p)
