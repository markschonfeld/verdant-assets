#!/usr/bin/env python3
"""Generate the VERDANT climber branching-architecture production sheet.

This is an original diagram, not a botanical-photo collage. Public photo evidence
and licenses are linked separately in the companion Markdown reference.
"""
from math import sin, pi
from pathlib import Path
import random
from PIL import Image, ImageDraw

from generate_climber_reference_sheets import (
    W, H, BG, PANEL, INK, MUTED, ACCENT, LEAF, LEAF_L, STEM, STEM_OLD,
    font, line, wrapped, title, draw_leaf, draw_solandra_flower, draw_pipe_flower,
)

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"references"/"botanical"/"climber_branching_architecture_reference_2400x1800.png"
SOL=(126,112,53)
SOL_Y=(155,137,63)
ARI=(53,104,77)
ARI_Y=(71,133,94)
RED=(155,61,47)
TRELLIS=(93,98,92)


def bezier(p0,p1,p2,p3,n=30):
    pts=[]
    for i in range(n+1):
        t=i/n; u=1-t
        pts.append((u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0],
                    u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]))
    return pts


def branch(d,pts,color,width):
    line(d,pts,INK,width+4)
    line(d,pts,color,width)


def dot(d,x,y,r,color):
    d.ellipse((x-r,y-r,x+r,y+r),fill=color,outline=INK,width=2)


def small_leaf(d,x,y,kind,angle=0.0,scale=1.0,color=LEAF):
    if kind=="solandra": draw_leaf(d,x,y,56*scale,27*scale,angle,"solandra",color=color)
    else: draw_leaf(d,x,y,50*scale,45*scale,angle,"aristolochia",color=color)


def panel(d,box,heading,sub=None):
    d.rounded_rectangle(box,radius=22,fill=PANEL,outline=(150,151,141),width=3)
    x0,y0,_,_=box
    d.text((x0+28,y0+20),heading,font=font(22,bold=True,mono=True),fill=ACCENT)
    if sub: d.text((x0+28,y0+54),sub,font=font(19),fill=MUTED)


def wrong_spline(d):
    x0,y0=130,480
    pts=bezier((x0,y0+245),(x0+30,y0+90),(x0+80,y0+45),(x0+130,y0))
    branch(d,pts,STEM,14)
    for i,(x,y) in enumerate(pts[5::5]):
        small_leaf(d,x-18,y, "solandra", -0.55 if i%2 else 2.6,.72)
        if i in (1,4): draw_solandra_flower(d,x+22,y-4,.48,0.15)
    d.line((105,445,355,760),fill=RED,width=10)
    d.line((355,445,105,760),fill=RED,width=10)
    d.text((126,770),"ONE DECORATED SPLINE",font=font(18,bold=True,mono=True),fill=RED)


def correct_hierarchy(d):
    primary=bezier((500,745),(500,630),(555,520),(620,445))
    branch(d,primary,STEM_OLD,18)
    nodes=[primary[7],primary[14],primary[21],primary[27]]
    laterals=[]
    for i,(x,y) in enumerate(nodes):
        side=-1 if i%2==0 else 1
        lat=bezier((x,y),(x+55*side,y-15),(x+95*side,y-70),(x+125*side,y-100))
        branch(d,lat,SOL,10)
        laterals.append(lat)
        dot(d,x,y,9,SOL_Y)
        small_leaf(d,x-20*side,y+8,"solandra",0.35 if side>0 else 2.8,.72)
        # tertiary shoot from the retained lateral
        bx,by=lat[18]
        ter=bezier((bx,by),(bx-25*side,by-15),(bx-30*side,by-45),(bx-18*side,by-65))
        branch(d,ter,SOL_Y,6)
        for q in ter[9::10]: small_leaf(d,q[0],q[1],"solandra",0.5 if side>0 else 2.6,.48,color=LEAF_L)
        if i!=1: draw_solandra_flower(d,ter[-1][0],ter[-1][1]-4,.44,-.15*side)
    d.text((442,770),"PRIMARY → LATERAL → TERTIARY",font=font(18,bold=True,mono=True),fill=ACCENT)
    # enlarged axil at the lowest node
    x,y=nodes[0]
    line(d,[(x,y),(815,690),(865,690)],ACCENT,3)
    d.rounded_rectangle((855,610,1050,795),radius=14,fill=(246,243,233),outline=ACCENT,width=3)
    branch(d,[(920,760),(920,650)],STEM,14)
    branch(d,[(920,700),(985,645)],SOL,8)
    small_leaf(d,900,700,"solandra",2.7,.72)
    dot(d,920,700,8,SOL_Y)
    d.text((875,625),"AXIL",font=font(17,bold=True,mono=True),fill=ACCENT)
    wrapped(d,(870,720),"bud produces lateral",font(16),INK,165,4)


