#!/usr/bin/env python3
"""Generate VERDANT Study 07: vine weight, support, wind, clearance and bloom."""
from pathlib import Path
from PIL import Image,ImageDraw
from generate_climber_reference_sheets import (
 W,H,BG,PANEL,INK,MUTED,ACCENT,LEAF,LEAF_L,STEM,STEM_OLD,
 font,line,wrapped,title,draw_leaf,draw_solandra_flower,draw_pipe_flower)

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"references"/"botanical"/"vine_weight_wind_bloom_reference_2400x1800.png"
RED=(160,55,45); GOLD=(202,150,51); GREEN=(55,104,70); BLUE=(52,105,125); WIRE=(151,158,151)


def bezier(p0,p1,p2,p3,n=36):
 pts=[]
 for i in range(n+1):
  t=i/n; u=1-t
  pts.append((u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0],u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]))
 return pts

def branch(d,pts,color,width): line(d,pts,INK,width+4); line(d,pts,color,width)

def panel(d,box,head,sub):
 d.rounded_rectangle(box,radius=22,fill=PANEL,outline=(150,151,141),width=3)
 x,y,_,_=box; d.text((x+25,y+18),head,font=font(21,True,True),fill=ACCENT); d.text((x+25,y+52),sub,font=font(17),fill=MUTED)

def label(d,xy,text,color=INK): d.text(xy,text,font=font(15,True,True),fill=color)

def support_panel(d):
 panel(d,(70,300,800,910),"A / SUPPORT-STATE FIRST","Classify each run before shaping it")
 # support line and valid bound helix
 line(d,[(130,430),(720,430)],WIRE,22); label(d,(125,375),"BOUND / TWINING")
 px,py=145,403
 for i in range(17):
  x=145+i*32; y=430+18*((i%4)-1.5)/1.5
  if i: line(d,[(px,py),(x,y)],STEM,8)
  px,py=x,y
 d.text((128,468),"helix exists only while touching support",font=font(16),fill=MUTED)
 # valid bridge sag
 label(d,(125,540),"BRIDGE / TWO ANCHORS")
 line(d,[(140,590),(140,650)],WIRE,16); line(d,[(715,590),(715,650)],WIRE,16)
 p=bezier((145,600),(300,680),(550,680),(710,600)); branch(d,p,STEM_OLD,11)
 d.text((128,688),"sag grows with chord length + flexibility",font=font(16),fill=MUTED)
 # one anchor hanging
 label(d,(125,760),"FREE / ONE ANCHOR")
 line(d,[(150,806),(310,806)],WIRE,16)
 p=bezier((300,806),(410,805),(455,865),(470,880)); branch(d,p,STEM,8)
 d.line((505,785,710,785),fill=RED,width=6); d.line((505,785,710,730),fill=RED,width=6)
 label(d,(500,835),"NO LONG STRAIGHT SPEAR",RED)

def gravity_panel(d):
 panel(d,(830,300,1640,910),"B / GRAVITY BY BRANCH ORDER","Same span, different diameter and age")
 y0=430
 specs=[("OLD PRIMARY",.08,17,STEM_OLD),("SECONDARY",.18,11,STEM),("TERTIARY",.32,7,GREEN),("SEARCHING TIP",.46,4,LEAF_L)]
 for i,(name,sag,w,c) in enumerate(specs):
  y=y0+i*105; line(d,[(910,y-8),(910,y+25)],WIRE,12); line(d,[(1550,y-8),(1550,y+25)],WIRE,12)
  depth=150*sag
  p=bezier((915,y),(1090,y+depth),(1370,y+depth),(1545,y)); branch(d,p,c,w)
  label(d,(880,y+42),name,c)
 d.rounded_rectangle((880,835,1585,885),radius=10,fill=(244,240,226),outline=ACCENT,width=2)
 d.text((895,849),"bridge: lerp(P0,P1) − up × 4·sag·t·(1−t)",font=font(17,True,True),fill=INK)

def wind_panel(d):
 panel(d,(70,940,800,1660),"C / COHERENT WIND WEIGHTS","Motion increases outward; branch phase stays shared")
 # trunk and branch hierarchy
 p=bezier((250,1555),(250,1390),(300,1210),(390,1055)); branch(d,p,STEM_OLD,17)
 laterals=[bezier((285,1370),(390,1320),(485,1270),(650,1260)),bezier((320,1245),(420,1160),(535,1120),(690,1090)),bezier((360,1130),(440,1050),(520,1015),(610,1000))]
 for j,q in enumerate(laterals):
  branch(d,q,GREEN,10-j*2)
  for i,(x,y) in enumerate(q[8::7]): draw_leaf(d,x,y,54,28,-.45 if i%2 else 2.5,"solandra",color=LEAF_L if i>2 else LEAF)
 # motion arrows
 for x,y,l in [(285,1450,15),(420,1300,35),(585,1170,58),(690,1075,85)]:
  d.line((x,y,x+l,y-18),fill=BLUE,width=5); d.polygon([(x+l,y-18),(x+l-14,y-25),(x+l-10,y-8)],fill=BLUE)
 d.rounded_rectangle((105,1010,245,1160),radius=12,fill=(245,241,228),outline=MUTED,width=2)
 label(d,(125,1028),"WEIGHT")
 d.text((125,1062),"primary 0.00–0.05\nsecondary 0.05–0.15\ntertiary 0.20–0.45\nleaf/tip 0.40–1.00",font=font(15),fill=INK,spacing=6)
 wrapped(d,(105,1580),"Use one low-frequency phase per branch family. Never give each leaf or spline independent jitter.",font(17),MUTED,640,5)

