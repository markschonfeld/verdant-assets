#!/usr/bin/env python3
"""Deterministic VERDANT Batch 1 asset generator.

Textures use only periodic/toroidal functions and wrapped drawing, so the
2048px exports are genuinely seamless and reproducible. Posters are composed
programmatically so all slogan text remains exact and legible.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "textures"
POST = ROOT / "posters"
TEX.mkdir(exist_ok=True)
POST.mkdir(exist_ok=True)
N = 2048
RNG = random.Random(1961)


def periodic_noise(n: int, seed: int, octaves=((2, .45), (5, .25), (11, .16), (23, .09), (47, .05))):
    """Smooth 2D Fourier noise on a torus, normalized 0..1."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    x *= 2 * np.pi / n
    y *= 2 * np.pi / n
    z = np.zeros((n, n), np.float32)
    for freq, amp in octaves:
        for _ in range(3):
            a, b = rng.integers(1, freq + 1, size=2)
            phase = rng.random() * 2 * np.pi
            z += amp * np.sin(a * x + b * y + phase)
    z -= z.min()
    z /= max(float(z.max()), 1e-6)
    return z


def rgb_from(base, noise, scale=1.0):
    b = np.asarray(base, np.float32)[None, None, :]
    delta = (noise[..., None] - .5) * scale
    return np.clip(b + delta, 0, 255).astype(np.uint8)


def wrapped_draw(draw: ImageDraw.ImageDraw, kind: str, box, fill, width=1, repeats=1):
    """Draw geometry on all nine torus-neighbor copies."""
    for ox in (-N, 0, N):
        for oy in (-N, 0, N):
            b = tuple(v + (ox if i % 2 == 0 else oy) for i, v in enumerate(box))
            if kind == "ellipse": draw.ellipse(b, fill=fill, width=width)
            elif kind == "rectangle": draw.rectangle(b, fill=fill, width=width)
            elif kind == "line": draw.line(b, fill=fill, width=width, joint="curve")


def save_texture(name: str, arr_or_img):
    img = arr_or_img if isinstance(arr_or_img, Image.Image) else Image.fromarray(arr_or_img, "RGB")
    # Duplicate opposite boundary pixels. The underlying functions are already
    # periodic; this makes edge equality machine-verifiable as well.
    a = np.array(img.convert("RGB"))
    a[-1, :, :] = a[0, :, :]
    a[:, -1, :] = a[:, 0, :]
    Image.fromarray(a).save(TEX / f"{name}_2048.png", optimize=True)


def soil():
    n1 = periodic_noise(N, 11)
    fine = periodic_noise(N, 12, ((19, .5), (43, .3), (89, .2)))
    y, x = np.mgrid[0:N, 0:N].astype(np.float32)
    # Broad, worked furrows with organic wobble but no directional lighting.
    wobble = 16 * np.sin(2*np.pi*y/N*3 + .7) + 9 * np.sin(2*np.pi*y/N*7)
    fur = (np.cos(2*np.pi*(x + wobble)/192) + 1) / 2
    tone = .55*n1 + .28*fine + .17*fur
    arr = rgb_from((57, 43, 31), tone, 42)
    im = Image.fromarray(arr)
    d = ImageDraw.Draw(im, "RGBA")
    rng = random.Random(1101)
    for _ in range(46):
        x0, y0 = rng.randrange(N), rng.randrange(N)
        # Tiny sprouts: paired leaves, seen orthographically.
        c = rng.choice([(65,105,49,210),(79,122,59,210),(89,134,62,190)])
        for dx in (-1, 1):
            wrapped_draw(d, "ellipse", (x0+dx*3-5, y0-7, x0+dx*3+5, y0+3), c)
        wrapped_draw(d, "ellipse", (x0-2,y0-2,x0+2,y0+7), (54,82,40,180))
    save_texture("soil_terrace", im)


