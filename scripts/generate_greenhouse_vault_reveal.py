#!/usr/bin/env python3
"""Generate the west-door greenhouse-vault reveal for VERDANT.

This is a reproducible art-direction image, not a measured construction drawing.
It fixes camera, massing, light, material eras, decay logic, and vegetation behavior
for the first view east from the entrance terrace.
"""
from __future__ import annotations

from math import cos, pi, sin
from pathlib import Path
import random

from PIL import Image, ImageDraw, ImageFilter

W, H = 2560, 1440
S = 2  # supersample for clean linework
OUT = Path(__file__).resolve().parents[1] / "references" / "environment"
OUT.mkdir(parents=True, exist_ok=True)
RNG = random.Random(4661524)


def sc(p):
    return tuple(int(v * S) for v in p)


def pts(seq):
    return [sc(p) for p in seq]


def line(draw, seq, fill, width: float = 1, joint="curve"):
    draw.line(pts(seq), fill=fill, width=max(1, int(width * S)), joint=joint)


def poly(draw, seq, fill, outline=None, width: float = 1):
    draw.polygon(pts(seq), fill=fill)
    if outline:
        line(draw, list(seq) + [seq[0]], outline, width)


def arch(depth: float, samples: int = 32):
    """Perspective barrel-vault section; depth 0=entrance, 1=far east end."""
    q = depth ** 0.72
    cx = 1280 + 238 * q
    half = 1120 * (1 - q) + 122 * q
    spring = 830 * (1 - q) + 612 * q
    rise = 900 * (1 - q) + 102 * q
    return [
        (cx + half * cos(pi - pi * i / samples), spring - rise * sin(pi * i / samples))
        for i in range(samples + 1)
    ]


def bezier(p0, p1, p2, p3, n=80):
    out = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        out.append((u**3*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t**3*p3[0],
                    u**3*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t**3*p3[1]))
    return out


