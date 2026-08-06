#!/usr/bin/env python3
"""Mechanical and visual QA for the improvised seal-plate sheet PBR set."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont

from generate_batch3_pbr import normal_dx

ROOT=Path(__file__).resolve().parents[1]
PBR=ROOT/"textures"/"pbr"; QA=ROOT/"qa"/"seal_plate_sheet"; QA.mkdir(parents=True,exist_ok=True)
NAME="seal_plate_sheet"; MAPS=("basecolor","normal","roughness","ao")

def stats(a:np.ndarray)->dict[str,float]:
 return {"min":int(a.min()),"max":int(a.max()),"mean":round(float(a.mean()),3),"stddev":round(float(a.std()),3),"p05":round(float(np.percentile(a,5)),3),"p95":round(float(np.percentile(a,95)),3)}

def exact_seams(a:np.ndarray)->tuple[bool,bool]:
 return bool(np.array_equal(a[:,0],a[:,-1])),bool(np.array_equal(a[0],a[-1]))

def tile_preview(im:Image.Image,out:Path)->None:
 thumb=im.resize((384,384),Image.Resampling.LANCZOS); canvas=Image.new(im.mode,(768,768))
 for x in (0,384):
  for y in (0,384): canvas.paste(thumb,(x,y))
 canvas.save(out,optimize=True)

def lit_preview(base:np.ndarray,normal:np.ndarray,rough:np.ndarray,ao:np.ndarray)->Image.Image:
 b=base.astype(np.float32)/255; n=normal.astype(np.float32)/255*2-1; light=np.array([-.38,-.42,.82],np.float32); light/=np.linalg.norm(light)
 ndotl=np.clip((n*light).sum(-1),0,1); r=rough.astype(np.float32)/255; diffuse=.27+.82*ndotl; spec=np.power(ndotl,5+70*r)*(1-r)*.75
 return Image.fromarray(np.clip((b*diffuse[...,None]*(ao[...,None]/255)+spec[...,None])*255,0,255).astype(np.uint8),"RGB")
report:dict={"spec":{"dimensions":[2048,2048],"format":"PNG","metallic_constant":1.0,
 "normal_convention":"DirectX tangent-space; green-down",
 "basecolor_policy":"unpainted neutral mill/zinc pigment only; no AO or lighting",
 "uv_caveat":"edge dimples require pane-local 0..1 UVs; use geometry/barycentric edge treatment under world projection"},"maps":{}}
loaded={}; passes=[]
for m in MAPS:
 p=PBR/f"{NAME}_{m}.png"; raw=Image.open(p); mode="RGB" if m in ("basecolor","normal") else "L"; im=raw.convert(mode); a=np.asarray(im); loaded[m]=a
 lr,tb=exact_seams(a); lum=.2126*a[...,0]+.7152*a[...,1]+.0722*a[...,2] if a.ndim==3 else a.astype(np.float32); s:dict=stats(lum)
 ok=raw.format=="PNG" and raw.mode==mode and im.size==(2048,2048) and lr and tb
 if m=="basecolor":
  chroma=(a.max(2)-a.min(2)).astype(np.float32); s["mean_rgb"]=[round(float(a[...,i].mean()),3) for i in range(3)]; s["mean_chroma"]=round(float(chroma.mean()),3); s["p95_chroma"]=round(float(np.percentile(chroma,95)),3)
  ok=ok and s["mean_chroma"]<12 and s["p95_chroma"]<24 and max(s["mean_rgb"])-min(s["mean_rgb"])<7
 elif m=="normal":
  ch=[stats(a[...,i]) for i in range(3)]; s["channels_rgb"]=ch; ok=ok and ch[2]["mean"]>185 and ch[0]["stddev"]>2.5 and ch[1]["stddev"]>2.5
 elif m=="roughness":
  s["p95_minus_p05"]=round(s["p95"]-s["p05"],3); ok=ok and s["stddev"]>=18 and s["p95_minus_p05"]>=55
 elif m=="ao":
  s["p95_minus_p05"]=round(s["p95"]-s["p05"],3); ok=ok and s["p95"]>=245 and s["p95_minus_p05"]>=25
 report["maps"][m]={"path":str(p.relative_to(ROOT)),"mode":raw.mode,"size":list(im.size),"exact_left_right":lr,"exact_top_bottom":tb,"statistics":s,"pass":bool(ok)}; passes.append(bool(ok))

base=loaded["basecolor"]; normal=loaded["normal"]; rough=loaded["roughness"]; ao=loaded["ao"]
lum=.2126*base[...,0]+.7152*base[...,1]+.0722*base[...,2]
# Reject base colour that is simply AO/height relief baked into pigment.
report["base_ao_abs_correlation"]=round(abs(float(np.corrcoef(lum.ravel(),ao.ravel())[0,1])),4)
passes.append(report["base_ao_abs_correlation"]<.45)
# Edge dimples must be materially stronger near pane UV edges than in the center.
dev=np.sqrt((normal[...,0].astype(float)-127.5)**2+(normal[...,1].astype(float)-127.5)**2)
edge=np.zeros((2048,2048),bool); edge[:128]=True; edge[-128:]=True; edge[:,:128]=True; edge[:,-128:]=True
report["normal_relief_edge_mean"]=round(float(dev[edge].mean()),3); report["normal_relief_center_mean"]=round(float(dev[~edge].mean()),3)
report["edge_fastener_concentration_pass"]=report["normal_relief_edge_mean"]>report["normal_relief_center_mean"]*1.25
passes.append(report["edge_fastener_concentration_pass"])
# DirectX convention unit test.
ramp_y=np.sin(np.arange(2048,dtype=np.float32)*2*np.pi/2048); ramp=np.repeat(ramp_y[:,None],2048,axis=1); rn=normal_dx(ramp,18)
report["directx_convention_unit_check"]={"positive_image_y_slope_green":int(rn[0,1024,1]),"negative_image_y_slope_green":int(rn[1024,1024,1]),"pass":bool(rn[0,1024,1]>127 and rn[1024,1024,1]<127)}; passes.append(report["directx_convention_unit_check"]["pass"])

tile_preview(Image.fromarray(base,"RGB"),QA/f"{NAME}_basecolor_2x2.png")
lit=lit_preview(base,normal,rough,ao); lit.resize((768,768),Image.Resampling.LANCZOS).save(QA/f"{NAME}_lit_preview.png",optimize=True)
cell=390; sheet=Image.new("RGB",(cell*5,cell+90),(21,27,25)); d=ImageDraw.Draw(sheet); font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",18)
ims=[Image.fromarray(base,"RGB"),Image.fromarray(normal,"RGB"),Image.fromarray(rough,"L").convert("RGB"),Image.fromarray(ao,"L").convert("RGB"),lit]
for i,(im,label) in enumerate(zip(ims,("BASE COLOR","NORMAL DX","ROUGHNESS","AO","QA-ONLY LIT"))):
 sheet.paste(im.resize((cell,cell),Image.Resampling.LANCZOS),(i*cell,35)); d.text((i*cell+10,8),label,font=font,fill=(231,221,196))
d.text((12,cell+48),"SEAL PLATE SHEET / UNPAINTED MILL FINISH / EDGE DIMPLING REQUIRES PANE-LOCAL UV",font=font,fill=(236,220,177)); sheet.save(QA/f"{NAME}_contact_sheet.png",optimize=True)
report["pass"]=bool(all(passes)); (QA/f"{NAME}_report.json").write_text(json.dumps(report,indent=2)+"\n"); print(json.dumps(report,indent=2)); raise SystemExit(0 if report["pass"] else 1)