def concrete():
    n1 = periodic_noise(N, 21)
    fine = periodic_noise(N, 22, ((13,.5),(31,.3),(73,.2)))
    arr = rgb_from((139, 137, 124), .68*n1+.32*fine, 35)
    im = Image.fromarray(arr)
    d = ImageDraw.Draw(im, "RGBA")
    # Board-form seams: quiet, irregular spacing, moss tucked into selected seams.
    # Keep a board interior at the texture boundary; this avoids turning the
    # tile edge itself into an obvious landmark when the material repeats.
    seams = [173, 515, 864, 1200, 1548, 1889]
    for i, y in enumerate(seams):
        d.line((0,y,N,y), fill=(71,70,61,120), width=6)
        d.line((0,y+7,N,y+7), fill=(174,168,148,70), width=2)
        if i % 2:
            for x in range(20, N, 75):
                a = 15 + 18*math.sin(x*.019+i)
                d.ellipse((x-16,y-5,x+25,y+8), fill=(54,78,43,int(max(0,a))))
    # Vertical board joints are staggered to avoid a grid landmark.
    for y0, xoff in [(0,198),(173,498),(515,78),(864,632),(1200,304),(1548,770),(1889,420)]:
        y1 = min(y0+350,N)
        for x in range(xoff, N, 620):
            d.line((x,y0,x,y1), fill=(87,84,73,80), width=4)
    rng = random.Random(2103)
    # Hairline cracks, drawn as short branching polylines well inside a torus.
    for _ in range(24):
        x, y = rng.randrange(N), rng.randrange(N)
        pts=[x,y]
        for _ in range(rng.randint(3,7)):
            x += rng.randint(-28,28); y += rng.randint(18,50); pts += [x,y]
        wrapped_draw(d, "line", tuple(pts), (66,64,57,115), width=2)
    # Vertical water staining without baked lighting.
    stain = Image.new("RGBA", (N,N)); sd=ImageDraw.Draw(stain,"RGBA")
    for x in range(80,N,187):
        w=30+(x*17)%44
        sd.rectangle((x,0,x+w,N),fill=(70,83,70,10+(x%17)))
    stain=stain.filter(ImageFilter.GaussianBlur(24))
    im=Image.alpha_composite(im.convert("RGBA"),stain).convert("RGB")
    save_texture("concrete_formed", im)


