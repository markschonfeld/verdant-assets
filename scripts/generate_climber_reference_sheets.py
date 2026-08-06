#!/usr/bin/env python3
"""Generate VERDANT climber modelling sheets and species-specific RGBA cards.

The drawings are deterministic design-intent references, not botanical plates.
Recognisable morphology is preserved at the jamb, then subtly redirected toward
the warm doorway across the trellis head to support Eden Prime's story logic.
"""
from __future__ import annotations

from math import atan2, cos, pi, sin
from pathlib import Path
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "references" / "botanical"
CUT = ROOT / "cutouts"
REF.mkdir(parents=True, exist_ok=True)
CUT.mkdir(parents=True, exist_ok=True)

W, H = 2400, 1800
BG = (231, 226, 210)
PANEL = (216, 216, 202)
INK = (31, 38, 39)
MUTED = (84, 89, 82)
ACCENT = (132, 65, 34)
WHITE = (248, 246, 238)
GALV = (122, 137, 132)
GALV_L = (174, 184, 174)
GALV_D = (64, 76, 74)
STEM = (64, 78, 38)
STEM_OLD = (89, 72, 43)
LEAF_D = (34, 77, 43)
LEAF = (54, 105, 52)
LEAF_L = (91, 137, 67)
YELLOW = (211, 166, 61)
PURPLE = (93, 40, 48)
PIPE = (142, 129, 73)
PIPE_D = (72, 47, 54)

REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def font(size: int, bold: bool = False, mono: bool = False):
    return ImageFont.truetype(MONO if mono else (BOLD if bold else REG), size)


def line(d, pts, fill=INK, width=4):
    d.line(pts, fill=fill, width=width, joint="curve")


def ellipse(d, box, fill, outline=INK, width=3):
    d.ellipse(box, fill=fill, outline=outline, width=width)


def wrapped(d, xy, text, fnt, fill, max_width, spacing=6):
    words, rows, row = text.split(), [], ""
    for word in words:
        trial = word if not row else f"{row} {word}"
        if d.textbbox((0, 0), trial, font=fnt)[2] <= max_width:
            row = trial
        else:
            rows.append(row); row = word
    if row:
        rows.append(row)
    x, y = xy
    for row in rows:
        d.text((x, y), row, font=fnt, fill=fill)
        y += fnt.size + spacing
    return y


def title(d, index, name, subtitle):
    d.text((96, 68), f"VERDANT / BOTANICAL STUDY {index}", font=font(28, mono=True), fill=ACCENT)
    d.text((96, 112), name, font=font(66, bold=True), fill=INK)
    d.text((100, 205), subtitle, font=font(27), fill=MUTED)
    line(d, [(96, 260), (2304, 260)], MUTED, 3)


def note_box(d, box, heading, body):
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, radius=18, fill=(244, 241, 230), outline=ACCENT, width=3)
    d.text((x0 + 24, y0 + 18), heading.upper(), font=font(21, bold=True, mono=True), fill=ACCENT)
    wrapped(d, (x0 + 24, y0 + 54), body, font(20), INK, x1 - x0 - 48, 5)


def callout(d, anchor, elbow, boxxy, number, heading, body, width=560):
    ax, ay = anchor; ex, ey = elbow; bx, by = boxxy
    line(d, [(ax, ay), (ex, ey), (bx, ey)], ACCENT, 4)
    ellipse(d, (ax-10, ay-10, ax+10, ay+10), ACCENT, WHITE, 2)
    ellipse(d, (bx-23, ey-23, bx+23, ey+23), ACCENT, ACCENT, 1)
    tw = d.textbbox((0, 0), str(number), font=font(23, bold=True))[2]
    d.text((bx-tw/2, ey-16), str(number), font=font(23, bold=True), fill=WHITE)
    d.text((bx+38, by), heading.upper(), font=font(21, bold=True, mono=True), fill=ACCENT)
    wrapped(d, (bx+38, by+34), body, font(22), INK, width-38, 5)


