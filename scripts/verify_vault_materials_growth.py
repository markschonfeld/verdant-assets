#!/usr/bin/env python3
"""Mechanical QA and visual evidence for VERDANT vault asset delivery."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
PBR=ROOT/"textures"/"pbr"; CUT=ROOT/"cutouts"
QA=ROOT/"qa"/"vault_materials_growth"; QA.mkdir(parents=True,exist_ok=True)
ALU_QA=ROOT/"qa"/"batch4_aluminium"; ALU_QA.mkdir(parents=True,exist_ok=True)
MATERIALS={
 "alu_oxidised":["basecolor","normal","roughness","ao"],
 "glaze_acrylic_original":["basecolor","normal","roughness","ao","opacity"],
 "glaze_glass_repair":["basecolor","normal","roughness","ao","opacity"],
}
CUTOUTS=["growth_tube_cling","growth_joint_mass","growth_creeping_mat","growth_reaching"]
FONT=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",18)
SMALL=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",13)


def stat(a):
 return {"min":int(a.min()),"max":int(a.max()),"mean":round(float(a.mean()),2),
         "stddev":round(float(a.std()),2),"p05":round(float(np.percentile(a,5)),2),
         "p95":round(float(np.percentile(a,95)),2)}


def seams(a): return bool(np.array_equal(a[:,0],a[:,-1])),bool(np.array_equal(a[0],a[-1]))


def lit(base,normal,rough,metallic=0.0):
 b=base.astype(np.float32)/255; n=normal.astype(np.float32)/255*2-1
 r=rough.astype(np.float32)/255
 light=np.array([-.48,-.30,.82],np.float32); light/=np.linalg.norm(light)
 nd=np.clip((n*light).sum(-1),0,1)
 diffuse=b*(.22+.70*nd[...,None])*(1-metallic*.72)
 # Broad environment-like reflection retains highlights at the chalked end.
 spec=np.power(nd,5+60*r)*(1-r)*(.34+.66*metallic)
 env=(.08+.22*(1-r))*metallic
 out=diffuse+spec[...,None]+env[...,None]*np.array([.82,.90,.94])
 return Image.fromarray(np.clip(out*255,0,255).astype(np.uint8),"RGB")


def checker(im):
 tile=32; bg=Image.new("RGB",im.size)
 d=ImageDraw.Draw(bg)
 for y in range(0,im.height,tile):
  for x in range(0,im.width,tile):
   d.rectangle((x,y,x+tile,y+tile),fill=(54,60,57) if (x//tile+y//tile)%2 else (112,118,111))
 bg.paste(im.convert("RGB"),(0,0),im.getchannel("A")); return bg

report={"spec":{"dimensions_pbr":[2048,2048],"dimensions_cutouts":[1024,1024],
 "normal":"DirectX green-down","opacity":"white=clear, dark=grime (matches glass_dome_grime)",
 "projection":"PBR maps are exact-edge seamless for triplanar/world-aligned projection"},"materials":{},"cutouts":{}}

# DirectX unit convention: positive image-Y height slope must raise green.
ramp=np.sin(np.arange(2048,dtype=np.float32)*2*np.pi/2048)
dy=(np.roll(ramp,-1)-np.roll(ramp,1))*20
g=(dy/np.sqrt(dy*dy+1)*.5+.5)*255
report["directx_unit"]={"positive_slope_green":int(g[0]),"negative_slope_green":int(g[1024]),
                         "pass":bool(g[0]>127 and g[1024]<127)}

for name,maps in MATERIALS.items():
 maps_rec: dict[str, object]={}; rec: dict[str, object]={"maps":maps_rec}; loaded={}; passes=[]
 for suffix in maps:
  p=PBR/f"{name}_{suffix}.png"; raw=Image.open(p); exp="RGB" if suffix in ("basecolor","normal") else "L"
  a=np.asarray(raw.convert(exp)); loaded[suffix]=a; lr,tb=seams(a)
  lum=.2126*a[...,0]+.7152*a[...,1]+.0722*a[...,2] if a.ndim==3 else a.astype(np.float32)
  s=stat(lum); ok=raw.format=="PNG" and raw.size==(2048,2048) and raw.mode==exp and lr and tb
  if suffix=="basecolor":
   s["channel_spread_mean"]=round(float(a.reshape(-1,3).std(0).mean()),2)
   if name=="alu_oxidised": ok=ok and s["channel_spread_mean"]<12 and s["p95"]-s["p05"]<38
  elif suffix=="normal":
   s["rgb"]=[stat(a[...,i]) for i in range(3)]; ok=ok and s["rgb"][2]["mean"]>220
  elif suffix=="roughness":
   s["p95_minus_p05"]=round(s["p95"]-s["p05"],2)
   ok=ok and s["p95_minus_p05"]>=45 and s["stddev"]>=14
   # v7's in-engine calibration deliberately raises the chalked-oxide ceiling
   # to 214; keep the verifier synchronized with the generator's explicit clamp.
   if name=="alu_oxidised": ok=ok and s["max"]<=214
  elif suffix=="ao": ok=ok and s["p95"]>=245
  elif suffix=="opacity": ok=ok and s["p95"]>=230 and s["p95"]-s["p05"]>=30
  maps_rec[suffix]={"path":str(p.relative_to(ROOT)),"size":list(raw.size),"mode":raw.mode,
   "exact_lr":lr,"exact_tb":tb,"statistics":s,"pass":bool(ok)}; passes.append(bool(ok))
 metal=.92 if name=="alu_oxidised" else 0
 prev=lit(loaded["basecolor"],loaded["normal"],loaded["roughness"],metal)
 prev.resize((768,768),Image.Resampling.LANCZOS).save(QA/f"{name}_lit.png",optimize=True)
 tile=loaded["basecolor"]; half=Image.fromarray(tile,"RGB").resize((384,384),Image.Resampling.LANCZOS)
 tiled=Image.new("RGB",(768,768))
 for x in (0,384):
  for y in (0,384): tiled.paste(half,(x,y))
 tiled.save(QA/f"{name}_basecolor_2x2.png",optimize=True)
 rec["pass"]=all(passes); report["materials"][name]=rec

for name in CUTOUTS:
 p=CUT/f"{name}_1024.png"; im=Image.open(p); a=np.asarray(im.convert("RGBA")); alpha=a[...,3]
 transparent=a[alpha==0,:3]; occupancy=float((alpha>8).mean())
 ok=im.format=="PNG" and im.size==(1024,1024) and im.mode=="RGBA" and alpha.min()==0 and alpha.max()==255 and occupancy>.045 and occupancy<.72 and (transparent.size==0 or transparent.max()==0)
 report["cutouts"][name]={"path":str(p.relative_to(ROOT)),"size":list(im.size),"mode":im.mode,
  "alpha":stat(alpha),"occupancy_gt_8":round(occupancy,4),"transparent_rgb_zero":bool(transparent.size==0 or transparent.max()==0),"pass":bool(ok)}
 checker(im).save(QA/f"{name}_checker.png",optimize=True)

# PBR contact sheet: raw maps plus QA-only lit result.
cell=260; rows=len(MATERIALS); sheet=Image.new("RGB",(cell*6,rows*(cell+42)+28),(19,25,23)); d=ImageDraw.Draw(sheet)
for c,h in enumerate(["BASE COLOR","NORMAL DX","ROUGHNESS","AO","OPACITY","QA-ONLY LIT"]): d.text((c*cell+8,7),h,font=SMALL,fill=(232,222,196))
for row,(name,maps) in enumerate(MATERIALS.items()):
 y=28+row*(cell+42); ims=[]
 for suffix in ["basecolor","normal","roughness","ao","opacity"]:
  p=PBR/f"{name}_{suffix}.png"
  ims.append(Image.open(p).convert("RGB") if p.exists() else Image.new("RGB",(2048,2048),(35,35,35)))
 ims.append(Image.open(QA/f"{name}_lit.png").convert("RGB"))
 for c,im in enumerate(ims): sheet.paste(im.resize((cell,cell),Image.Resampling.LANCZOS),(c*cell,y))
 d.text((8,y+cell+7),name.upper().replace("_"," "),font=FONT,fill=(235,220,177))
sheet.save(QA/"vault_materials_contact_sheet.png",optimize=True)
# Keep the established urgent-material path updated with a focused crop.
alu=Image.new("RGB",(cell*5,cell+42),(19,25,23)); ad=ImageDraw.Draw(alu)
for c,suffix in enumerate(["basecolor","normal","roughness","ao"]):
 im=Image.open(PBR/f"alu_oxidised_{suffix}.png").convert("RGB"); alu.paste(im.resize((cell,cell),Image.Resampling.LANCZOS),(c*cell,0)); ad.text((c*cell+7,7),suffix.upper(),font=SMALL,fill=(255,239,180))
alu.paste(Image.open(QA/"alu_oxidised_lit.png").resize((cell,cell)),(cell*4,0)); ad.text((cell*4+7,7),"QA-ONLY LIT",font=SMALL,fill=(255,239,180)); ad.text((7,cell+8),"ALU OXIDISED — SPARSE PITS / ROUGHNESS-LED / NO RUST",font=FONT,fill=(235,220,177))
alu.save(ALU_QA/"alu_oxidised_contact_sheet.png",optimize=True)

# Cutout contact sheet on checkerboard.
cs=Image.new("RGB",(512*2,512*2),(25,29,27)); cd=ImageDraw.Draw(cs)
for i,name in enumerate(CUTOUTS):
 im=Image.open(QA/f"{name}_checker.png").resize((512,512),Image.Resampling.LANCZOS); x=(i%2)*512;y=(i//2)*512;cs.paste(im,(x,y));cd.rectangle((x,y,x+511,y+31),fill=(18,23,21));cd.text((x+9,y+7),name.upper().replace("_"," "),font=SMALL,fill=(239,226,185))
cs.save(QA/"engineered_growth_contact_sheet.png",optimize=True)

report["pass"]=bool(report["directx_unit"]["pass"] and all(v["pass"] for v in report["materials"].values()) and all(v["pass"] for v in report["cutouts"].values()))
(QA/"vault_materials_growth_report.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2)); raise SystemExit(0 if report["pass"] else 1)
