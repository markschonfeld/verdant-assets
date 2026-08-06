#!/usr/bin/env python3
"""Mechanical and visual QA for VERDANT mature climber bark PBR sets."""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
PBR=ROOT/"textures"/"pbr"
QA=ROOT/"qa"/"climber_bark_pbr"
QA.mkdir(parents=True,exist_ok=True)
MATERIALS=["bark_solandra_mature","bark_aristolochia_mature"]
MAPS=["basecolor","normal","roughness","ao"]
FONT=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",18)
SMALL=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",14)


def seams(a): return bool(np.array_equal(a[:,0],a[:,-1])),bool(np.array_equal(a[0],a[-1]))
def stats(a): return {"min":int(a.min()),"max":int(a.max()),"mean":round(float(a.mean()),3),"stddev":round(float(a.std()),3),"p05":round(float(np.percentile(a,5)),3),"p95":round(float(np.percentile(a,95)),3)}


def lit(base,normal,rough,ao):
    b=base.astype(np.float32)/255; n=normal.astype(np.float32)/255*2-1
    light=np.array([-.35,-.25,.90],np.float32); light/=np.linalg.norm(light)
    nd=np.clip((n*light).sum(-1),0,1); r=rough.astype(np.float32)/255
    diffuse=.30+.78*nd; spec=np.power(nd,7+58*r)*(1-r)*.44
    out=b*diffuse[...,None]*(ao[...,None]/255)+spec[...,None]
    return Image.fromarray(np.clip(out*255,0,255).astype(np.uint8),"RGB")


report={"spec":{"dimensions":[2048,2048],"format":"PNG","maps":MAPS,
    "normal_convention":"DirectX tangent-space; green-down",
    "uv_orientation":"image Y/V follows stem axis; X/U wraps circumference",
    "basecolor_policy":"pigment only; no baked lighting or AO",
    "contact_policy":"bearing flattening/polish excluded from tile; use mesh/contact mask"},"materials":{}}
all_pass=True
for mat in MATERIALS:
    rec: dict={"maps":{}}; loaded={}; passes=[]
    for m in MAPS:
        p=PBR/f"{mat}_{m}.png"; raw=Image.open(p)
        mode="RGB" if m in ("basecolor","normal") else "L"
        a=np.asarray(raw.convert(mode)); loaded[m]=a; lr,tb=seams(a)
        ai=a.astype(np.int16)
        edge_lr=float(np.abs((ai[:,1]-ai[:,0])-(ai[:,-1]-ai[:,-2])).mean())
        edge_tb=float(np.abs((ai[1]-ai[0])-(ai[-1]-ai[-2])).mean())
        lum=.2126*a[...,0]+.7152*a[...,1]+.0722*a[...,2] if a.ndim==3 else a.astype(np.float32)
        s=stats(lum); ok=raw.format=="PNG" and raw.mode==mode and raw.size==(2048,2048) and lr and tb
        if m=="basecolor":
            h,w=lum.shape; qs=[lum[:h//2,:w//2].mean(),lum[:h//2,w//2:].mean(),lum[h//2:,:w//2].mean(),lum[h//2:,w//2:].mean()]
            s["quadrant_spread"]=round(float(max(qs)-min(qs)),3); ok &= s["quadrant_spread"]<22 and s["stddev"]>6
        elif m=="normal":
            channels=[stats(a[...,i]) for i in range(3)]; s["channels_rgb"]=channels
            ok &= channels[2]["mean"]>175 and channels[0]["stddev"]>3 and channels[1]["stddev"]>1
        elif m=="roughness":
            s["p95_minus_p05"]=round(s["p95"]-s["p05"],3); ok &= s["p95_minus_p05"]>=45 and s["stddev"]>=13
        elif m=="ao":
            s["p95_minus_p05"]=round(s["p95"]-s["p05"],3); ok &= s["p95_minus_p05"]>=25 and s["p95"]>=245
        rec["maps"][m]={"path":str(p.relative_to(ROOT)),"size":list(raw.size),"mode":raw.mode,
            "exact_left_right":lr,"exact_top_bottom":tb,"bytes":p.stat().st_size,"statistics":s,"pass":bool(ok)}
        rec["maps"][m]["edge_derivative_mae_lr"]=round(edge_lr,3)
        rec["maps"][m]["edge_derivative_mae_tb"]=round(edge_tb,3)
        passes.append(bool(ok))
    # Longitudinal grain: variation across U should dominate variation along V.
    h=loaded["normal"].astype(np.float32)
    gx=float(np.abs(np.diff(h[...,0],axis=1)).mean()); gy=float(np.abs(np.diff(h[...,1],axis=0)).mean())
    orient=gx>gy*1.10
    rec["orientation"]={"mean_abs_u_red_gradient":round(gx,4),"mean_abs_v_green_gradient":round(gy,4),"u_dominates":bool(orient),"pass":bool(orient)}
    rec["alignment_pass"]=len({a.shape[:2] for a in loaded.values()})==1
    rec["pass"]=bool(all(passes) and orient and rec["alignment_pass"]); all_pass &= rec["pass"]
    lp=lit(loaded["basecolor"],loaded["normal"],loaded["roughness"],loaded["ao"])
    lp.resize((768,768),Image.Resampling.LANCZOS).save(QA/f"{mat}_lit_preview.png",optimize=True)
    tile=Image.new("RGB",(768,768)); base=Image.fromarray(loaded["basecolor"],"RGB").resize((384,384),Image.Resampling.LANCZOS)
    for x in (0,384):
        for y in (0,384): tile.paste(base,(x,y))
    tile.save(QA/f"{mat}_basecolor_2x2.png",optimize=True)
    report["materials"][mat]=rec

# Contact sheet: maps, 2x2 seam preview, and QA-only lit response.
cell=270; headers=["BASE COLOR","NORMAL DX","ROUGHNESS","AO","2×2 TILE","QA-ONLY LIT"]
sheet=Image.new("RGB",(cell*6,2*(cell+62)+42),(21,27,25)); d=ImageDraw.Draw(sheet)
for i,h in enumerate(headers): d.text((i*cell+8,10),h,font=SMALL,fill=(229,220,196))
for row,mat in enumerate(MATERIALS):
    y=40+row*(cell+62)
    ims=[Image.open(PBR/f"{mat}_basecolor.png").convert("RGB"),Image.open(PBR/f"{mat}_normal.png").convert("RGB"),
         Image.open(PBR/f"{mat}_roughness.png").convert("RGB"),Image.open(PBR/f"{mat}_ao.png").convert("RGB"),
         Image.open(QA/f"{mat}_basecolor_2x2.png").convert("RGB"),Image.open(QA/f"{mat}_lit_preview.png").convert("RGB")]
    for col,im in enumerate(ims): sheet.paste(im.resize((cell,cell),Image.Resampling.LANCZOS),(col*cell,y))
    d.text((10,y+cell+8),mat.replace("_"," ").upper(),font=FONT,fill=(236,220,177))
sheet.save(QA/"climber_bark_pbr_contact_sheet.png",optimize=True)
report["pass"]=bool(all_pass)
(QA/"climber_bark_pbr_report.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
raise SystemExit(0 if all_pass else 1)
