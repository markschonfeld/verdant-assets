#!/usr/bin/env python3
"""Annotate Mark's 2026-08-06 vine-growth screenshots for Claude handoff."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
QA=ROOT/"qa"/"vine_growth_review_2026-08-06"
REG="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
INK=(235,232,219); BG=(22,27,26); PANEL=(35,42,40); RED=(235,88,65); GOLD=(230,177,76)


def font(n,bold=False): return ImageFont.truetype(BOLD if bold else REG,n)

def wrapped(d,xy,text,fnt,fill,width,spacing=5):
    x,y=xy; words=text.split(); row=""; lines=[]
    for w in words:
        test=(row+" "+w).strip()
        if d.textbbox((0,0),test,font=fnt)[2]<=width: row=test
        else: lines.append(row); row=w
    if row: lines.append(row)
    for line in lines:
        d.text((x,y),line,font=fnt,fill=fill); y+=fnt.size+spacing
    return y


def make(src_name,out_name,title,regions,notes):
    src=Image.open(QA/src_name).convert("RGB")
    target_w=1700; target_h=round(src.height*target_w/src.width)
    src=src.resize((target_w,target_h),Image.Resampling.LANCZOS)
    out=Image.new("RGB",(2400,max(1050,target_h+90)),BG); d=ImageDraw.Draw(out)
    d.text((35,20),title,font=font(32,True),fill=INK)
    d.text((35,58),"CURRENT BUILD / MARK SCREENSHOT / NUMBERED FAILURE REGIONS",font=font(17,True),fill=GOLD)
    out.paste(src,(0,90))
    sx=target_w/2577; sy=target_h/1374
    for n,(box,point) in enumerate(regions,1):
        x0,y0,x1,y1=box
        b=(x0*sx,90+y0*sy,x1*sx,90+y1*sy)
        d.rounded_rectangle(b,radius=14,outline=RED,width=6)
        px,py=point; px*=sx; py=90+py*sy
        d.ellipse((px-24,py-24,px+24,py+24),fill=RED,outline=(255,230,205),width=3)
        label=str(n); bb=d.textbbox((0,0),label,font=font(24,True));
        d.text((px-(bb[2]-bb[0])/2,py-(bb[3]-bb[1])/2-3),label,font=font(24,True),fill=(255,255,245))
    d.rectangle((1700,90,2399,out.height-1),fill=PANEL)
    y=115
    for n,(head,body) in enumerate(notes,1):
        d.ellipse((1730,y,1770,y+40),fill=RED)
        d.text((1743,y+4),str(n),font=font(22,True),fill=(255,255,245))
        d.text((1790,y),head,font=font(20,True),fill=GOLD)
        y=wrapped(d,(1790,y+30),body,font(18),INK,560,5)+25
    d.text((1730,out.height-42),"See VINE_GROWTH_DYNAMICS_CORRECTION_BRIEF.md",font=font(14,True),fill=(150,174,164))
    out.save(QA/out_name,optimize=True)


def main():
    make("source_exterior.png","annotated_exterior.png","EXTERIOR / GREENHOUSE SIDE",[
      ((350,610,2200,1120),(1320,780)),
      ((240,350,2210,760),(1850,480)),
      ((670,640,1870,940),(1180,690)),
      ((650,700,1800,1110),(900,900)),
      ((520,580,2050,940),(1550,650)),
      ((900,520,1700,1210),(1290,1000)),
    ],[
      ("RECTANGULAR HEDGE SILHOUETTE","Density forms a uniform wire rectangle. Break the top line and side masses into supported knots, weighted drapes, and asymmetrical flowering lobes."),
      ("UNSUPPORTED SPEARS","Long secondary and tertiary stems project straight upward and sideways after leaving support. Only the last short searching tip may rise; the parent run must sag."),
      ("VISIBLE PROCEDURAL HELICES","Repeated inner spirals read as coils of cable. A twining helix is valid only while touching a trellis wire or host stem, and it should disappear beneath foliage."),
      ("LINE DENSITY, NOT CANOPY MASS","There are many dark curves but leaves remain tiny, evenly scattered, and mostly one layer. Build 3–5 overlapping leaf layers with species-scale leaves and clustered shoots."),
      ("NO BLOOM SYSTEM","This volume of warm greenhouse growth needs distributed Solandra cups and buds. Pipe flowers stay mostly concealed, with visible mutation-biased examples near the warm doorway."),
      ("DOORWAY INTRUSION WITHOUT WEIGHT","Stems extend deep into the entrance yet remain straight. Preserve edge overgrowth, but drape it from head/jamb anchors and keep thick stems outside the player clearance envelope."),
    ])
    make("source_interior.png","annotated_interior.png","INTERIOR / LOOKING OUT",[
      ((450,410,1950,980),(1270,650)),
      ((380,430,850,1060),(590,760)),
      ((750,520,1750,1050),(1450,900)),
      ((510,330,1960,760),(1120,470)),
      ((550,400,1900,900),(1700,560)),
      ((500,360,1960,1030),(1100,850)),
    ],[
      ("GRAVITY-INVARIANT CURTAIN","Long free stems hang at arbitrary diagonals or stay nearly straight. Once unsupported, their tangent must relax downward and sag must increase with free length."),
      ("EYE-LEVEL LANCES","The left diagonal crosses the passage as a rigid stick. Replace it with a weighted arc attached at the jamb, or prune it back to leaves and flexible tips at the edge."),
      ("FLOOR-SEEKING STRAIGHT LINES","Several center/right stems approach the floor as straight rods. Hanging shoots need curved shoulders, tapered ends, leaf weight, and varied termination heights."),
      ("COIL/GRID READ","The inner canopy is dominated by repeated dark loops and radial-looking crossings. Break procedural phase, remove free-space helices, and occlude most thin stems with foliage."),
      ("FLOWER VOID","The opening has no large focal blooms despite strong warmth and mature mass. Flowers need a branch-order-aware placement pass, not random node decoration."),
      ("PLAY SPACE NEEDS A SOFT ENVELOPE","Allow leaves, flowers, and a few thin tips to brush the edge of the opening; exclude woody stems from the central 1.5 m × 2.2 m passage."),
    ])
    a=Image.open(QA/"annotated_exterior.png"); b=Image.open(QA/"annotated_interior.png")
    c=Image.new("RGB",(2400,a.height+b.height+30),BG); c.paste(a,(0,0)); c.paste(b,(0,a.height+30)); c.save(QA/"vine_growth_review_contact_sheet.png",optimize=True)
    print(QA)

if __name__=="__main__": main()
