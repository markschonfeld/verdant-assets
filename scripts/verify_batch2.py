#!/usr/bin/env python3
"""Mechanical QA and visual-review artifacts for VERDANT Batch 2."""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
TEX=ROOT/'textures'; CUT=ROOT/'cutouts'; QA=ROOT/'qa'; QA.mkdir(exist_ok=True)
textures=['soil_terrace','rust_corrugated','terrazzo_institutional','dome_glass_dirty','concrete_rubble']
cutouts=['vine_hanging','vine_wall_patch','weed_clump','leaf_debris']
report: dict = {'textures':{},'cutouts':{}}
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',24)

# Seam, near-edge, and broad illumination guards.
tex_thumbs=[]
for name in textures:
    p=TEX/f'{name}_2048.png'; im=Image.open(p).convert('RGB'); a=np.asarray(im).astype(np.int16)
    exact_lr=bool(np.array_equal(a[:,0],a[:,-1])); exact_tb=bool(np.array_equal(a[0],a[-1]))
    lr=float(np.abs((a[:,1]-a[:,0])-(a[:,-1]-a[:,-2])).mean())
    tb=float(np.abs((a[1]-a[0])-(a[-1]-a[-2])).mean())
    lum=.2126*a[...,0]+.7152*a[...,1]+.0722*a[...,2]
    q=[lum[:1024,:1024].mean(),lum[:1024,1024:].mean(),lum[1024:,:1024].mean(),lum[1024:,1024:].mean()]
    rec={'size':list(im.size),'mode':im.mode,'format':Image.open(p).format,'exact_left_right':exact_lr,'exact_top_bottom':exact_tb,'edge_derivative_mae_lr':round(lr,3),'edge_derivative_mae_tb':round(tb,3),'quadrant_luminance_spread':round(float(max(q)-min(q)),3),'mean_luminance':round(float(lum.mean()),3),'bytes':p.stat().st_size}
    rec['pass']=rec['size']==[2048,2048] and rec['mode']=='RGB' and rec['format']=='PNG' and exact_lr and exact_tb and rec['quadrant_luminance_spread']<18
    report['textures'][name]=rec
    tile=im.resize((340,340),Image.Resampling.LANCZOS); tiled=Image.new('RGB',(680,680))
    for x in (0,340):
        for y in (0,340): tiled.paste(tile,(x,y))
    tiled.save(QA/f'{name}_2x2_preview.png',optimize=True); tex_thumbs.append((name,tiled.resize((360,360),Image.Resampling.LANCZOS)))

# Alpha and padding guards. Fully transparent pixels must carry zero RGB.
cut_thumbs=[]
for name in cutouts:
    p=CUT/f'{name}_1024.png'; im=Image.open(p).convert('RGBA'); a=np.asarray(im)
    alpha=a[...,3]; ys,xs=np.where(alpha>0)
    bbox=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)] if len(xs) else None
    transparent=alpha==0; partial=(alpha>0)&(alpha<255)
    transparent_rgb_max=int(a[...,:3][transparent].max()) if transparent.any() else None
    rec={'size':list(im.size),'mode':im.mode,'format':Image.open(p).format,'alpha_min':int(alpha.min()),'alpha_max':int(alpha.max()),'transparent_fraction':round(float(transparent.mean()),4),'partial_alpha_pixels':int(partial.sum()),'opaque_pixels':int((alpha==255).sum()),'content_bbox':bbox,'transparent_rgb_max':transparent_rgb_max,'bytes':p.stat().st_size}
    padded=bool(bbox and bbox[0]>=20 and bbox[1]>=20 and bbox[2]<=1004 and bbox[3]<=1004)
    rec['pass']=rec['size']==[1024,1024] and rec['mode']=='RGBA' and rec['format']=='PNG' and rec['alpha_min']==0 and rec['alpha_max']==255 and rec['transparent_fraction']>.18 and rec['partial_alpha_pixels']>100 and transparent_rgb_max==0 and padded
    report['cutouts'][name]=rec
    # Checkerboard proves transparency and makes white fringes visible.
    bg=Image.new('RGB',(1024,1024),(58,62,58)); bd=ImageDraw.Draw(bg)
    step=64
    for yy in range(0,1024,step):
        for xx in range(0,1024,step):
            if (xx//step+yy//step)%2==0: bd.rectangle((xx,yy,xx+step-1,yy+step-1),fill=(188,184,170))
    bg.paste(im,(0,0),im); bg.save(QA/f'{name}_checker_preview.png',optimize=True)
    cut_thumbs.append((name,bg.resize((360,360),Image.Resampling.LANCZOS)))

contact=Image.new('RGB',(1140,820),(25,31,28)); d=ImageDraw.Draw(contact)
for i,(name,im) in enumerate(tex_thumbs):
    x=20+(i%3)*370; y=20+(i//3)*400; contact.paste(im,(x,y)); d.text((x,y+365),name.replace('_',' ').upper(),font=font,fill=(238,222,179))
contact.save(QA/'batch2_textures_contact_sheet.png',optimize=True)

contact=Image.new('RGB',(760,820),(25,31,28)); d=ImageDraw.Draw(contact)
for i,(name,im) in enumerate(cut_thumbs):
    x=20+(i%2)*370; y=20+(i//2)*400; contact.paste(im,(x,y)); d.text((x,y+365),name.replace('_',' ').upper(),font=font,fill=(238,222,179))
contact.save(QA/'batch2_cutouts_contact_sheet.png',optimize=True)

report['pass']=all(v['pass'] for v in report['textures'].values()) and all(v['pass'] for v in report['cutouts'].values())
(QA/'batch2_report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['pass'] else 1)