def clearance_bloom_panel(d):
 panel(d,(830,940,1640,1660),"D / CLEARANCE + BLOOM","Mass the edges; keep the passage believable")
 # opening frame
 d.rounded_rectangle((920,1080,1540,1580),radius=8,outline=WIRE,width=26)
 # central clearance
 d.rounded_rectangle((1110,1240,1350,1580),radius=18,outline=RED,width=4)
 for y in range(1240,1580,18): d.line((1110,y,1128,y+9),fill=RED,width=2); d.line((1332,y+9,1350,y),fill=RED,width=2)
 label(d,(1120,1592),"1.5 m × 2.2 m WOODY-STEM EXCLUSION",RED)
 # weighted masses at corners and head
 for side in (-1,1):
  anchor=990 if side<0 else 1470
  for k in range(5):
   end=anchor+side*(120+k*18)
   p=bezier((anchor,1120+k*15),(anchor+side*35,1190),(end,1280+k*35),(end+side*15,1390+k*30))
   branch(d,p,STEM if k%2 else STEM_OLD,8 if k<2 else 5)
   for i,(x,y) in enumerate(p[9::9]): draw_leaf(d,x,y,46,25,-.5 if side>0 else 2.6,"solandra",color=LEAF)
 # head drapes and flowers
 for k in range(9):
  x=970+k*63; depth=70+(k%3)*34
  p=bezier((x,1100),(x+10,1140),(x-20,1170+depth),(x+8,1220+depth)); branch(d,p,GREEN,5)
  if k%2==0: draw_solandra_flower(d,x+8,1210+depth,.46,0.05)
  else: draw_leaf(d,x+6,1200+depth,48,43,1.4,"aristolochia",color=LEAF)
 draw_pipe_flower(d,1010,1420,.45,-.15); draw_pipe_flower(d,1470,1370,.45,.15)
 label(d,(875,1008),"THICK STEMS: OUTSIDE"); label(d,(1200,1008),"LEAVES / FLOWERS: MAY BRUSH EDGE",GREEN)

def sidebar(d):
 d.rounded_rectangle((1675,300,2325,1660),radius=22,fill=(244,241,230),outline=ACCENT,width=3)
 d.text((1710,330),"IMPLEMENTATION GATES",font=font(21,True,True),fill=ACCENT)
 items=[
  ("1 / SUPPORT","Bound: conform to support. Bridge: sag between two anchors. Free: inherit tangent, then relax down. Search: only distal 0.35–0.60 m may rise."),
  ("2 / SAG","Any unsupported run beyond 0.75 m visibly droops. Beyond 1.5 m it cannot stay lateral or rise as a straight rod."),
  ("3 / HELIX","Generate a helix around an actual support centerline only. Stop the helix at detachment; never coil through free space."),
  ("4 / CLEARANCE","Keep woody stems out of the central 1.5 m wide × 2.2 m high passage. Leaves, flowers and a few flexible tips may intrude 0.10–0.25 m at edges."),
  ("5 / CANOPY","Reduce visible line count 25–40%; replace it with 3–5 overlapping foliage layers. Old branch hierarchy should be sensed, not diagrammed."),
  ("6 / SOLANDRA BLOOM","Hero trellis target: 20–35 open cups plus 30–50 buds/aging blooms across the whole frame. Put 60% near head/corners and warmth-facing growth."),
  ("7 / PIPE FLOWERS","Use 12–20 total; conceal roughly 70% below the leaf curtain. Concentrate the deliberately visible mutation-biased examples near doorway warmth."),
 ]
 y=385
 for head,body in items:
  d.text((1710,y),head,font=font(18,True,True),fill=GOLD); y=wrapped(d,(1710,y+30),body,font(17),INK,555,5)+20
 d.line((1710,1450,2290,1450),fill=MUTED,width=2)
 wrapped(d,(1710,1470),"All distances and counts are production heuristics, not measured botanical constants. Tune in Play mode, but preserve the state logic.",font(17),MUTED,555,6)
 d.text((1710,1608),"NO STRAIGHT FREE SPEARS / NO FREE-SPACE COILS",font=font(15,True,True),fill=RED)

def main():
 im=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(im)
 title(d,"07","VINE WEIGHT / WIND / BLOOM","Support-state curves / gravity relaxation / coherent motion / playable overgrowth")
 support_panel(d); gravity_panel(d); wind_panel(d); clearance_bloom_panel(d); sidebar(d)
 OUT.parent.mkdir(parents=True,exist_ok=True); im.save(OUT,optimize=True); print(OUT.relative_to(ROOT))

if __name__=="__main__": main()
