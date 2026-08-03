#!/usr/bin/env python3
"""Mechanical QA and contact-sheet generation for VERDANT Batch 1."""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
TEX=ROOT/'textures'; POST=ROOT/'posters'; QA=ROOT/'qa'; QA.mkdir(exist_ok=True)
texture_names=['soil_terrace','concrete_formed','steel_pastel_turquoise','stucco_cream','overgrowth_vine']
poster_names=['garden_loved','wild_branch','pruning_direction']
report: dict = {'textures':{},'posters':{}}

# Edge equality plus near-edge derivative comparisons. Exact opposite-edge equality
# is intentionally enforced at export, while the derivative score catches obvious
# discontinuity in the first few inward rows/columns.
for name in texture_names:
    p=TEX/f'{name}_2048.png'; im=Image.open(p).convert('RGB'); a=np.asarray(im).astype(np.int16)
    exact_lr=bool(np.array_equal(a[:,0],a[:,-1])); exact_tb=bool(np.array_equal(a[0],a[-1]))
    lr_deriv=float(np.abs((a[:,1]-a[:,0])-(a[:,-1]-a[:,-2])).mean())
    tb_deriv=float(np.abs((a[1]-a[0])-(a[-1]-a[-2])).mean())
    # Mean-luminance spread among quadrants: broad lighting-direction guard.
    lum=a.mean(2); q=[lum[:1024,:1024].mean(),lum[:1024,1024:].mean(),lum[1024:,:1024].mean(),lum[1024:,1024:].mean()]
    report['textures'][name]={'size':list(im.size),'mode':im.mode,'exact_left_right':exact_lr,'exact_top_bottom':exact_tb,'edge_derivative_mae_lr':round(lr_deriv,3),'edge_derivative_mae_tb':round(tb_deriv,3),'quadrant_mean_spread':round(float(max(q)-min(q)),3),'bytes':p.stat().st_size}

for name in poster_names:
    p=POST/f'{name}_1024x1536.png'; im=Image.open(p)
    report['posters'][name]={'size':list(im.size),'mode':im.mode,'bytes':p.stat().st_size}

# 2x2 texture tile previews, individually and in a labeled grid.
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',26)
thumbs=[]
for name in texture_names:
    im=Image.open(TEX/f'{name}_2048.png').convert('RGB').resize((384,384),Image.Resampling.LANCZOS)
    tiled=Image.new('RGB',(768,768));
    for x in (0,384):
        for y in (0,384): tiled.paste(im,(x,y))
    tiled.save(QA/f'{name}_2x2_preview.png',optimize=True)
    th=tiled.resize((400,400),Image.Resampling.LANCZOS); thumbs.append((name,th))
contact=Image.new('RGB',(1240,920),(28,35,31)); d=ImageDraw.Draw(contact)
for i,(name,im) in enumerate(thumbs):
    x=20+(i%3)*410; y=20+(i//3)*450
    contact.paste(im,(x,y)); d.text((x,y+406),name.replace('_',' ').upper(),font=font,fill=(238,222,179))
contact.save(QA/'textures_contact_sheet.png',optimize=True)

# Poster contact sheet.
pc=Image.new('RGB',(1044,560),(28,35,31));
for i,name in enumerate(poster_names):
    im=Image.open(POST/f'{name}_1024x1536.png').convert('RGB').resize((320,480),Image.Resampling.LANCZOS)
    pc.paste(im,(18+i*342,18))
    ImageDraw.Draw(pc).text((18+i*342,510),name.replace('_',' ').upper(),font=font,fill=(238,222,179))
pc.save(QA/'posters_contact_sheet.png',optimize=True)

ok=all(v['size']==[2048,2048] and v['mode']=='RGB' and v['exact_left_right'] and v['exact_top_bottom'] for v in report['textures'].values()) and all(v['size']==[1024,1536] and v['mode']=='RGB' for v in report['posters'].values())
report['pass']=ok
(ROOT/'qa'/'batch1_report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
raise SystemExit(0 if ok else 1)