def draw_trellis_network(d):
    # three-sided frame in frontal production view
    line(d,[(210,1540),(210,1050),(1450,1050),(1450,1540)],TRELLIS,34)
    line(d,[(210,1540),(210,1050),(1450,1050),(1450,1540)],(167,172,162),22)
    for x in range(330,1450,145): line(d,[(x,1050),(x,1540)],(192,194,183),3)
    for y in range(1160,1540,125): line(d,[(210,y),(1450,y)],(192,194,183),3)
    # Solandra structural primaries: arching, semi-rigid, diagonally crossing the head.
    sol_paths=[
      bezier((245,1540),(220,1330),(235,1120),(430,1055)),
      bezier((285,1540),(300,1320),(390,1100),(700,1060)),
      bezier((360,1515),(480,1340),(710,1120),(1000,1060)),
      bezier((420,1500),(690,1370),(930,1130),(1335,1065)),
    ]
    for p in sol_paths: branch(d,p,SOL,12)
    # Aristolochia leaders: narrower, vertical and densely interwoven.
    ari_paths=[
      bezier((1350,1540),(1440,1370),(1390,1170),(1280,1055)),
      bezier((1410,1540),(1280,1350),(1190,1160),(1040,1055)),
      bezier((1290,1520),(1170,1360),(980,1170),(790,1060)),
      bezier((1180,1510),(990,1380),(770,1180),(560,1060)),
      bezier((1110,1530),(900,1420),(620,1210),(360,1060)),
    ]
    for p in ari_paths: branch(d,p,ARI,8)
    # retained secondary growth — parallel runs plus crossovers, not evenly radial branches.
    rng=random.Random(6021)
    secondary=[]
    for i,p in enumerate(sol_paths):
        for idx in (10,20):
            x,y=p[idx]; target=(min(1430,x+rng.randint(160,360)),y+rng.randint(-80,120))
            q=bezier((x,y),(x+80,y-20),(target[0]-60,target[1]-25),target)
            branch(d,q,SOL_Y,6); secondary.append(("solandra",q))
    for i,p in enumerate(ari_paths):
        for idx in (9,19):
            x,y=p[idx]; target=(max(220,x-rng.randint(120,300)),y+rng.randint(-90,100))
            q=bezier((x,y),(x-60,y-35),(target[0]+45,target[1]-20),target)
            branch(d,q,ARI_Y,5); secondary.append(("aristolochia",q))
    # Mature canopy: leaves occur on every live branch order. Keep primaries visible
    # by redrawing their centerlines after the foliage pass; this is a topology
    # diagram, not a literal occlusion render.
    for p in sol_paths:
        for j,(x,y) in enumerate(p[3::3]):
            small_leaf(d,x,y,"solandra",(-.55 if j%2 else 2.55),.36,
                       color=LEAF_L if j>=len(p[3::3])-2 else LEAF)
    for p in ari_paths:
        for j,(x,y) in enumerate(p[2::3]):
            small_leaf(d,x,y,"aristolochia",(-.45 if j%2 else 2.65),.42,
                       color=LEAF_L if j>=len(p[2::3])-2 else LEAF)
    for species,q in secondary:
        samples=q[5::6]
        for j,(x,y) in enumerate(samples):
            small_leaf(d,x,y,species,(-.6 if j%2 else 2.5),.42 if species=="solandra" else .40,
                       color=LEAF_L if j>=len(samples)-2 else LEAF)
    for p in sol_paths: line(d,p,SOL,5)
    for p in ari_paths: line(d,p,ARI,4)
    # Solandra cups are distributed among numerous flowering laterals. Pipe
    # flowers stay sparse/partly hidden unless the VERDANT mutation override is used.
    for species,q in secondary:
        if species=="solandra" and rng.random()<.72:
            draw_solandra_flower(d,q[-1][0],q[-1][1],.38,rng.uniform(-.35,.35))
        elif species=="aristolochia" and rng.random()<.28:
            draw_pipe_flower(d,q[-1][0],q[-1][1],.33,rng.uniform(-.2,.2))
    # corner knots: multiple crossings plus short hanging tertiary skirt.
    for cx in (230,1430):
        for k in range(7):
            color=SOL_Y if k%2==0 else ARI_Y
            d.arc((cx-48-k*2,1005-k*2,cx+72+k*2,1125+k*2),20,315,fill=color,width=6)
        for k in range(5):
            x=cx-28+k*14
            p=bezier((x,1095),(x+10,1150),(x-20,1210),(x+12,1275+rng.randint(-20,30)))
            branch(d,p,SOL_Y if k%2==0 else ARI_Y,4)
    d.text((250,1580),"SOLANDRA / HEAVIER ARCHING SCAFFOLD",font=font(16,bold=True,mono=True),fill=SOL)
    d.text((900,1580),"ARISTOLOCHIA / DENSE TWINING CURTAIN",font=font(16,bold=True,mono=True),fill=ARI)


