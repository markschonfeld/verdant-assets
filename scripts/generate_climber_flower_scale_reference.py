#!/usr/bin/env python3
"""Generate same-scale flower/leaf comparison and Unreal card transform guide."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]; CUT=ROOT/"cutouts"; OUT=ROOT/"references"/"botanical"/"climber_flower_scale_reference_2400x1800.png"
W,H=2400,1800; BG=(236,231,215); PANEL=(220,219,204); INK=(31,38,39); MUTED=(85,91,84); ACC=(135,63,31); GOLD=(196,145,51); RED=(157,54,43)
REG="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"; BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"; MONO="/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
def f(n,b=False,m=False): return ImageFont.truetype(MONO if m else BOLD if b else REG,n)
def crop_alpha(name):
 im=Image.open(CUT/name).convert("RGBA"); return im.crop(im.getbbox())
def fit_axis(im,target,axis=0):
 scale=target/(im.width if axis==0 else im.height); return im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS)
def paste(canvas,im,xy): canvas.paste(im,xy,im)
def wrap(d,xy,text,font,width,fill=MUTED):
 x,y=xy; row=""
 for word in text.split():
  test=(row+" "+word).strip()
  if d.textbbox((0,0),test,font=font)[2]<=width: row=test
  else: d.text((x,y),row,font=font,fill=fill); y+=font.size+6; row=word
 if row:d.text((x,y),row,font=font,fill=fill)
def ruler(d,x,y,cm,pxcm):
 d.line((x,y,x+cm*pxcm,y),fill=INK,width=4)
 for i in range(cm+1):
  h=24 if i%5==0 else 12; d.line((x+i*pxcm,y-h,x+i*pxcm,y+h),fill=INK,width=3 if i%5==0 else 1)
  if i%5==0:d.text((x+i*pxcm-9,y+28),str(i),font=f(15,m=True),fill=INK)
 d.text((x+cm*pxcm+18,y-9),"cm",font=f(16,True,m=True),fill=INK)
def main():
 im=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(im)
 d.text((75,55),"VERDANT / BOTANICAL STUDY 08",font=f(24,m=True),fill=ACC)
 d.text((75,110),"FLOWER SCALE LOCK",font=f(64,True),fill=INK)
 d.text((78,195),"Same biological scale / flower-body dimensions / committed-card transform",font=f(27),fill=MUTED)
 d.line((75,250,2325,250),fill=MUTED,width=3)
 d.rounded_rectangle((70,300,1160,1470),radius=24,fill=PANEL,outline=(150,151,141),width=3)
 d.rounded_rectangle((1200,300,2330,1470),radius=24,fill=PANEL,outline=(150,151,141),width=3)
 pxcm=32
 # Solandra, 18 cm leaf and 20 cm corolla body at identical scale.
 d.text((105,330),"SOLANDRA MAXIMA",font=f(28,True,m=True),fill=ACC)
 d.text((105,375),"architectural cup / normal hero corolla 18–22 cm",font=f(20),fill=MUTED)
 leaf=fit_axis(crop_alpha("solandra_maxima_leaf_flat_1024.png"),round(18*pxcm/.845),1)
 flower=fit_axis(crop_alpha("solandra_maxima_flower_open_1024.png"),round(20*pxcm/.744),0)
 paste(im,leaf,(130,500)); paste(im,flower,(295,680))
 d.text((125,1130),"leaf blade shown: 18 cm",font=f(18,True),fill=(48,91,55)); d.text((300,1020),"corolla body shown: 20 cm",font=f(18,True),fill=GOLD)
 d.line((480,660,480+20*pxcm,660),fill=RED,width=4); d.text((610,620),"20 cm flower body",font=f(17,True,m=True),fill=RED)
 ruler(d,130,1350,25,pxcm)
 # Aristolochia, 24 cm leaf and 4 cm perianth body at same scale.
 d.text((1235,330),"ARISTOLOCHIA MACROPHYLLA",font=f(26,True,m=True),fill=ACC)
 d.text((1235,375),"small concealed pipe / normal perianth body 3–5 cm",font=f(20),fill=MUTED)
 aleaf=fit_axis(crop_alpha("aristolochia_leaf_flat_1024.png"),round(24*pxcm/.856),1)
 pipe=fit_axis(crop_alpha("aristolochia_pipe_flower_1024.png"),round(4*pxcm/.775),0)
 paste(im,aleaf,(1300,460)); paste(im,pipe,(1950,900))
 d.text((1280,1275),"leaf blade shown: 24 cm",font=f(18,True),fill=(48,91,55)); d.text((1900,1080),"perianth body shown: 4 cm",font=f(18,True),fill=GOLD)
 d.line((1950,875,1950+4*pxcm,875),fill=RED,width=4); d.text((1910,825),"4 cm",font=f(17,True,m=True),fill=RED)
 ruler(d,1260,1350,25,pxcm)
 # Bottom implementation strip.
 d.rounded_rectangle((70,1510,2330,1735),radius=20,fill=(246,242,228),outline=ACC,width=3)
 d.text((100,1540),"FULL 1024 QUAD WIDTHS (1 UU = 1 CM)",font=f(21,True,m=True),fill=ACC)
 d.text((100,1585),"Solandra: 28–37 uu quad  →  18–24 cm corolla body",font=f(22,True,m=True),fill=INK)
 d.text((100,1625),"Aristolochia: 4.6–7.7 uu quad  →  3–5 cm perianth body",font=f(22,True,m=True),fill=INK)
 d.text((100,1665),"Mutation-only pipe ceiling: 10.8 uu quad → 7 cm body",font=f(19,m=True),fill=RED)
 wrap(d,(1240,1545),"Measure the flower body, not transparent padding, pedicel, or the full quad. Solandra is about 4–7× longer and far wider; do not scale both species up together.",f(20),1030)
 OUT.parent.mkdir(parents=True,exist_ok=True); im.save(OUT,optimize=True); print(OUT.relative_to(ROOT))
if __name__=="__main__":main()
