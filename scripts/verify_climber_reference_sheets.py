#!/usr/bin/env python3
"""Mechanical QA and contact sheet for VERDANT climber references."""
from __future__ import annotations

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
REF=ROOT/"references"/"botanical"
CUT=ROOT/"cutouts"
QA=ROOT/"qa"/"climber_references"
QA.mkdir(parents=True,exist_ok=True)
SHEETS=[
 REF/"solandra_maxima_trellis_reference_2400x1800.png",
 REF/"aristolochia_dutchmans_pipe_trellis_reference_2400x1800.png",
 REF/"climber_stem_bark_surface_reference_2400x1800.png",
]
CARDS=[
 CUT/"solandra_maxima_leaf_flat_1024.png",
 CUT/"aristolochia_leaf_flat_1024.png",
 CUT/"aristolochia_pipe_flower_1024.png",
]
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def checker(size):
 im=Image.new("RGB",size,(214,211,197)); d=ImageDraw.Draw(im); s=32
 for y in range(0,size[1],s):
  for x in range(0,size[0],s):
   if (x//s+y//s)%2: d.rectangle((x,y,x+s-1,y+s-1),fill=(166,171,161))
 return im


def main():
 report={"sheets":{},"cards":{},"all_pass":True}
 for p in SHEETS:
  im=Image.open(p)
  ok=im.size==(2400,1800) and im.mode=="RGB"
  report["sheets"][p.name]={"size":list(im.size),"mode":im.mode,"pass":ok}
  report["all_pass"] &= ok
 for p in CARDS:
  im=Image.open(p).convert("RGBA"); a=np.asarray(im)
  alpha=a[...,3]; nz=np.argwhere(alpha>0)
  y0,x0=nz.min(0); y1,x1=nz.max(0)
  transparent_rgb_max=int(a[alpha==0,:3].max()) if np.any(alpha==0) else None
  ok=(im.size==(1024,1024) and Image.open(p).mode=="RGBA" and alpha.min()==0 and alpha.max()==255
      and transparent_rgb_max==0 and x0>=24 and y0>=24 and x1<=999 and y1<=999)
  report["cards"][p.name]={"size":list(im.size),"mode":Image.open(p).mode,
      "alpha_min":int(alpha.min()),"alpha_max":int(alpha.max()),"alpha_levels":int(np.unique(alpha).size),
      "transparent_rgb_max":transparent_rgb_max,"content_bbox":[int(x0),int(y0),int(x1),int(y1)],"pass":bool(ok)}
  report["all_pass"] &= bool(ok)

 # Trellis pair, companion bark sheet, then checkerboard card previews.
 canvas=Image.new("RGB",(1800,2300),(231,226,210)); d=ImageDraw.Draw(canvas)
 f=ImageFont.truetype(FONT,24); fb=ImageFont.truetype(FONT,32)
 d.text((55,25),"VERDANT / CLIMBER REFERENCES / QA CONTACT SHEET",font=fb,fill=(31,38,39))
 for i,p in enumerate(SHEETS[:2]):
  im=Image.open(p).convert("RGB"); im.thumbnail((830,620),Image.Resampling.LANCZOS)
  x=55+i*875; canvas.paste(im,(x,85)); d.text((x,85+im.height+12),p.name,font=f,fill=(84,89,82))
 im=Image.open(SHEETS[2]).convert("RGB"); im.thumbnail((830,620),Image.Resampling.LANCZOS)
 x=485; canvas.paste(im,(x,780)); d.text((x,780+im.height+12),SHEETS[2].name,font=f,fill=(84,89,82))
 for i,p in enumerate(CARDS):
  rgba=Image.open(p).convert("RGBA"); rgba.thumbnail((500,500),Image.Resampling.LANCZOS)
  bg=checker((500,500)); bg.paste(rgba,((500-rgba.width)//2,(500-rgba.height)//2),rgba)
  x=55+i*570; canvas.paste(bg,(x,1490)); d.text((x,2005),p.name,font=f,fill=(84,89,82))
 d.text((55,2220),"PASS" if report["all_pass"] else "FAIL",font=fb,fill=(48,88,56) if report["all_pass"] else (150,45,35))
 canvas.save(QA/"climber_reference_contact_sheet.png",optimize=True)
 (QA/"climber_reference_report.json").write_text(json.dumps(report,indent=2)+"\n")
 print(json.dumps(report,indent=2))
 if not report["all_pass"]: raise SystemExit(1)

if __name__=="__main__": main()