def leaf_shape(cx, cy, length, width, angle, kind):
    ca, sa = cos(angle), sin(angle)
    if kind == "aristolochia":
        # One continuous cordate perimeter: basal sinus -> left lobe -> apex ->
        # right lobe -> sinus. Cubic curves avoid the triangular notch artifacts
        # produced by inserting points into an already-closed ellipse.
        def bez(p0, p1, p2, p3, steps=28):
            out=[]
            for j in range(steps):
                t=j/(steps-1); q=1-t
                out.append((q**3*p0[0]+3*q*q*t*p1[0]+3*q*t*t*p2[0]+t**3*p3[0],
                            q**3*p0[1]+3*q*q*t*p1[1]+3*q*t*t*p2[1]+t**3*p3[1]))
            return out
        sinus=(-length*.31,0)
        left_base=(-length*.43,width*.18)
        apex=(length*.50,0)
        right_base=(-length*.43,-width*.18)
        local=bez(sinus,(-length*.48,width*.09),(-length*.33,width*.55),left_base)
        local+=bez(left_base,(-length*.05,width*.62),(length*.36,width*.30),apex)[1:]
        local+=bez(apex,(length*.36,-width*.30),(-length*.05,-width*.62),right_base)[1:]
        local+=bez(right_base,(-length*.48,-width*.09),(-length*.36,-width*.035),sinus)[1:]
        return [(cx+x*ca-y*sa,cy+x*sa+y*ca) for x,y in local]
    pts = []
    # Local x runs base -> apex; widths are intentionally asymmetric.
    for i in range(45):
        t = i / 44
        x = -length * .46 + length * t
        profile = sin(pi * (t ** .92)) ** .72
        half = width * .5 * profile * (1.0 - .10*t)
        if t > .78:
            half *= (1 - (t-.78)*.8)
        pts.append((cx + x*ca - half*sa, cy + x*sa + half*ca))
    for i in range(44, -1, -1):
        t = i / 44
        x = -length * .46 + length * t
        profile = sin(pi * (t ** .92)) ** .72
        half = width * .5 * profile * (1.0 - .10*t)
        if t > .78:
            half *= (1 - (t-.78)*.8)
        pts.append((cx + x*ca + half*sa, cy + x*sa - half*ca))
    return pts


def draw_leaf(d, cx, cy, length, width, angle, kind, color=LEAF, underside=False):
    pts = leaf_shape(cx, cy, length, width, angle, kind)
    fill = (105, 132, 92) if underside else color
    d.polygon(pts, fill=fill, outline=INK)
    ca, sa = cos(angle), sin(angle)
    base = (cx-length*.46*ca, cy-length*.46*sa)
    tip = (cx+length*.50*ca, cy+length*.50*sa)
    line(d, [base, tip], (42, 80, 44), max(2, int(width/38)))
    for t in (.18, .34, .50, .66, .80):
        x = base[0] + (tip[0]-base[0])*t; y = base[1] + (tip[1]-base[1])*t
        # Keep secondary veins comfortably inside even the deep cordate base.
        span = width*(.20*(sin(pi*t)**.7))
        for side in (-1, 1):
            line(d, [(x, y), (x-ca*length*.03-side*sa*span, y-sa*length*.03+side*ca*span)],
                 (58, 96, 53), max(1, int(width/70)))
    # soft waxy highlight, no dramatic directional shadow
    line(d, [(base[0]+ca*length*.18, base[1]+sa*length*.18),
             (base[0]+ca*length*.62, base[1]+sa*length*.62)],
         (146, 169, 112), max(2, int(width/30)))


def draw_trellis(d):
    """Three-quarter upper-left doorway corner: jamb turns into head."""
    # back grid, stood proud of wall; diagonal offset gives thickness
    for x in (250, 470, 690, 910, 1130, 1350):
        line(d, [(x, 430), (x, 1450)], GALV_D, 11)
        line(d, [(x-8, 421), (x-8, 1441)], GALV_L, 4)
    for y in (520, 740, 960, 1180, 1400):
        line(d, [(210, y), (1450, y+110)], GALV_D, 11)
        line(d, [(210, y-7), (1450, y+103)], GALV_L, 4)
    # perimeter jamb/head with a pronounced turn at upper left of doorway void
    line(d, [(210, 1455), (210, 415), (1470, 525)], GALV_D, 34)
    line(d, [(198, 1440), (198, 400), (1476, 512)], GALV_L, 10)
    # small stand-off brackets establish that the frame is proud
    for x, y in ((210, 690), (210, 1180), (780, 466), (1300, 512)):
        line(d, [(x, y), (x+35, y-30)], GALV_D, 12)
        ellipse(d, (x+26, y-42, x+46, y-22), GALV_D, INK, 2)