def make_reveal():
    im = Image.new("RGB", (W*S, H*S), (22, 31, 27))
    d = ImageDraw.Draw(im)

    # Deep humid atmosphere: warm east haze under a cold, dirty envelope.
    for y in range(H*S):
        t = y / (H*S)
        col = (int(72 - 46*t), int(92 - 53*t), int(77 - 45*t))
        d.line([(0, y), (W*S, y)], fill=col)
    haze = Image.new("RGBA", im.size, (0, 0, 0, 0))
    hd = ImageDraw.Draw(haze)
    hd.ellipse(sc((1040, 285, 2200, 1110)), fill=(246, 201, 112, 92))
    haze = haze.filter(ImageFilter.GaussianBlur(250*S))
    im = Image.alpha_composite(im.convert("RGBA"), haze)
    d = ImageDraw.Draw(im)

    depths = [0.02, .10, .19, .29, .40, .52, .64, .75, .84, .91, .96, 1.0]
    arches = [arch(z) for z in depths]

    # Glazing skin: strips between successive sections, mixed by maintenance era.
    glass = Image.new("RGBA", im.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glass)
    for k in range(len(arches)-1):
        a, b = arches[k], arches[k+1]
        for i in range(32):
            newer = ((i*7 + k*5) % 17 in (1, 2, 9))
            base = (128, 143, 106, 46) if not newer else (135, 194, 190, 76)
            # Dirty original acrylic is warmer/cloudier; repairs are cooler/clearer.
            if not newer and ((i + 3*k) % 6 == 0):
                base = (126, 119, 76, 74)
            poly(gd, [a[i], a[i+1], b[i+1], b[i]], base)
    # Mineral/algae grime concentrated at lower glazing and selected runoff lanes.
    for _ in range(210):
        x = RNG.randint(150, 2410); y = RNG.randint(120, 840)
        r = RNG.randint(8, 48)
        gd.ellipse(sc((x-r*2, y-r/2, x+r*2, y+r/2)), fill=(73, 82, 48, RNG.randint(4, 15)))
    glass = glass.filter(ImageFilter.GaussianBlur(1.2*S))
    im = Image.alpha_composite(im, glass)
    d = ImageDraw.Draw(im)

    # Suspended fine glazing net, visually subordinate to structure.
    for k in range(len(arches)-1):
        a, b = arches[k], arches[k+1]
        for i in range(0, 32, 2):
            line(d, [a[i], b[min(32, i+1)]], (137, 156, 145, 74), 1.1)
            if i + 2 <= 32:
                line(d, [a[i+2], b[i+1]], (137, 156, 145, 62), 1.0)
    for a in arches:
        line(d, a, (155, 170, 159, 72), 1.2)

    # 3 m chalked aluminium lamella lattice: broad ribs + triangulated longitudinals.
    for k, a in enumerate(arches):
        strength = int(174 - k*6)
        line(d, a, (strength, strength+4, strength, 205), max(2.0, 8.0-k*.48))
        line(d, [(x, y+3) for x, y in a], (65, 78, 72, 180), max(1.0, 2.8-k*.13))
    for k in range(len(arches)-1):
        a, b = arches[k], arches[k+1]
        for i in range(0, 32, 4):
            j = min(32, i+4)
            line(d, [a[i], b[j]], (164, 171, 162, 154), max(1.2, 4.6-k*.23))
            line(d, [a[j], b[i]], (164, 171, 162, 154), max(1.2, 4.6-k*.23))
            # Steel fasteners: tiny dark points, rust reserved to runoff below them.
            bx, by = b[j]
            rr = max(1.2, 4.0-k*.19)
            d.ellipse(sc((bx-rr, by-rr, bx+rr, by+rr)), fill=(73, 65, 53, 220))
            if (i + 2*k) % 12 == 0:
                line(d, [(bx, by+rr), (bx+2, by+22+7*k)], (126, 73, 42, 125), max(.7, 1.8-k*.07))

    # Floor and central run: intact, drained, and deliberately closed rather than rubble-filled.
    vp = (1518, 602)
    poly(d, [(70, 1440), (820, 810), (1115, 686), vp, (1910, 740), (2560, 1200), (2560, 1440)], (47, 57, 46, 255))
    poly(d, [(480, 1440), (910, 820), (1210, 695), vp, (1695, 705), (2050, 1440)], (63, 67, 54, 255))
    # Stepped terraces down the length.
    terrace_z = [.05, .13, .23, .35, .48, .61, .73, .83, .90]
    for n, z in enumerate(terrace_z):
        q = z**.72
        y = 1320*(1-q) + 622*q
        xl = 470*(1-q) + 1432*q
        xr = 2110*(1-q) + 1604*q
        line(d, [(xl, y), (xr, y-20*q)], (154, 142, 101, 150), max(1.5, 7*(1-q)+1))
        if n < 7:
            line(d, [(xl, y+8), (xr, y-20*q+8)], (19, 27, 22, 150), max(1, 4*(1-q)))
    # Deliberate maintenance channel and terrace edge stripes.
    line(d, [(980, 1440), (1449, 615)], (180, 158, 94, 105), 4)
    line(d, [(1110, 1440), (1470, 615)], (35, 40, 34, 190), 3)

    # Pier colonnade establishes scale and cadence.
    for side in (-1, 1):
        for k, z in enumerate([.05, .16, .29, .43, .57, .69, .79, .87, .93]):
            q = z**.72
            x = (1280 + side*925)*(1-q) + (1518 + side*115)*q
            y0 = 1240*(1-q) + 625*q
            y1 = 720*(1-q) + 570*q
            w = 48*(1-q)+5
            poly(d, [(x-w, y0), (x+w, y0), (x+w*.55, y1), (x-w*.55, y1)], (103, 104, 88, 245), (31, 39, 34, 230), max(1, 2.5*(1-q)))
            # cap and chalked lime/mineral bloom
            line(d, [(x-w*1.2, y1), (x+w*1.2, y1)], (183, 180, 151, 210), max(1, 7*(1-q)))

    # Side service doors: intact, dogged shut, with warmth-seeking growth converging on seams.
    doors = [(330, 938, 555, 1275), (2210, 850, 2390, 1115)]
    for di, (x0,y0,x1,y1) in enumerate(doors):
        poly(d, [(x0,y0),(x1,y0+10),(x1,y1),(x0,y1)], (38, 58, 57, 255), (178, 160, 112, 220), 4)
        line(d, [((x0+x1)/2, y0+6), ((x0+x1)/2, y1)], (17, 27, 28, 230), 3)
        for yy in (y0+55, y0+145, y1-55):
            d.ellipse(sc((x0+22,yy-8,x0+38,yy+8)), fill=(71,65,52,255))
        # quarantine slash and surviving placard blocks; no generated lettering.
        line(d, [(x0+38,y0+45),(x1-38,y1-45)], (183, 146, 58, 190), 12)
        poly(d, [(x0+45,y0+82),(x1-45,y0+86),(x1-45,y0+150),(x0+45,y0+148)], (199,190,150,180), (62,57,44,180), 2)

    # Engineered/wrong vegetation: long runs obey aluminium paths, then bend toward warm doors.
    growth = Image.new("RGBA", im.size, (0,0,0,0)); vg = ImageDraw.Draw(growth)
    vines = [
        bezier((100,790),(520,520),(920,420),(1420,548)),
        bezier((2460,730),(2120,570),(1860,510),(1550,596)),
        bezier((290,560),(430,820),(420,900),(430,1070)),
        bezier((2340,510),(2290,690),(2305,790),(2300,925)),
        bezier((840,160),(980,310),(1170,430),(1485,550)),
    ]
    for idx, v in enumerate(vines):
        line(vg, v, (35,74,43,235), 11 if idx < 2 else 8)
        for j in range(5, len(v), 10):
            x,y=v[j]; ang=(-1 if j%20 else 1)
            leaf=[(x,y),(x+ang*22,y-14),(x+ang*43,y-8),(x+ang*25,y+8)]
            poly(vg, leaf, (50+idx*4,95+idx*3,51,205))
    # Tendrils gather unnaturally at door warmth and seams.
    for target in [(445,1045),(2295,955)]:
        tx,ty=target
        for n in range(10):
            sx = tx + RNG.randint(-260,260); sy = 700 + RNG.randint(-180,240)
            v=bezier((sx,sy),((sx+tx)/2,sy-80),(tx+RNG.randint(-50,50),ty-100),(tx,ty),35)
            line(vg,v,(32,68+RNG.randint(0,18),39,150),RNG.randint(2,5))
    im=Image.alpha_composite(im,growth)

    # Volumetric shafts through dirt: main event, from roof to terraces.
    shafts = Image.new("RGBA", im.size, (0,0,0,0)); sd=ImageDraw.Draw(shafts)
    shaft_polys=[
        ([(520,190),(720,230),(1320,1320),(1030,1370)],(255,220,139,88)),
        ([(1050,95),(1215,112),(1580,1180),(1370,1225)],(240,233,174,68)),
        ([(1700,155),(1840,185),(1840,1010),(1660,1030)],(249,211,130,78)),
        ([(2050,290),(2175,350),(2070,860),(1940,890)],(236,222,166,52)),
    ]
    for p,c in shaft_polys: poly(sd,p,c)
    shafts=shafts.filter(ImageFilter.GaussianBlur(22*S))
    im=Image.alpha_composite(im,shafts)

    # Foreground blast-door reveal frame: player has just crossed the threshold.
    d=ImageDraw.Draw(im)
    poly(d, [(0,0),(250,0),(320,1440),(0,1440)], (17,24,23,255))
    poly(d, [(2560,0),(2370,0),(2295,1440),(2560,1440)], (16,23,22,255))
    poly(d, [(0,0),(2560,0),(2350,120),(235,120)], (13,20,20,255))
    # Door jamb wear, gasket, and quarantine closure hardware remain intact.
    line(d, [(246,110),(310,1430)], (80,92,85,255), 22)
    line(d, [(2360,110),(2305,1430)], (80,92,85,255), 22)
    line(d, [(267,120),(326,1430)], (170,142,74,170), 4)

    # Filmic finishing: humid bloom, fine grain, and restrained vignette.
    bloom=im.filter(ImageFilter.GaussianBlur(16*S))
    im=Image.blend(im,bloom,.08)
    pix=im.load()
    assert pix is not None
    for y in range(H*S):
        ny=(y/(H*S)-.5)*2
        for x in range(W*S):
            nx=(x/(W*S)-.5)*2
            vig=max(0,(nx*nx+ny*ny-.45))*24
            r,g,b,a=pix[x,y]
            noise=RNG.randint(-3,3)
            pix[x,y]=(max(0,min(255,int(r-vig+noise))),max(0,min(255,int(g-vig+noise))),max(0,min(255,int(b-vig+noise))),a)

    im=im.convert("RGB").resize((W,H),Image.Resampling.LANCZOS)
    path=OUT/"greenhouse_vault_reveal_west_2560x1440.png"
    im.save(path,optimize=True)
    return path


if __name__ == "__main__":
    print(make_reveal())
