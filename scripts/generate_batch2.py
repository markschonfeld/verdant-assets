#!/usr/bin/env python3
"""Deterministic VERDANT Batch 2 texture and foliage-card generator.

Seamless textures are built from periodic fields and torus-wrapped marks.
Cutouts are rendered oversize and alpha-correct downsampled for clean edges.
All exports are base color only: no directional highlights, cast shadows, or vignette.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "textures"
CUT = ROOT / "cutouts"
TEX.mkdir(exist_ok=True)
CUT.mkdir(exist_ok=True)
N = 2048
C = 2048  # render cutouts at 2x, then alpha-correct downsample to 1024


def periodic_noise(n: int, seed: int, octaves=((2,.42),(5,.28),(11,.17),(23,.09),(47,.04))):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    x *= 2*np.pi/n; y *= 2*np.pi/n
    z = np.zeros((n,n), np.float32)
    for freq, amp in octaves:
        for _ in range(3):
            a,b = rng.integers(1,freq+1,size=2)
            z += amp*np.sin(a*x+b*y+rng.random()*2*np.pi)
    z -= z.min(); z /= max(float(z.max()),1e-6)
    return z


def save_texture(name: str, arr_or_image):
    im = arr_or_image if isinstance(arr_or_image,Image.Image) else Image.fromarray(arr_or_image,"RGB")
    a = np.asarray(im.convert("RGB")).copy()
    a[-1,:,:] = a[0,:,:]; a[:,-1,:] = a[:,0,:]
    Image.fromarray(a,"RGB").save(TEX/f"{name}_2048.png",optimize=True)


def wrapped(draw, kind, coords, fill, width=1, outline=None):
    for ox in (-N,0,N):
        for oy in (-N,0,N):
            if kind in ("line","polygon"):
                pts=[(x+ox,y+oy) for x,y in coords]
                if kind=="line": draw.line(pts,fill=fill,width=width,joint="curve")
                else: draw.polygon(pts,fill=fill,outline=outline)
            else:
                x0,y0,x1,y1=coords; box=(x0+ox,y0+oy,x1+ox,y1+oy)
                if kind=="ellipse": draw.ellipse(box,fill=fill,outline=outline,width=width)
                elif kind=="rectangle": draw.rectangle(box,fill=fill,outline=outline,width=width)


def leaf_points(cx,cy,length,width,ang,serrated=False):
    ca,sa=math.cos(ang),math.sin(ang); pts=[]; steps=24
    for i in range(steps):
        t=math.tau*i/steps
        along=math.cos(t)*length/2
        across=math.sin(t)*width/2*(abs(math.sin(t))**.42)
        if serrated: across *= 1 + .10*math.sin(t*7)
        pts.append((cx+along*ca-across*sa,cy+along*sa+across*ca))
    return pts


def soil_terrace_redo():
    broad=periodic_noise(N,110); crumb=periodic_noise(N,111,((17,.35),(39,.33),(83,.22),(151,.10)))
    y,x=np.mgrid[0:N,0:N].astype(np.float32)
    wobble=17*np.sin(2*np.pi*y/N*3+.4)+8*np.sin(2*np.pi*y/N*7+1.2)
    # Symmetric trough/ridge bands communicate furrows without a light direction.
    phase=2*np.pi*(x+wobble)/170
    trough=((1+np.cos(phase))/2)**2
    broken=.52*broad+.48*crumb
    base=np.empty((N,N,3),np.float32)
    base[:]=np.array((38,27,20),np.float32)
    base += (broken[...,None]-.5)*np.array((22,17,13))
    base -= trough[...,None]*np.array((14,11,8))
    # Damp dark brown micro-variation, not painted shine.
    damp=(periodic_noise(N,112,((29,.5),(71,.3),(137,.2)))>.71)[...,None]
    base += damp*np.array((7,6,4))
    im=Image.fromarray(np.clip(base,0,255).astype(np.uint8),"RGB"); d=ImageDraw.Draw(im,"RGBA")
    rng=random.Random(1104)
    # Many irregular clods and crumbs with non-directional outlines.
    for _ in range(1250):
        cx,cy=rng.randrange(N),rng.randrange(N); rx=rng.randint(3,16); ry=rng.randint(2,11)
        fill=rng.choice([(42,29,21,145),(52,35,24,130),(29,20,16,130),(62,42,27,85)])
        wrapped(d,"ellipse",(cx-rx,cy-ry,cx+rx,cy+ry),fill,outline=(24,17,14,80))
    # Sparse sprouts: only 28 across four million pixels.
    for _ in range(28):
        cx,cy=rng.randrange(N),rng.randrange(N); a=rng.random()*math.tau
        col=rng.choice([(55,91,43,235),(69,108,48,225),(76,116,53,210)])
        for da in (-.55,.55): wrapped(d,"polygon",leaf_points(cx+math.cos(a+da)*5,cy+math.sin(a+da)*5,15,7,a+da),col)
    save_texture("soil_terrace",im)


def rust_corrugated():
    # Mid-frequency periodic fields avoid one giant stain becoming a repeat landmark.
    macro=periodic_noise(N,201,((5,.35),(11,.30),(23,.22),(47,.13))); fine=periodic_noise(N,202,((13,.28),(31,.32),(71,.25),(149,.15)))
    y,x=np.mgrid[0:N,0:N].astype(np.float32)
    wobble=5*np.sin(2*np.pi*y/N*3)
    corr=(1+np.cos(2*np.pi*(x+wobble)/112))/2
    # Rust dominates; pale paint survives as interrupted islands and streaks.
    rust=np.clip((.60*macro+.27*fine+.13*corr-.27)*2.15,0,1)
    paint=np.array((207,202,174),np.float32); oxide=np.array((109,50,26),np.float32)
    arr=paint[None,None,:]*(1-rust[...,None])+oxide[None,None,:]*rust[...,None]
    # Symmetric chromatic rib bands: obvious corrugation, no one-sided bevel light.
    arr += (corr[...,None]-.5)*np.array((28,19,12))
    vertical_grime=(.5+.5*np.cos(2*np.pi*x/224+1.1))*(.35+.65*(.5+.5*np.sin(2*np.pi*y/N*7)))
    arr -= (rust*vertical_grime)[...,None]*np.array((20,12,6))
    im=Image.fromarray(np.clip(arr,0,255).astype(np.uint8),"RGB"); d=ImageDraw.Draw(im,"RGBA")
    rng=random.Random(204)
    for _ in range(520):
        cx,cy=rng.randrange(N),rng.randrange(N); rx=rng.randint(4,28); ry=rng.randint(3,30)
        wrapped(d,"ellipse",(cx-rx,cy-ry,cx+rx,cy+ry),rng.choice([(67,37,25,105),(154,70,31,125),(225,216,183,70)]))
    # Repeated rib valleys are material structure, kept neutral rather than highlighted.
    for x0 in range(43,N,112):
        d.line((x0,0,x0,N),fill=(57,39,30,135),width=5)
    save_texture("rust_corrugated",im)


def terrazzo_institutional():
    n=periodic_noise(N,301,((9,.5),(27,.32),(63,.18)))
    arr=np.clip(np.array((218,207,181),np.float32)+(n[...,None]-.5)*18,0,255).astype(np.uint8)
    im=Image.fromarray(arr,"RGB"); d=ImageDraw.Draw(im,"RGBA"); rng=random.Random(302)
    aggregate=[(91,91,86,245),(55,60,60,235),(191,98,78,235),(143,139,125,220),(235,225,198,220)]
    for _ in range(4300):
        cx,cy=rng.randrange(N),rng.randrange(N); r=rng.randint(2,9); ang=rng.random()*math.tau
        pts=[]
        for j in range(rng.randint(4,7)):
            a=ang+math.tau*j/rng.randint(4,7); rr=r*rng.uniform(.65,1.35)
            pts.append((cx+math.cos(a)*rr,cy+math.sin(a)*rr))
        wrapped(d,"polygon",pts,rng.choice(aggregate))
    # Offset brass divider grid; flat hue, no highlight/shadow bevel.
    for x in (287,970,1653): d.rectangle((x,0,x+12,N),fill=(139,105,49,255))
    for y in (401,1084,1767): d.rectangle((0,y,N,y+12),fill=(139,105,49,255))
    # Scuffs are neutral translucent arcs, distributed rather than lit.
    for _ in range(65):
        cx,cy=rng.randrange(N),rng.randrange(N); rx=rng.randint(18,75); ry=rng.randint(4,15)
        wrapped(d,"ellipse",(cx-rx,cy-ry,cx+rx,cy+ry),(85,82,72,rng.randint(8,20)))
    save_texture("terrazzo_institutional",im)


def dome_glass_dirty():
    macro=periodic_noise(N,401); fine=periodic_noise(N,402,((13,.45),(37,.32),(97,.23)))
    arr=np.empty((N,N,3),np.float32); arr[:]=np.array((192,215,198),np.float32)
    arr += (macro[...,None]-.5)*np.array((16,19,14)) + (fine[...,None]-.5)*np.array((8,10,7))
    im=Image.fromarray(np.clip(arr,0,255).astype(np.uint8),"RGB").convert("RGBA")
    # Periodic translucent algae mottles with no image-corner vignette.
    algae=Image.new("RGBA",(N,N),(0,0,0,0)); ad=ImageDraw.Draw(algae,"RGBA"); rng=random.Random(403)
    for _ in range(95):
        cx,cy=rng.randrange(N),rng.randrange(N); rx=rng.randint(18,120); ry=rng.randint(8,55)
        wrapped(ad,"ellipse",(cx-rx,cy-ry,cx+rx,cy+ry),rng.choice([(54,96,55,18),(76,111,66,23),(39,82,48,15)]))
    algae=algae.filter(ImageFilter.GaussianBlur(18)); im=Image.alpha_composite(im,algae)
    d=ImageDraw.Draw(im,"RGBA")
    # Face-on water/mineral traces; every mark wraps.
    for _ in range(115):
        x=rng.randrange(N); y=rng.randrange(N); length=rng.randint(90,520); wob=rng.randint(-12,12)
        pts=[(x,y),(x+wob,y+length*.35),(x-wob//2,y+length)]
        wrapped(d,"line",pts,rng.choice([(236,235,208,28),(96,127,102,20),(123,139,120,18)]),width=rng.randint(2,7))
    for _ in range(190):
        cx,cy=rng.randrange(N),rng.randrange(N); r=rng.randint(2,12)
        wrapped(d,"ellipse",(cx-r,cy-r,cx+r,cy+r),(229,224,193,rng.randint(20,48)),outline=(139,149,128,20))
    save_texture("dome_glass_dirty",im.convert("RGB"))


def concrete_rubble():
    n=periodic_noise(N,501,((7,.45),(23,.34),(61,.21)))
    arr=np.clip(np.array((101,97,89),np.float32)+(n[...,None]-.5)*22,0,255).astype(np.uint8)
    im=Image.fromarray(arr,"RGB"); d=ImageDraw.Draw(im,"RGBA"); rng=random.Random(502)
    # Large, high-contrast broken slabs; flat faces and neutral edge lines avoid baked light.
    for _ in range(92):
        cx,cy=rng.randrange(N),rng.randrange(N); rad=rng.randint(55,175); count=rng.randint(5,9)
        angs=sorted(rng.random()*math.tau for _ in range(count)); pts=[]
        for a in angs:
            rr=rad*rng.uniform(.58,1.16); pts.append((cx+math.cos(a)*rr,cy+math.sin(a)*rr*.76))
        col=rng.choice([(166,161,147,255),(145,142,132,255),(184,178,158,255),(126,127,121,255)])
        wrapped(d,"polygon",pts,col)
        wrapped(d,"line",pts+[pts[0]],(58,58,55,230),width=rng.randint(4,8))
        # Angular internal fracture marks, not face shading.
        if rng.random()<.72:
            a=rng.random()*math.tau; p1=(cx+math.cos(a)*rad*.08,cy+math.sin(a)*rad*.06); p2=(cx+math.cos(a)*rad*.60,cy+math.sin(a)*rad*.42)
            wrapped(d,"line",[p1,p2],(76,74,69,175),width=rng.randint(2,5))
        # Exposed rusted rebar projecting beyond selected chunks.
        if rng.random()<.52:
            a=rng.random()*math.tau; p1=(cx+math.cos(a)*rad*.28,cy+math.sin(a)*rad*.18); p2=(cx+math.cos(a)*rad*1.45,cy+math.sin(a)*rad*1.02)
            wrapped(d,"line",[p1,p2],rng.choice([(112,58,35,255),(126,66,37,255),(72,67,59,255)]),width=rng.randint(5,10))
            ex,ey=p2; wrapped(d,"ellipse",(ex-7,ey-7,ex+7,ey+7),(70,51,39,255),outline=(143,78,43,255),width=3)
    # Dust and grit in the gaps, subordinate to the slabs.
    for _ in range(480):
        cx,cy=rng.randrange(N),rng.randrange(N); r=rng.randint(1,6)
        wrapped(d,"ellipse",(cx-r,cy-r,cx+r,cy+r),rng.choice([(75,74,69,165),(137,131,117,175),(178,169,145,140)]))
    save_texture("concrete_rubble",im)


# ---------- alpha cutouts ----------
def alpha_downsample(im: Image.Image, out: Path):
    """Downsample in premultiplied-alpha space, then unpremultiply RGB."""
    a=np.asarray(im.convert("RGBA"),dtype=np.float32)
    alpha=a[...,3:4]/255.0; prem=np.concatenate((a[...,:3]*alpha,a[...,3:4]),axis=2).astype(np.uint8)
    small=np.asarray(Image.fromarray(prem,"RGBA").resize((1024,1024),Image.Resampling.LANCZOS),dtype=np.float32)
    sa=small[...,3:4]; rgb=np.where(sa>0,np.clip(small[...,:3]*255.0/np.maximum(sa,1),0,255),0)
    outa=np.concatenate((rgb,sa),axis=2).astype(np.uint8)
    Image.fromarray(outa,"RGBA").save(out,optimize=True)


def draw_leaf(d,cx,cy,length,width,ang,color,vein=(24,58,32,165)):
    d.polygon(leaf_points(cx,cy,length,width,ang,True),fill=color)
    ca,sa=math.cos(ang),math.sin(ang)
    d.line((cx-ca*length*.34,cy-sa*length*.34,cx+ca*length*.34,cy+sa*length*.34),fill=vein,width=max(2,int(width/20)))


def vine_hanging():
    im=Image.new("RGBA",(C,C),(0,0,0,0)); d=ImageDraw.Draw(im,"RGBA"); rng=random.Random(601)
    stems=[]
    for branch in range(4):
        pts=[]
        for i in range(18):
            y=150+i*98; x=1010+(branch-1.5)*65+90*math.sin(i*.58+branch*.8)+i*(branch-1.5)*3
            pts.append((x,y))
        stems.append(pts); d.line(pts,fill=(41,79,42,255),width=15-branch*2,joint="curve")
        for i,(x,y) in enumerate(pts[1:-1],1):
            if i%2==branch%2 or rng.random()<.45:
                side=-1 if (i+branch)%2 else 1; ang=side*(1.05+rng.uniform(-.25,.25))
                ex=x+math.cos(ang)*58; ey=y+math.sin(ang)*58
                d.line((x,y,ex,ey),fill=(48,88,45,245),width=7)
                draw_leaf(d,ex,ey,rng.randint(90,145),rng.randint(45,75),ang,rng.choice([(39,94,48,255),(50,113,55,255),(65,126,62,255),(83,133,68,255)]))
    alpha_downsample(im,CUT/"vine_hanging_1024.png")


def vine_wall_patch():
    im=Image.new("RGBA",(C,C),(0,0,0,0)); d=ImageDraw.Draw(im,"RGBA"); rng=random.Random(602); cx=cy=1024
    for b in range(30):
        a=math.tau*b/30+rng.uniform(-.11,.11); length=rng.randint(420,830); pts: list[tuple[float,float]]=[(cx,cy)]
        for j in range(1,7):
            t=j/6; pts.append((cx+math.cos(a)*length*t+math.sin(t*math.pi*2+b)*35,cy+math.sin(a)*length*t+math.cos(t*math.pi*2+b)*35))
        d.line(pts,fill=(42,76,39,225),width=rng.randint(5,11),joint="curve")
    # Dense center, thinning raggedly at edge.
    for _ in range(430):
        a=rng.random()*math.tau; radius=760*(rng.random()**.62); x=cx+math.cos(a)*radius*rng.uniform(.78,1.15); y=cy+math.sin(a)*radius*rng.uniform(.72,1.08)
        size=int(112-55*(radius/800)+rng.randint(-12,18)); size=max(42,size)
        draw_leaf(d,x,y,size,int(size*.50),a+rng.uniform(-1.1,1.1),rng.choice([(31,82,43,255),(43,101,48,255),(54,116,53,255),(69,128,61,255),(82,137,66,255)]))
    alpha_downsample(im,CUT/"vine_wall_patch_1024.png")


def weed_clump():
    im=Image.new("RGBA",(C,C),(0,0,0,0)); d=ImageDraw.Draw(im,"RGBA"); rng=random.Random(603); bx,by=1024,1840
    # Scrappy grass blades: narrow base, broad irregular crown.
    for _ in range(105):
        x0=bx+rng.randint(-90,90); h=rng.randint(470,1300); lean=rng.randint(-360,360); w=rng.randint(8,25)
        pts=[(x0-w,by),(x0+lean-w//3,by-h*.56),(x0+lean,by-h),(x0+lean+w//2,by-h*.56),(x0+w,by)]
        d.polygon(pts,fill=rng.choice([(47,92,43,255),(62,108,49,255),(74,119,53,255),(89,126,57,255),(118,124,65,255)]))
    # A few tall weed stems and seed heads.
    for _ in range(18):
        x0=bx+rng.randint(-65,65); h=rng.randint(850,1450); lean=rng.randint(-260,260); top=(x0+lean,by-h)
        d.line((x0,by,*top),fill=(65,92,43,255),width=rng.randint(7,13))
        for k in range(rng.randint(3,7)):
            a=math.tau*k/6+rng.random()*.45; ex=top[0]+math.cos(a)*rng.randint(20,65); ey=top[1]+math.sin(a)*rng.randint(18,55)
            d.line((*top,ex,ey),fill=(85,97,48,255),width=5); d.ellipse((ex-10,ey-8,ex+10,ey+8),fill=(128,112,61,255))
    alpha_downsample(im,CUT/"weed_clump_1024.png")


def leaf_debris():
    im=Image.new("RGBA",(C,C),(0,0,0,0)); d=ImageDraw.Draw(im,"RGBA"); rng=random.Random(604)
    palette=[(74,94,43,255),(95,107,48,255),(122,105,51,255),(143,92,48,255),(104,68,41,255),(54,83,42,255)]
    for _ in range(120):
        x=rng.randint(230,1818); y=rng.randint(260,1788); length=rng.randint(45,145); width=rng.randint(22,78); a=rng.random()*math.tau
        draw_leaf(d,x,y,length,width,a,rng.choice(palette),vein=(62,54,34,170))
        if rng.random()<.28:
            ca,sa=math.cos(a),math.sin(a); d.line((x-ca*length*.5,y-sa*length*.5,x-ca*length*.78,y-sa*length*.78),fill=(72,57,35,220),width=4)
    for _ in range(34):
        x=rng.randint(260,1780); y=rng.randint(260,1780); a=rng.random()*math.tau; length=rng.randint(35,150)
        d.line((x,y,x+math.cos(a)*length,y+math.sin(a)*length),fill=(76,58,37,235),width=rng.randint(3,8))
    alpha_downsample(im,CUT/"leaf_debris_1024.png")


def main():
    soil_terrace_redo(); rust_corrugated(); terrazzo_institutional(); dome_glass_dirty(); concrete_rubble()
    vine_hanging(); vine_wall_patch(); weed_clump(); leaf_debris()
    print("Generated corrected soil + 8 Batch 2 assets")


if __name__=="__main__": main()