def sidebar(d):
    panel(d,(1675,300,2325,1660),"PROCEDURAL BRIEF","Hierarchy first; leaves and flowers last")
    rules=[
      ("01","START WITH SEVERAL PRIMARIES","Build 3–5 structural leaders per jamb/head zone, not one master spline."),
      ("02","BRANCH AT AXILS","At retained nodes, spawn lateral shoots. Leaves do not transform into branches; both arise at the node/axil."),
      ("03","KEEP PARALLEL + CROSSING RUNS","Secondaries can track beside a primary, switch support wires, cross neighbours, bridge one bay, or hang."),
      ("04","ADD A THIRD ORDER","Short tertiary shoots carry most of the fine leaf and flower density. Cull some so the hierarchy stays readable."),
      ("05","MASS CORNERS","Old primaries and crossing laterals form the knot; younger tertiary growth makes the hanging skirt."),
    ]
    y=380
    for num,head,body in rules:
        d.text((1710,y),num,font=font(27,bold=True,mono=True),fill=ACCENT)
        d.text((1770,y+3),head,font=font(18,bold=True,mono=True),fill=INK)
        y=wrapped(d,(1770,y+33),body,font(18),MUTED,505,5)+24
    d.line((1710,y,2285,y),fill=(158,158,147),width=3); y+=25
    d.text((1710,y),"SPECIES READ",font=font(19,bold=True,mono=True),fill=ACCENT); y+=38
    y=wrapped(d,(1710,y),"SOLANDRA: woody, arching and openly visible between leaves. Solitary cups repeat across many retained flowering laterals.",font(18),INK,560,6)+18
    y=wrapped(d,(1710,y),"A. MACROPHYLLA: thinner twining leaders build a layered leaf curtain. Real flowers are usually sparse and hidden by foliage.",font(18),INK,560,6)+18
    d.rounded_rectangle((1705,y,2290,y+190),radius=14,fill=(244,239,219),outline=ACCENT,width=3)
    d.text((1727,y+18),"VERDANT OVERRIDE",font=font(18,bold=True,mono=True),fill=ACCENT)
    wrapped(d,(1727,y+52),"Let both species follow structure and warmth. If more pipe flowers are needed for the research-subject read, treat that as a deliberate mutation—not the baseline habit.",font(18),INK,520,6)
    d.text((1710,1617),"COUNTS ARE PRODUCTION HEURISTICS / NOT MEASURED BOTANY",font=font(14,bold=True,mono=True),fill=MUTED)


def main():
    im=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(im)
    title(d,"06","CLIMBER BRANCHING ARCHITECTURE","Node → lateral shoot → retained scaffold → mature two-species trellis network")
    panel(d,(70,300,1080,840),"A / CORRECT THE BASE TOPOLOGY","The branch hierarchy exists before leaf or flower placement")
    wrong_spline(d); correct_hierarchy(d)
    panel(d,(70,880,1640,1660),"B / MATURE COMBINED HABIT","Opened topology view; final canopy is 3–5 overlapping foliage layers deep / see photo dossier")
    draw_trellis_network(d)
    sidebar(d)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    im.save(OUT,optimize=True)
    print(OUT.relative_to(ROOT))

if __name__=="__main__": main()