def steel():
    n1=periodic_noise(N,31)
    fine=periodic_noise(N,32,((7,.5),(29,.3),(83,.2)))
    arr=rgb_from((91,169,164),.7*n1+.3*fine,30)
    im=Image.fromarray(arr); d=ImageDraw.Draw(im,"RGBA")
    # Panel seams (offset, not centered) and a regular construction logic.
    for x in (173,857,1541):
        d.line((x,0,x,N),fill=(35,79,79,150),width=7)
        d.line((x+9,0,x+9,N),fill=(146,198,187,80),width=2)
    for y in (211,723,1235,1747):
        d.line((0,y,N,y),fill=(37,79,76,125),width=6)
    rng=random.Random(3104)
    # Chipped paint, modest scale and dispersed.
    for _ in range(220):
        x,y=rng.randrange(N),rng.randrange(N); rx=rng.randint(3,17); ry=rng.randint(2,10)
        col=rng.choice([(54,95,92,150),(165,116,72,150),(193,153,101,100),(49,69,68,130)])
        wrapped_draw(d,"ellipse",(x-rx,y-ry,x+rx,y+ry),col)
    # Rivets and small rust halos, no highlights/shadows.
    for x in (151,195,835,879,1519,1563):
        for y in range(42,N,128):
            wrapped_draw(d,"ellipse",(x-11,y-11,x+11,y+11),(143,81,48,65))
            wrapped_draw(d,"ellipse",(x-6,y-6,x+6,y+6),(55,76,73,235))
            d.line((x,y+7,x+((y//128)%3-1)*5,y+23),fill=(139,70,37,105),width=4)
    save_texture("steel_pastel_turquoise",im)


def stucco():
    n1=periodic_noise(N,41)
    fine=periodic_noise(N,42,((17,.45),(43,.35),(97,.2)))
    # Warm cream base with a coral cast; keep color variation fine-grained so
    # no large faded patch becomes a repetition landmark.
    arr=rgb_from((218,190,158),.74*n1+.26*fine,24)
    im=Image.fromarray(arr); d=ImageDraw.Draw(im,"RGBA")
    rng=random.Random(4105)
    # Fine plaster crazing: many tiny, non-directional fragments.
    for _ in range(185):
        x,y=rng.randrange(N),rng.randrange(N)
        ang=rng.random()*math.tau; length=rng.randint(10,38)
        x2=x+math.cos(ang)*length; y2=y+math.sin(ang)*length
        wrapped_draw(d,"line",(x,y,x2,y2),(104,91,74,70),width=1)
    # Diffuse grime as small toroidal mottles instead of a literal "bottom"
    # band, which would create a horizontal landmark in a world-space tile.
    for _ in range(55):
        x,y=rng.randrange(N),rng.randrange(N)
        rx,ry=rng.randint(25,85),rng.randint(6,20)
        wrapped_draw(d,"ellipse",(x-rx,y-ry,x+rx,y+ry),(76,79,61,rng.randint(5,15)))
    save_texture("stucco_cream",im)


def leaf_polygon(cx,cy,rx,ry,ang):
    ca,sa=math.cos(ang),math.sin(ang)
    pts=[]
    for i in range(20):
        t=math.tau*i/20
        # pointed broad leaf
        r=abs(math.sin(t))**.55
        lx=math.cos(t)*rx; ly=math.sin(t)*ry*r
        pts.append((cx+lx*ca-ly*sa,cy+lx*sa+ly*ca))
    return pts


def vine():
    base=rgb_from((31,66,39),periodic_noise(N,51),32)
    im=Image.fromarray(base); d=ImageDraw.Draw(im,"RGBA")
    rng=random.Random(5106)
    # Layered leaves in three scales. Wrapped copies guarantee continuity.
    palettes=[[(26,75,42,255),(38,92,48,255),(50,102,55,255)],
              [(35,89,47,255),(48,111,55,255),(63,123,66,255)],
              [(44,104,53,255),(59,127,65,255),(76,139,72,255)]]
    for layer,(count,size) in enumerate(((300,95),(390,68),(470,46))):
        for _ in range(count):
            cx,cy=rng.randrange(N),rng.randrange(N); rx=rng.randint(int(size*.55),size); ry=rng.randint(int(size*.25),int(size*.55)); ang=rng.random()*math.tau
            pts=leaf_polygon(cx,cy,rx,ry,ang)
            col=rng.choice(palettes[layer])
            for ox in (-N,0,N):
                for oy in (-N,0,N):
                    p=[(x+ox,y+oy) for x,y in pts]; d.polygon(p,fill=col)
                    # flat vein accents, no lighting cue
                    ca,sa=math.cos(ang),math.sin(ang)
                    d.line((cx+ox-rx*.65*ca,cy+oy-rx*.65*sa,cx+ox+rx*.65*ca,cy+oy+rx*.65*sa),fill=(21,62,34,100),width=max(1,int(size/30)))
    save_texture("overgrowth_vine",im)


# ---------- Posters ----------
PW, PH = 1024, 1536
CREAM=(238,222,179); INK=(35,56,48); GREEN=(42,94,57); MINT=(106,151,114)
CORAL=(202,92,70); GOLD=(221,166,72); RED=(144,55,47); TURQ=(74,146,144)
FONT_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def font(sz,bold=True): return ImageFont.truetype(FONT_BOLD if bold else FONT_REG,sz)

def fit_font(draw,text,maxw,start=92,minsize=36):
    for sz in range(start,minsize-1,-1):
        f=font(sz)
        if draw.textbbox((0,0),text,font=f)[2] <= maxw: return f
    return font(minsize)

def centered(draw,text,y,fill,maxw=870,start=92,spacing=8):
    f=fit_font(draw,text,maxw,start)
    bb=draw.textbbox((0,0),text,font=f)
    draw.text(((PW-(bb[2]-bb[0]))/2,y),text,font=f,fill=fill,stroke_width=0)
    return y+(bb[3]-bb[1])+spacing

def starburst(draw,cx,cy,r1,r2,n,fill):
    pts=[]
    for i in range(n*2):
        a=-math.pi/2+i*math.pi/n; r=r1 if i%2==0 else r2
        pts.append((cx+math.cos(a)*r,cy+math.sin(a)*r))
    draw.polygon(pts,fill=fill)

def footer(draw,number):
    draw.rectangle((0,1450,PW,PH),fill=INK)
    draw.text((54,1471),"EDEN PRIME CULTIVATION BUREAU",font=font(25),fill=CREAM)
    draw.text((882,1471),f"C-{number:02d}",font=font(25),fill=GOLD)

def poster_one():
    im=Image.new("RGB",(PW,PH),CREAM); d=ImageDraw.Draw(im)
    d.rectangle((0,0,PW,145),fill=TURQ); d.rectangle((0,145,PW,166),fill=CORAL)
    centered(d,"A GARDEN IS",38,CREAM,start=84)
    # Atomic sun and terraced fields.
    starburst(d,512,680,380,300,24,GOLD)
    d.ellipse((260,425,764,930),fill=(245,206,104))
    for y,col in [(890,GREEN),(970,MINT),(1050,GREEN),(1130,TURQ),(1210,GREEN)]:
        d.rectangle((0,y,PW,y+100),fill=col)
    # Hand entering from right, gently cupped around seedling.
    skin=(205,142,101); skin2=(185,116,82)
    d.polygon([(1024,780),(838,745),(705,805),(650,880),(688,925),(785,886),(900,900),(1024,940)],fill=skin)
    d.polygon([(1024,896),(830,862),(710,922),(670,980),(714,1014),(798,967),(920,976),(1024,1006)],fill=skin2)
    # Seedling and soil mound.
    d.ellipse((330,930,700,1080),fill=(82,57,41)); d.rectangle((508,790,522,975),fill=INK)
    d.ellipse((420,785,520,842),fill=GREEN); d.ellipse((516,754,628,822),fill=MINT)
    d.line((515,813,466,805),fill=INK,width=6); d.line((518,792,570,784),fill=INK,width=6)
    d.rectangle((74,1258,950,1424),fill=CREAM); centered(d,"NOT FREE.",1260,RED,start=86); centered(d,"A GARDEN IS LOVED.",1340,INK,start=73)
    footer(d,1); im.save(POST/"garden_loved_1024x1536.png",optimize=True)

def branch_shape(d,pts,width,color): d.line(pts,fill=color,width=width,joint="curve")
def leaf(d,x,y,s,col,flip=1):
    d.polygon([(x,y),(x+flip*s,y-s*.45),(x+flip*s*1.5,y),(x+flip*s,y+s*.45)],fill=col)

def poster_two():
    im=Image.new("RGB",(PW,PH),CREAM); d=ImageDraw.Draw(im)
    d.rectangle((0,0,PW,300),fill=CORAL)
    centered(d,"THE WILD BRANCH",48,CREAM,start=80)
    centered(d,"TAKES WATER FROM",136,INK,start=72)
    centered(d,"THE FRUITING BRANCH.",218,CREAM,start=68)
    # Reservoir wedge / water rising into a disciplined fruiting tree.
    d.polygon([(0,1290),(0,515),(380,920),(1024,500),(1024,1290)],fill=TURQ)
    d.polygon([(0,1290),(0,1040),(1024,770),(1024,1290)],fill=GREEN)
    # Main cultivated branch, laden with fruit.
    branch_shape(d,[(200,1260),(350,1050),(500,850),(650,665),(830,515)],38,INK)
    for x,y in [(390,1010),(500,870),(610,750),(715,640),(800,552)]:
        leaf(d,x,y,55,MINT,-1); leaf(d,x+10,y-35,48,GREEN,1)
    for x,y in [(470,950),(585,820),(695,700),(790,595)]:
        d.ellipse((x-30,y-30,x+30,y+30),fill=GOLD); d.ellipse((x-9,y-30,x+9,y-12),fill=RED)
    # Wild branch reaches left, stripped at the pruning point.
    branch_shape(d,[(500,850),(395,750),(275,650),(110,570)],24,RED)
    for x,y in [(365,730),(300,675),(220,625),(145,585)]:
        leaf(d,x,y,44,(65,112,68),-1 if x%2 else 1)
    # Shears: cheerful cream/chrome geometry, but poised at the fork.
    d.ellipse((395,750,490,845),outline=INK,width=20); d.ellipse((475,790,570,885),outline=INK,width=20)
    d.polygon([(455,790),(585,680),(610,700),(500,825)],fill=(192,202,184))
    d.polygon([(500,825),(630,745),(647,772),(535,850)],fill=(155,171,158))
    d.rectangle((70,1325,954,1425),fill=CREAM); centered(d,"WATER SERVES THE HARVEST.",1344,INK,start=52)
    footer(d,2); im.save(POST/"wild_branch_1024x1536.png",optimize=True)

def poster_three():
    im=Image.new("RGB",(PW,PH),INK); d=ImageDraw.Draw(im)
    d.rectangle((0,0,PW,175),fill=GOLD)
    centered(d,"PRUNING IS NOT DEATH.",52,INK,start=67)
    # Severe concentric geometry: a civic seal that also reads as an eye/sun.
    starburst(d,512,685,430,345,28,RED)
    d.ellipse((190,365,834,1009),fill=CREAM)
    d.ellipse((270,445,754,929),fill=CORAL)
    d.ellipse((355,530,669,844),fill=INK)
    # Upright branch transitions from cut stump to ordered topiary.
    d.rectangle((490,640,534,1190),fill=GREEN)
    d.polygon([(512,500),(420,625),(480,700),(512,660),(544,700),(604,625)],fill=MINT)
    d.polygon([(512,410),(440,540),(492,600),(512,570),(532,600),(584,540)],fill=GREEN)
    # Clean pruning cut and directional chevrons.
    d.ellipse((476,1145,548,1205),fill=GOLD)
    for y in (1040,1120,1200):
        d.polygon([(170,y),(310,y+45),(170,y+90),(210,y+45)],fill=GOLD)
        d.polygon([(854,y),(714,y+45),(854,y+90),(814,y+45)],fill=GOLD)
    d.rectangle((0,1260,PW,1450),fill=CREAM)
    centered(d,"PRUNING IS",1280,RED,start=82)
    centered(d,"DIRECTION.",1365,INK,start=92)
    footer(d,3); im.save(POST/"pruning_direction_1024x1536.png",optimize=True)


def main():
    soil(); concrete(); steel(); stucco(); vine()
    poster_one(); poster_two(); poster_three()
    print("Generated 8 assets")

if __name__ == "__main__": main()
