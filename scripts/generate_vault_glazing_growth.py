#!/usr/bin/env python3
"""Generate VERDANT vault glazing PBR sets and engineered-growth cards.

Glazing fields are toroidal for triplanar/world-aligned projection.  The growth
cards are deterministic RGBA silhouettes rendered at 2x and downsampled in
premultiplied-alpha space.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
PBR = ROOT / "textures" / "pbr"
CUT = ROOT / "cutouts"
PBR.mkdir(parents=True, exist_ok=True)
CUT.mkdir(parents=True, exist_ok=True)
N = 2048
C = 2048


def seal(a: np.ndarray) -> np.ndarray:
    a[-1, ...] = a[0, ...]
    a[:, -1, ...] = a[:, 0, ...]
    return a


def norm01(a: np.ndarray, lo=1.0, hi=99.0) -> np.ndarray:
    q0, q1 = np.percentile(a, (lo, hi))
    return np.clip((a-q0) / max(float(q1-q0), 1e-6), 0, 1).astype(np.float32)


def noise(seed: int, layers) -> np.ndarray:
    rng = np.random.default_rng(seed)
    z = np.zeros((N, N), np.float32)
    for sigma, weight in layers:
        raw = rng.standard_normal((N, N), dtype=np.float32)
        v = gaussian_filter(raw, sigma=sigma, mode="wrap")
        v = (v-v.mean()) / max(float(v.std()), 1e-6)
        z += weight*v
    return norm01(z)


def impulses(seed: int, count: int, sigma: float) -> np.ndarray:
    rng = np.random.default_rng(seed)
    a = np.zeros((N, N), np.float32)
    np.add.at(a, (rng.integers(0, N, count), rng.integers(0, N, count)),
              rng.uniform(.5, 1, count).astype(np.float32))
    return norm01(gaussian_filter(a, sigma=sigma, mode="wrap"), 0, 99.7)


def torus_lines(seed: int, count: int, length=(80, 520), width=(1, 4), directional=False) -> np.ndarray:
    rng = random.Random(seed)
    im = Image.new("L", (N, N), 0)
    d = ImageDraw.Draw(im)
    for _ in range(count):
        x, y = rng.randrange(N), rng.randrange(N)
        ang = rng.gauss(-math.pi/2, .18) if directional else rng.random()*math.tau
        total = rng.randint(*length)
        pts: list[tuple[float, float]] = [(float(x), float(y))]
        for k in range(1, rng.randint(3, 7)):
            t = total*k/6
            pts.append((x+math.cos(ang)*t+rng.uniform(-18,18),
                        y+math.sin(ang)*t+rng.uniform(-18,18)))
        for ox in (-N, 0, N):
            for oy in (-N, 0, N):
                d.line([(px+ox, py+oy) for px,py in pts], fill=255,
                       width=rng.randint(*width), joint="curve")
    return np.asarray(im, np.float32)/255


def normal_dx(height: np.ndarray, strength: float) -> np.ndarray:
    dx = (np.roll(height,-1,1)-np.roll(height,1,1))*strength
    dy = (np.roll(height,-1,0)-np.roll(height,1,0))*strength
    nx,ny,nz = -dx,dy,np.ones_like(height)
    inv = 1/np.sqrt(nx*nx+ny*ny+nz*nz)
    return np.clip(np.stack((nx*inv*.5+.5,ny*inv*.5+.5,nz*inv*.5+.5),-1)*255,0,255).astype(np.uint8)


def save_rgb(name: str, suffix: str, a: np.ndarray) -> None:
    Image.fromarray(seal(a.copy()), "RGB").save(PBR/f"{name}_{suffix}.png", optimize=True)


def save_l(name: str, suffix: str, a: np.ndarray) -> None:
    Image.fromarray(seal(a.copy()), "L").save(PBR/f"{name}_{suffix}.png", optimize=True)


def save_glazing(name: str, base: np.ndarray, height: np.ndarray,
                 rough: np.ndarray, ao: np.ndarray, opacity: np.ndarray) -> None:
    save_rgb(name,"basecolor",np.clip(base,0,255).astype(np.uint8))
    save_rgb(name,"normal",normal_dx(height,20))
    save_l(name,"roughness",np.clip(rough,0,255).astype(np.uint8))
    save_l(name,"ao",np.clip(ao,0,255).astype(np.uint8))
    save_l(name,"opacity",np.clip(opacity,0,255).astype(np.uint8))


def glazing_fields(seed: int):
    yy,xx=np.mgrid[0:N,0:N].astype(np.float32)
    haze=noise(seed,((22,.30),(64,.38),(160,.22),(340,.10)))
    fine=noise(seed+1,((2,.18),(7,.31),(19,.31),(55,.20)))
    dx=np.minimum(xx,N-xx); dy=np.minimum(yy,N-yy)
    corner=np.exp(-((np.sqrt(dx*dx+dy*dy))/330)**1.65)
    moisture=np.clip(corner*(.48+.72*haze)+.28*impulses(seed+2,75,38)-.23,0,1)
    run_src=impulses(seed+3,38,11)
    runs=np.zeros_like(run_src)
    for shift in range(0,620,13):
        runs += np.roll(run_src,shift,0)*math.exp(-shift/255)
    runs=norm01(runs,62,99.8)
    dust=np.clip(.60*haze+.40*fine-.52,0,1)
    return haze,fine,moisture,runs,dust


def glaze_acrylic_original() -> None:
    haze,fine,moisture,runs,dust=glazing_fields(5101)
    crazing=gaussian_filter(torus_lines(5110,190,(35,220),(1,2),False),.55,mode="wrap")
    scratches=gaussian_filter(torus_lines(5111,72,(140,660),(1,3),False),.7,mode="wrap")
    mineral=np.clip((fine-.60)*2.8,0,1)*(.25+.75*runs)
    grime=np.clip(.46*moisture+.22*runs+.21*dust+.18*mineral,0,1)
    amber=np.clip(moisture*.75+.25*dust,0,1)
    base=np.empty((N,N,3),np.float32); base[:]=(213,218,197)
    base+=(haze-.5)[...,None]*np.array((15,14,9))
    base+=amber[...,None]*np.array((20,9,-17))
    base-=grime[...,None]*np.array((37,30,26))
    base-=crazing[...,None]*np.array((10,9,7))
    height=.012*haze+.045*crazing+.028*scratches+.035*mineral+.025*moisture
    rough=62+82*haze+64*crazing+43*scratches+67*grime+38*mineral
    ao=255-42*crazing-55*mineral-34*moisture
    opacity=255-192*np.clip(grime+.24*crazing+.10*scratches,0,1)
    save_glazing("glaze_acrylic_original",base,height,rough,ao,opacity)


def glaze_glass_repair() -> None:
    haze,fine,moisture,runs,dust=glazing_fields(5201)
    scratches=gaussian_filter(torus_lines(5210,42,(180,760),(1,2),False),.45,mode="wrap")
    lamination=gaussian_filter(torus_lines(5211,18,(260,920),(1,2),False),1.2,mode="wrap")
    mineral=np.clip((fine-.66)*3.1,0,1)*(.18+.82*runs)
    grime=np.clip(.38*moisture+.22*runs+.15*dust+.20*mineral,0,1)
    edge_green=np.clip(.82*moisture+.18*dust,0,1)
    base=np.empty((N,N,3),np.float32); base[:]=(220,233,224)
    base+=(haze-.5)[...,None]*np.array((7,9,7))
    base+=edge_green[...,None]*np.array((-16,9,-7))
    base-=grime[...,None]*np.array((26,24,23))
    base-=scratches[...,None]*np.array((6,6,6))
    height=.008*haze+.028*scratches+.018*lamination+.036*mineral+.018*moisture
    rough=26+68*haze+56*scratches+29*lamination+124*grime+70*mineral
    ao=255-24*scratches-42*mineral-25*moisture
    opacity=255-230*np.clip(1.30*grime+.14*scratches+.08*lamination,0,1)
    save_glazing("glaze_glass_repair",base,height,rough,ao,opacity)


# ---------- engineered growth cards ----------
def alpha_downsample(im: Image.Image, out: Path) -> None:
    a=np.asarray(im.convert("RGBA"),np.float32)
    al=a[...,3:4]/255
    prem=np.concatenate((a[...,:3]*al,a[...,3:4]),2).astype(np.uint8)
    sm=np.asarray(Image.fromarray(prem,"RGBA").resize((1024,1024),Image.Resampling.LANCZOS),np.float32)
    sa=sm[...,3:4]
    rgb=np.where(sa>0,np.clip(sm[...,:3]*255/np.maximum(sa,1),0,255),0)
    Image.fromarray(np.concatenate((rgb,sa),2).astype(np.uint8),"RGBA").save(out,optimize=True)


def leaf_points(cx,cy,length,width,ang,lobes=0,hook=0.0):
    ca,sa=math.cos(ang),math.sin(ang); pts=[]
    for i in range(40):
        t=math.tau*i/40
        along=math.cos(t)*length/2
        across=math.sin(t)*width/2*(abs(math.sin(t))**.38)
        if lobes: across*=1+.20*math.sin((lobes*2+1)*t)
        along += hook*(math.sin(t)**2)*length*.22
        pts.append((cx+along*ca-across*sa,cy+along*sa+across*ca))
    return pts


def draw_leaf(d,cx,cy,length,width,ang,color,lobes=0,split=False,hook=0.0):
    if split:
        # A crop-like blade that bifurcates into an anatomically wrong fork.
        for da in (-.22,.22):
            d.polygon(leaf_points(cx+math.cos(ang)*length*.08,cy+math.sin(ang)*length*.08,
                                  length*.82,width*.55,ang+da,lobes,hook),fill=color)
    else:
        d.polygon(leaf_points(cx,cy,length,width,ang,lobes,hook),fill=color)
    ca,sa=math.cos(ang),math.sin(ang)
    d.line((cx-ca*length*.35,cy-sa*length*.35,cx+ca*length*.38,cy+sa*length*.38),
           fill=(27,59,31,190),width=max(3,int(width/24)))


def palette(rng):
    return rng.choice([(37,83,45,255),(46,101,48,255),(57,116,54,255),
                       (73,128,60,255),(91,125,63,255),(112,118,65,255)])


def tube_cling() -> None:
    im=Image.new("RGBA",(C,C),(0,0,0,0)); d=ImageDraw.Draw(im,"RGBA"); rng=random.Random(6101)
    # Two woody runners hug a horizontal member rather than sagging under gravity.
    for lane in (-34,34):
        pts=[]
        for i in range(18):
            x=110+i*105; y=1010+lane+32*math.sin(i*.78)+rng.randint(-9,9); pts.append((x,y))
        d.line(pts,fill=(48,76,39,255),width=24,joint="curve")
        for i,(x,y) in enumerate(pts[1:-1],1):
            if i%2:
                side=-1 if (i//2)%2 else 1; ang=side*(1.12+rng.uniform(-.16,.16))
                ex=x+math.cos(ang)*100; ey=y+math.sin(ang)*100
                d.line((x,y,ex,ey),fill=(52,88,43,255),width=10)
                draw_leaf(d,ex,ey,rng.randint(150,230),rng.randint(62,100),ang,palette(rng),
                          lobes=2 if i>9 else 0,split=i>12 and i%3==1,hook=.18 if i>8 else 0)
    # Circumferential gripping tendrils: repeated clamps around the unseen tube.
    for x in range(190,1900,210):
        d.arc((x-35,900,x+35,1115),75,292,fill=(91,110,52,255),width=12)
        d.ellipse((x-13,992,x+13,1018),fill=(132,118,63,255))
    alpha_downsample(im,CUT/"growth_tube_cling_1024.png")


def joint_mass() -> None:
    im=Image.new("RGBA",(C,C),(0,0,0,0)); d=ImageDraw.Draw(im,"RGBA"); rng=random.Random(6201); cx=cy=1030
    d.ellipse((650,650,1410,1410),fill=(39,67,35,245))
    for b in range(34):
        a=math.tau*b/34+rng.uniform(-.09,.09); length=rng.randint(430,830)
        pts: list[tuple[float, float]]=[(float(cx),float(cy))]
        for j in range(1,7):
            t=j/6; pts.append((cx+math.cos(a)*length*t+math.sin(t*9+b)*28,
                               cy+math.sin(a)*length*t+math.cos(t*7+b)*28))
        d.line(pts,fill=(43,78,38,240),width=rng.randint(9,18),joint="curve")
        if b%2==0:
            x,y=pts[-2]; mutated=b>16
            draw_leaf(d,x,y,rng.randint(155,260),rng.randint(75,145),a+rng.uniform(-.5,.5),
                      palette(rng),lobes=3 if mutated else 1,split=mutated and b%4==0,hook=.25)
    # Fasciated plates and nodules make the center botanical but not ivy-pretty.
    for _ in range(80):
        a=rng.random()*math.tau; r=380*(rng.random()**.7); x=cx+math.cos(a)*r; y=cy+math.sin(a)*r
        rr=rng.randint(18,54)
        d.ellipse((x-rr*1.3,y-rr,x+rr*1.3,y+rr),fill=rng.choice([(73,102,48,255),(96,109,54,255),(118,103,56,255)]))
    alpha_downsample(im,CUT/"growth_joint_mass_1024.png")


def creeping_mat() -> None:
    im=Image.new("RGBA",(C,C),(0,0,0,0)); d=ImageDraw.Draw(im,"RGBA"); rng=random.Random(6301)
    # Heat-seeking stolons all advance left-to-right across the floor plane.
    for lane in range(11):
        pts=[]
        for i in range(11):
            x=90+i*185; y=1180+(lane-5)*62+45*math.sin(i*.75+lane)
            pts.append((x,y))
        d.line(pts,fill=(48,77,38,235),width=rng.randint(8,15),joint="curve")
        for i,(x,y) in enumerate(pts[1:-1],1):
            if (i+lane)%3==0:
                ang=rng.choice([-.9,-.55,.55,.9]); mutated=x>1120
                draw_leaf(d,x,y,rng.randint(120,210),rng.randint(95,170),ang,palette(rng),
                          lobes=4 if mutated else 2,split=mutated and (i+lane)%2==0,hook=.2)
    # Rootlets point down; silhouette stays low and creeping, never a grass clump.
    for x in range(150,1940,85):
        y=1510+35*math.sin(x*.017)
        d.line((x,y,x+rng.randint(-22,22),y+rng.randint(80,170)),fill=(65,70,39,210),width=5)
    alpha_downsample(im,CUT/"growth_creeping_mat_1024.png")


def reaching() -> None:
    im=Image.new("RGBA",(C,C),(0,0,0,0)); d=ImageDraw.Draw(im,"RGBA"); rng=random.Random(6401)
    # Every stem aims at one warm target above-right, overriding normal phototropism.
    target=(1635,310); bases=[(280,1830),(520,1870),(760,1860),(1010,1880)]
    for bi,(bx,by) in enumerate(bases):
        pts=[]
        for j in range(9):
            t=j/8; x=bx*(1-t)+target[0]*t+math.sin(t*10+bi)*48*(1-t)
            y=by*(1-t)+target[1]*t+math.cos(t*8+bi)*30
            pts.append((x,y))
        d.line(pts,fill=(45,78,39,255),width=24-bi*3,joint="curve")
        for j,(x,y) in enumerate(pts[2:-1],2):
            if j%2==bi%2:
                ang=-.55+rng.uniform(-.22,.22)
                ex=x+math.cos(ang)*115; ey=y+math.sin(ang)*115
                d.line((x,y,ex,ey),fill=(50,91,43,245),width=9)
                draw_leaf(d,ex,ey,rng.randint(160,250),rng.randint(60,115),ang,palette(rng),
                          lobes=0 if j<4 else 3,split=j>=5,hook=.35)
    # Distal tendrils form grasping, finger-like forks at the shared target.
    for k in range(9):
        a=-1.15+k*.16
        reach=rng.randint(105,180)
        d.line((target[0]-80,target[1]+80,target[0]+math.cos(a)*reach,
                target[1]+math.sin(a)*reach),fill=(91,111,49,245),width=7)
    alpha_downsample(im,CUT/"growth_reaching_1024.png")


def main() -> None:
    glaze_acrylic_original(); glaze_glass_repair()
    tube_cling(); joint_mass(); creeping_mat(); reaching()
    print("generated 10 glazing maps and 4 engineered-growth RGBA cards")


if __name__ == "__main__":
    main()