def draw_helix_legend(d):
    d.rounded_rectangle((1110,1280,1575,1575),radius=16,fill=(241,238,226),outline=MUTED,width=3)
    d.text((1135,1302),"HELIX READ / PRODUCTION",font=font(18,bold=True,mono=True),fill=MUTED)
    line(d,[(1240,1360),(1240,1525)],GALV_D,18)
    d.arc((1170,1365,1310,1505),40,322,fill=STEM,width=13)
    d.polygon([(1308,1415),(1278,1403),(1294,1433)],fill=STEM)
    wrapped(d,(1335,1360),"Drawn ascending clockwise when viewed from outside the trellis. This is a production convention, not a species diagnostic. Mirror the whole plant if changed; never reverse mid-stem.",font(17),INK,210,4)


def draw_stem(d, pts, width=18, old=False):
    line(d, pts, STEM_OLD if old else STEM, width)
    line(d, [(x-2, y-3) for x, y in pts], (111, 128, 68), max(2, width//4))


def solandra_scene(d):
    draw_trellis(d)
    draw_helix_legend(d)
    rng = random.Random(7201)
    # Load-bearing woody runner grips the jamb then turns across the head.
    trunk = [(250,1460),(225,1320),(255,1190),(225,1050),(260,910),(230,770),(270,620),(245,500),
             (380,455),(540,485),(690,460),(850,500),(1020,488),(1190,530),(1390,528)]
    draw_stem(d, trunk, 32, True)
    # Helical contact marks clearly show repeated stem twining around the trellis.
    for x, y, horizontal in [(235,1260,False),(240,1020,False),(245,790,False),(265,555,False),
                             (480,470,True),(740,475,True),(1010,492,True),(1280,520,True)]:
        if horizontal:
            d.arc((x-52,y-34,x+52,y+34),195,520,fill=(72,91,42),width=13)
        else:
            d.arc((x-35,y-56,x+35,y+56),70,292,fill=(72,91,42),width=13)
    # Bearing nodes thicken where the runner turns and where long bridges begin.
    for x,y,r in [(250,500,38),(385,458,28),(690,470,26),(1010,495,28)]:
        ellipse(d,(x-r,y-r*.65,x+r,y+r*.65),(91,79,43),INK,3)
    # Gap bridge: self-supporting arc, then a hanging skirt from the underside.
    bridge=[(685,470),(765,390),(900,372),(1015,495)]
    draw_stem(d,bridge,19)
    hang=[(720,478),(760,650),(710,790),(760,930),(735,1100)]
    draw_stem(d,hang,15)
    # Large leathery leaves, fewer and heavier than Aristolochia.
    leaves=[(300,1180,230,105,-.45),(310,940,245,110,.18),(330,700,250,118,-.36),
            (470,475,240,110,-1.05),(600,500,250,112,.68),(820,410,245,110,-.70),
            (935,490,255,120,.82),(1130,500,250,115,-.75),(1320,535,245,110,.55),
            (770,720,235,108,.35),(720,900,250,115,2.20),(750,1070,230,105,.15)]
    for i,(x,y,l,w,a) in enumerate(leaves):
        draw_leaf(d,x,y,l,w,a,"solandra",LEAF_L if i in (1,5,9) else LEAF)
    # Cup flowers hang at the corner and under the head; model as heavy trumpet volumes.
    for x,y,s,a in [(430,560,1.0,.25),(970,610,.84,-.15),(745,1120,.72,.2)]:
        draw_solandra_flower(d,x,y,s,a)
    # Story override: distal tip straightens and reaches warm doorway instead of light.
    reach=[(1190,530),(1330,560),(1450,650),(1515,760)]
    draw_stem(d,reach,13)
    for x,y,a in [(1340,580,.4),(1450,675,.75)]:
        draw_leaf(d,x,y,190,72,a,"solandra",(107,125,62))


def draw_solandra_flower(d, x, y, scale=1.0, angle=0.0):
    # Side/three-quarter trumpet: narrow calyx throat, broad folded five-lobed cup.
    ca, sa = cos(angle), sin(angle)
    def tr(px,py): return (x+(px*ca-py*sa)*scale, y+(px*sa+py*ca)*scale)
    tube=[tr(-105,-28),tr(15,-42),tr(120,-92),tr(145,-58),tr(120,0),tr(150,58),tr(118,92),tr(15,44),tr(-105,28)]
    d.polygon(tube,fill=YELLOW,outline=INK)
    for off in (-42,-20,0,20,42):
        line(d,[tr(-25,off*.5),tr(110,off)],PURPLE,max(3,int(5*scale)))
    # five soft lobe tips around cup rim
    for px,py in [(145,-58),(165,-20),(162,24),(145,60),(126,0)]:
        ellipse(d,(tr(px-14,py-12)[0],tr(px-14,py-12)[1],tr(px+14,py+12)[0],tr(px+14,py+12)[1]),
                (231,190,81),INK,2)
    # pentagonal green calyx and pedicel
    line(d,[tr(-170,0),tr(-98,0)],STEM,11)
    d.polygon([tr(-112,-30),tr(-82,-17),tr(-95,0),tr(-82,17),tr(-112,30)],fill=(71,103,50),outline=INK)


def aristolochia_scene(d):
    draw_trellis(d)
    draw_helix_legend(d)
    rng=random.Random(7301)
    # Several slender twining stems make a layered cloak rather than one ropey trunk.
    paths=[]
    for lane in range(4):
        pts=[]
        for i in range(11):
            y=1460-i*98
            x=250+lane*30+42*sin(i*.92+lane)
            pts.append((x,y))
        pts += [(360+lane*40,455+lane*9),(560+lane*60,470+lane*6),(820+lane*65,485+lane*5),
                (1100+lane*55,505+lane*6),(1400,530+lane*8)]
        paths.append(pts); draw_stem(d,pts,15 if lane<2 else 11,old=lane==0)
    # Explicit repeated helices; all stems keep the same drawn handedness.
    for x,y in [(250,1280),(250,1050),(250,820),(255,600),(480,468),(720,480),(980,500),(1250,520)]:
        d.arc((x-38,y-48,x+38,y+48),62,298,fill=(70,91,43),width=10)
    # Broad overlapping heart-shaped screen, denser at the turn.
    leaves=[]
    for i in range(25):
        if i<11:
            x=315+rng.randint(-65,120); y=1360-i*82+rng.randint(-28,28)
        else:
            x=420+(i-11)*76+rng.randint(-35,35); y=500+rng.randint(-95,125)
        leaves.append((x,y,rng.randint(190,275),rng.randint(170,250),rng.uniform(-1.1,1.1)))
    # extra knot at jamb-to-head corner
    leaves += [(350,470,300,275,-.55),(450,430,285,260,.30),(390,570,270,250,1.0)]
    for i,(x,y,l,w,a) in enumerate(leaves):
        draw_leaf(d,x,y,l,w,a,"aristolochia",LEAF_L if i%7==0 else LEAF)
    # Hanging flowers stay tucked beneath the leaf cloak, concentrated at the turn.
    for x,y,s,a in [(360,640,1.0,.1),(480,610,.85,-.2),(700,610,.82,.12),(1130,640,.72,-.08)]:
        draw_pipe_flower(d,x,y,s,a)
    # A free runner bridges one bay then becomes too straight toward the door warmth.
    bridge=[(800,500),(875,610),(980,670),(1120,650),(1260,590),(1450,650),(1535,760)]
    draw_stem(d,bridge,12)
    for x,y,a in [(930,645,.4),(1190,625,-.5),(1425,675,.75)]:
        draw_leaf(d,x,y,205,180,a,"aristolochia",(99,124,61))


def draw_pipe_flower(d,x,y,scale=1.0,angle=0.0):
    ca,sa=cos(angle),sin(angle)
    def tr(px,py): return (x+(px*ca-py*sa)*scale,y+(px*sa+py*ca)*scale)
    # Pedicel -> swollen utricle -> bent tube -> three-lobed dark mouth.
    line(d,[tr(-110,-60),tr(-48,-25)],STEM,max(5,int(9*scale)))
    body=[tr(-55,-28),tr(-15,-52),tr(30,-44),tr(54,-14),tr(45,18),tr(82,42),tr(70,70),
          tr(30,55),tr(6,30),tr(-24,48),tr(-54,22)]
    d.polygon(body,fill=PIPE,outline=INK)
    mouth=[tr(68,38),tr(115,16),tr(105,54),tr(134,75),tr(94,87),tr(70,70)]
    d.polygon(mouth,fill=PIPE_D,outline=INK)
    # throat seam and restrained veins
    line(d,[tr(-18,-35),tr(35,-20),tr(76,50)],(103,66,55),max(2,int(4*scale)))
    for oy in (-20,0,20): line(d,[tr(15,oy),tr(92,52+oy*.25)],PURPLE,max(2,int(3*scale)))


def draw_bark_sample(d, start, end, width, base, seed, fissures, young=False):
    """Even-lit cylindrical stem close-up with deterministic longitudinal grain."""
    x0,y0=start; x1,y1=end; dx=x1-x0; dy=y1-y0
    length=(dx*dx+dy*dy)**.5; ux,uy=dx/length,dy/length; nx,ny=-uy,ux
    line(d,[start,end],INK,width+8)
    line(d,[start,end],base,width)
    # Broad side bands describe roundness without directional cast shadow.
    line(d,[(x0+nx*width*.23,y0+ny*width*.23),(x1+nx*width*.23,y1+ny*width*.23)],
         tuple(min(255,c+28) for c in base),max(4,width//8))
    line(d,[(x0-nx*width*.31,y0-ny*width*.31),(x1-nx*width*.31,y1-ny*width*.31)],
         tuple(max(0,c-27) for c in base),max(4,width//7))
    rng=random.Random(seed)
    if not young:
        for i in range(fissures):
            lateral=rng.uniform(-.34,.34)*width
            a=rng.uniform(.05,.28); b=rng.uniform(.58,.95)
            pts=[]
            for j in range(7):
                t=a+(b-a)*j/6
                wob=sin(t*18+i)*rng.uniform(2,7)
                pts.append((x0+dx*t+nx*(lateral+wob),y0+dy*t+ny*(lateral+wob)))
            line(d,pts,(64,53,35),rng.randint(2,max(3,width//18)))
    else:
        # Young epidermis: sparse lenticel-like marks, no mature plate texture.
        for _ in range(max(5,fissures//2)):
            t=rng.uniform(.12,.9); lateral=rng.uniform(-.27,.27)*width
            cx=x0+dx*t+nx*lateral; cy=y0+dy*t+ny*lateral
            line(d,[(cx-ux*8,cy-uy*8),(cx+ux*8,cy+uy*8)],(72,91,47),2)
    # Cut end shows pith/cambium only as a modelling cue, not a material map.
    ex,ey=x1,y1
    ellipse(d,(ex-width*.48,ey-width*.34,ex+width*.48,ey+width*.34),
            tuple(min(255,c+34) for c in base),(52,48,33),3)
    ellipse(d,(ex-width*.14,ey-width*.10,ex+width*.14,ey+width*.10),(119,103,65),None,1)


def bark_swatch(d, box, base, seed, split_count, polished=False):
    x0,y0,x1,y1=box
    d.rounded_rectangle(box,radius=14,fill=base,outline=INK,width=3)
    rng=random.Random(seed)
    for i in range(split_count):
        x=rng.randint(x0+18,x1-18)
        pts=[]
        for j in range(7):
            y=y0+18+(y1-y0-36)*j/6
            pts.append((x+sin(j*1.4+i)*rng.uniform(2,9),y))
        line(d,pts,(63,50,34),rng.randint(2,5))
    if polished:
        d.rounded_rectangle((x0+28,y0+44,x1-28,y1-42),radius=24,outline=(176,157,103),width=14)
        d.text((x0+44,y1-70),"compressed contact face",font=font(16,mono=True),fill=WHITE)


def make_stem_bark_sheet():
    im=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(im)
    title(d,"05","CLIMBER STEM + BARK SURFACES","Close modelling reference / age transition / bearing contact / texture scale")
    d.rounded_rectangle((70,300,1640,1660),radius=26,fill=PANEL,outline=(150,151,141),width=3)
    line(d,[(105,930),(1605,930)],(150,151,141),3)

    # SOLANDRA — heavier, ropey, corking mature runner.
    d.text((110,330),"A / SOLANDRA MAXIMA",font=font(25,bold=True,mono=True),fill=ACCENT)
    d.text((110,368),"smooth green shoot → corking bearing runner",font=font(20),fill=MUTED)
    d.text((145,430),"YOUNG / 1×",font=font(16,mono=True),fill=MUTED)
    d.text((600,430),"MATURE / ~1.8×",font=font(16,mono=True),fill=MUTED)
    d.text((1050,430),"BEARING / ~2.7×",font=font(16,mono=True),fill=MUTED)
    d.text((1350,365),"RELATIVE, NOT MEASURED",font=font(15,mono=True),fill=MUTED)
    draw_bark_sample(d,(150,520),(570,500),48,(75,104,51),7501,8,young=True)
    draw_bark_sample(d,(600,520),(1030,505),88,(116,91,50),7502,14)
    draw_bark_sample(d,(1050,520),(1530,500),132,(105,78,43),7503,23)
    # Node swelling and flattened trellis-bearing face.
    ellipse(d,(780,455,900,565),(128,96,49),INK,4)
    line(d,[(840,455),(840,420)],STEM,18)
    line(d,[(1215,390),(1215,655)],GALV_D,26)
    ellipse(d,(1135,448,1295,566),(130,101,55),INK,4)
    d.rounded_rectangle((1190,458,1250,556),radius=20,fill=(164,139,83),outline=INK,width=3)
    bark_swatch(d,(180,650,660,860),(105,78,43),7510,28)
    bark_swatch(d,(700,650,1180,860),(105,78,43),7511,17,polished=True)
    d.text((200,875),"ropey longitudinal cork / no large plates",font=font(17,mono=True),fill=MUTED)
    d.text((720,875),"bearing face: flatter, smoother, slightly lighter",font=font(17,mono=True),fill=MUTED)

    # ARISTOLOCHIA — slim, smooth green to shallow-split brown.
    d.text((110,965),"B / ARISTOLOCHIA MACROPHYLLA",font=font(25,bold=True,mono=True),fill=ACCENT)
    d.text((110,1003),"slender green twiner → thin brown bark with shallow vertical splits",font=font(20),fill=MUTED)
    d.text((145,1060),"YOUNG / 1×",font=font(16,mono=True),fill=MUTED)
    d.text((630,1060),"MATURE / ~1.7×",font=font(16,mono=True),fill=MUTED)
    d.text((1080,1060),"BEARING / ~2.2×",font=font(16,mono=True),fill=MUTED)
    draw_bark_sample(d,(150,1140),(610,1120),28,(69,101,51),7601,8,young=True)
    draw_bark_sample(d,(630,1140),(1060,1125),50,(100,82,50),7602,11)
    draw_bark_sample(d,(1080,1140),(1530,1120),66,(91,72,45),7603,14)
    # Modest node and woolly bud; never the Solandra-sized boss.
    ellipse(d,(800,1090,868,1160),(111,88,49),INK,3)
    line(d,[(834,1094),(850,1048)],STEM,10)
    for ox,oy in [(850,1046),(856,1042),(845,1038),(862,1051)]:
        ellipse(d,(ox-5,oy-5,ox+5,oy+5),(184,175,139),None,1)
    line(d,[(1240,1045),(1240,1260)],GALV_D,18)
    d.arc((1195,1065,1285,1225),65,300,fill=(89,72,45),width=18)
    bark_swatch(d,(180,1280,660,1510),(91,72,45),7610,17)
    bark_swatch(d,(700,1280,1180,1510),(88,78,54),7611,8,polished=True)
    d.text((200,1525),"fine shallow splits / keep silhouette cylindrical",font=font(17,mono=True),fill=MUTED)
    d.text((720,1525),"contact polish is local, not a full glossy band",font=font(17,mono=True),fill=MUTED)

    callout(d,(1320,500),(1660,445),(1680,415),1,"Solandra age stack","Young stems are smooth olive green and relatively round. Mature bearing wood grows much thicker, browns, and develops ropey longitudinal cork. Avoid oak-like plates, deep furrows, or generic tree bark.")
    callout(d,(1218,500),(1660,720),(1680,690),2,"Bearing deformation","At a trellis contact, widen the node, flatten only the loaded inner face, and polish the high-contact strip. Wet recesses remain darker and rougher; the whole circumference does not become smooth.")
    callout(d,(1320,1125),(1660,1000),(1680,970),3,"Aristolochia scale","Keep the mature pipevine visibly slimmer than Solandra. Brown bark receives shallow vertical splitting but retains a cylindrical silhouette. Nodes swell modestly; woolly buds are small, pale accents.")
    callout(d,(500,1390),(1660,1245),(1680,1215),4,"Texture orientation","All grain and fissures follow the stem axis, bending continuously through the helix. Break repetition at nodes and contacts. Do not project one straight bark tile across a turn without rotating its grain.")
    note_box(d,(1665,1410,2310,1660),"Surface response","Young epidermis: moist satin, low micro-relief. Solandra mature cork: dry roughness with rounded ridges and darker damp seams. Aristolochia mature bark: finer and less deeply relieved. Bearing polish raises highlight response only on compressed faces. Story mutation changes directional growth and proportion first; bark should not become thorny, diseased, or fantasy-scaled.")
    path=REF/"climber_stem_bark_surface_reference_2400x1800.png"
    im.save(path,optimize=True)
    return path


def make_sheet(kind):
    im=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(im)
    if kind=="solandra":
        title(d,"03","CUP OF GOLD / SOLANDRA MAXIMA","Three-quarter trellis study / heavy woody twiner / architectural leaves + cups")
    else:
        title(d,"04","DUTCHMAN'S PIPE / A. MACROPHYLLA","Three-quarter trellis study / slender twiner / overlapping leaf cloak + pipe flower")
    d.rounded_rectangle((70,300,1640,1660),radius=26,fill=PANEL,outline=(150,151,141),width=3)
    # even grounding shadow only; specimen itself has no dramatic key light
    sh=Image.new("RGBA",im.size,(0,0,0,0)); sd=ImageDraw.Draw(sh)
    sd.ellipse((160,1390,1450,1600),fill=(0,0,0,32)); sh=sh.filter(ImageFilter.GaussianBlur(25))
    im.paste(sh,(0,0),sh); d=ImageDraw.Draw(im)
    if kind=="solandra": solandra_scene(d)
    else: aristolochia_scene(d)

    if kind=="solandra":
        callout(d,(246,990),(1660,470),(1680,440),1,"Grip + bearing wood","A vigorous woody runner coils around the trellis itself. At repeated contact points, flatten the inner face and swell the node; keep free spans slimmer. Show one consistent helical hand across an individual plant.")
        callout(d,(375,490),(1660,710),(1680,680),2,"Corner mass","Both: a dense bearing knot above the turn, then a heavy hanging skirt below it. Large cups and leaves pull downward while the main runner remains locked to jamb and head.")
        callout(d,(850,390),(1660,950),(1680,920),3,"Bridge + hang","Across one open bay, the mature stem can hold a shallow self-supporting arc. Secondary shoots and flowers hang; they do not all trace the grid mechanically.")
        callout(d,(1450,675),(1660,1190),(1680,1160),4,"Research-subject resolve","Begin with glossy broad-elliptic crop morphology. Toward doorway warmth, straighten the distal runner, tighten its grip, and let leaf proportion narrow subtly—recognisable first, wrong only at the edge.")
        note_box(d,(1665,1410,2310,1660),"Material / surface callout","Old bearing stems: ropey tan-brown bark with shallow longitudinal fissures and compressed, polished contact faces. Young stems: smooth olive green. Leaves: thick, leathery, glossy dark green above; lighter and duller below, with a strong pale midrib. Flowers: waxy cream-to-gold trumpet, five rolled lobes, violet-brown bands deep in the cup. Keep lighting broad and even.")
        path=REF/"solandra_maxima_trellis_reference_2400x1800.png"
    else:
        callout(d,(250,1030),(1660,470),(1680,440),1,"Twining scaffold","Multiple slender stems wrap the trellis with repeated, same-handed helices. Young stems are green and stiff; older load-bearing runs brown, remain relatively slim, and gain shallow vertical fissures.")
        callout(d,(385,505),(1660,710),(1680,680),2,"Corner mass","A dense knot and a hanging skirt occur together: overlapping heart leaves cloak the outside of the turn, while flowers remain tucked in shade beneath the foliage and hang into the doorway edge.")
        callout(d,(900,640),(1660,950),(1680,920),3,"Bridge + leaf cloak","A stem can bridge one trellis bay before finding the next member. Alternate, large cordate leaves overlap like shingles; preserve small gaps so the screen reads as vegetation, not one solid blob.")
        callout(d,(390,640),(1660,1190),(1680,1160),4,"Pipe flower","Build three linked volumes: swollen basal chamber, bent narrow tube, and a brown-purple three-lobed mouth. Hang it from a leaf axil and partly conceal it. It should feel engineered before mutation is added.")
        note_box(d,(1665,1410,2310,1660),"Material / surface callout","Stems: smooth green when young, brown with shallow vertical splits when mature; small woolly buds at nodes. Leaves: 15–30 cm, smooth cordate silhouette, dark matte-satin green above and pale silver-green below. Flowers: yellow-green tube with brown-purple lobes and restrained veins. Story variation belongs in direction and proportion, not random thorns or generic ivy lobing.")
        path=REF/"aristolochia_dutchmans_pipe_trellis_reference_2400x1800.png"
    im.save(path,optimize=True)
    return path


def alpha_downsample(im, out):
    import numpy as np
    a=np.asarray(im.convert("RGBA"),np.float32); al=a[...,3:4]/255
    prem=np.concatenate((a[...,:3]*al,a[...,3:4]),2).astype(np.uint8)
    sm=np.asarray(Image.fromarray(prem,"RGBA").resize((1024,1024),Image.Resampling.LANCZOS),np.float32)
    sa=sm[...,3:4]; rgb=np.where(sa>0,np.clip(sm[...,:3]*255/np.maximum(sa,1),0,255),0)
    Image.fromarray(np.concatenate((rgb,sa),2).astype(np.uint8),"RGBA").save(out,optimize=True)


def make_leaf_card(kind):
    S=2048; im=Image.new("RGBA",(S,S),(0,0,0,0)); d=ImageDraw.Draw(im,"RGBA")
    if kind=="solandra":
        line(d,[(1030,1600),(1030,1920)],(82,83,43,255),34)
        draw_leaf(d,1030,940,1540,700,-pi/2,"solandra",(55,111,55,255))
        out=CUT/"solandra_maxima_leaf_flat_1024.png"
    else:
        line(d,[(1020,1340),(1020,1905)],(76,83,43,255),34)
        draw_leaf(d,1020,940,1460,1320,-pi/2,"aristolochia",(48,103,55,255))
        out=CUT/"aristolochia_leaf_flat_1024.png"
    alpha_downsample(im,out); return out


def make_pipe_card():
    S=2048; im=Image.new("RGBA",(S,S),(0,0,0,0)); d=ImageDraw.Draw(im,"RGBA")
    draw_pipe_flower(d,950,980,7.0,-.18)
    alpha_downsample(im,CUT/"aristolochia_pipe_flower_1024.png")
    return CUT/"aristolochia_pipe_flower_1024.png"


def main():
    paths=[make_sheet("solandra"),make_sheet("aristolochia"),make_leaf_card("solandra"),
           make_leaf_card("aristolochia"),make_pipe_card(),make_stem_bark_sheet()]
    for p in paths: print(p)


if __name__=="__main__":
    main()
