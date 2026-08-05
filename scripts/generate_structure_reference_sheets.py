#!/usr/bin/env python3
"""Generate lore-independent VERDANT structural modelling reference sheets.

These are measured design-intent illustrations, not fabrication drawings. Geometry,
materials, and weathering are deliberately separated so the sheets are useful while
modelling the dome in Blender.
"""
from __future__ import annotations

from pathlib import Path
from math import cos, sin, pi
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 2400, 1800
BG = (231, 226, 210)
INK = (31, 38, 39)
MUTED = (84, 89, 82)
STEEL = (91, 104, 103)
STEEL_L = (133, 145, 139)
STEEL_D = (52, 63, 64)
RUST = (126, 66, 38)
RUST_L = (174, 101, 54)
GREEN = (48, 88, 56)
GLASS = (144, 184, 181, 118)
PUTTY = (181, 174, 143)
RUBBER = (39, 43, 40)
WHITE = (248, 246, 238)
OUT = Path(__file__).resolve().parents[1] / "references" / "structure"
OUT.mkdir(parents=True, exist_ok=True)

REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

def font(size, bold=False, mono=False):
    return ImageFont.truetype(MONO if mono else (BOLD if bold else REG), size)


def line(draw, pts, fill=INK, width=4):
    draw.line(pts, fill=fill, width=width, joint="curve")


def poly(draw, pts, fill, outline=INK, width=3):
    draw.polygon(pts, fill=fill)
    if outline:
        draw.line(pts + [pts[0]], fill=outline, width=width, joint="curve")


def ellipse(draw, box, fill, outline=INK, width=3):
    draw.ellipse(box, fill=fill, outline=outline, width=width)


def wrapped(draw, xy, text, fnt, fill, max_width, spacing=8):
    words = text.split()
    rows, row = [], ""
    for word in words:
        test = word if not row else row + " " + word
        if draw.textbbox((0, 0), test, font=fnt)[2] <= max_width:
            row = test
        else:
            rows.append(row); row = word
    if row: rows.append(row)
    x, y = xy
    for r in rows:
        draw.text((x, y), r, font=fnt, fill=fill)
        y += fnt.size + spacing
    return y


def title(draw, index, name, subtitle):
    draw.text((96, 68), f"VERDANT / STRUCTURE STUDY {index}", font=font(28, mono=True), fill=RUST)
    draw.text((96, 112), name, font=font(72, bold=True), fill=INK)
    draw.text((100, 206), subtitle, font=font(28), fill=MUTED)
    line(draw, [(96, 260), (2304, 260)], MUTED, 3)


def note_box(draw, box, heading, body, accent=RUST):
    x0, y0, x1, y1 = box
    draw.rounded_rectangle(box, radius=18, fill=(244, 241, 230), outline=accent, width=3)
    draw.text((x0+24, y0+18), heading.upper(), font=font(22, bold=True, mono=True), fill=accent)
    wrapped(draw, (x0+24, y0+56), body, font(21), INK, x1-x0-48, 5)


def callout(draw, anchor, elbow, boxxy, number, heading, body, width=430):
    ax, ay = anchor; ex, ey = elbow; bx, by = boxxy
    line(draw, [(ax, ay), (ex, ey), (bx, ey)], RUST, 4)
    ellipse(draw, (ax-10, ay-10, ax+10, ay+10), RUST, WHITE, 2)
    ellipse(draw, (bx-23, ey-23, bx+23, ey+23), RUST, RUST, 1)
    tw = draw.textbbox((0,0), str(number), font=font(23, bold=True))[2]
    draw.text((bx-tw/2, ey-16), str(number), font=font(23, bold=True), fill=WHITE)
    draw.text((bx+38, by), heading.upper(), font=font(22, bold=True, mono=True), fill=RUST)
    wrapped(draw, (bx+38, by+34), body, font(23), INK, width-38, 5)


def steel_beam(draw, start, end, width=105, flange=18, bolts=True):
    """Stylized isometric rolled I-section represented as a plated beam."""
    x0,y0=start; x1,y1=end
    dx=x1-x0; dy=y1-y0; L=(dx*dx+dy*dy)**0.5; nx=-dy/L; ny=dx/L
    p1=(x0+nx*width/2,y0+ny*width/2); p2=(x1+nx*width/2,y1+ny*width/2)
    p3=(x1-nx*width/2,y1-ny*width/2); p4=(x0-nx*width/2,y0-ny*width/2)
    poly(draw,[p1,p2,p3,p4],STEEL)
    # extruded lower side
    off=(16,18)
    poly(draw,[p4,p3,(p3[0]+off[0],p3[1]+off[1]),(p4[0]+off[0],p4[1]+off[1])],STEEL_D)
    # flange highlight strips
    line(draw,[(p1[0]+nx*flange*.25,p1[1]+ny*flange*.25),(p2[0]+nx*flange*.25,p2[1]+ny*flange*.25)],STEEL_L,flange)
    line(draw,[(p4[0]-nx*flange*.25,p4[1]-ny*flange*.25),(p3[0]-nx*flange*.25,p3[1]-ny*flange*.25)],STEEL_D,flange)
    # splice plates near node
    t0=.10; t1=.32
    q=[]
    for t,n in [(t0,1),(t1,1),(t1,-1),(t0,-1)]:
        q.append((x0+dx*t+nx*width*.28*n,y0+dy*t+ny*width*.28*n))
    poly(draw,q,STEEL_L,INK,3)
    if bolts:
        for t in (.15,.23,.30):
            for s in (-.18,.18):
                cx=x0+dx*t+nx*width*s; cy=y0+dy*t+ny*width*s
                ellipse(draw,(cx-8,cy-8,cx+8,cy+8),STEEL_D,INK,2)
                line(draw,[(cx-5,cy),(cx+5,cy)],STEEL_L,2)
    return (dx,dy,nx,ny)


def weather(draw, paths):
    for pts in paths:
        for i, shift in enumerate((0,7,14)):
            jitter=[(x+shift*.15,y+shift) for x,y in pts]
            line(draw,jitter,RUST if i==0 else RUST_L,4 if i==0 else 2)


def make_joinery():
    im=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(im)
    title(d,"01","SEALED STEEL INFRASTRUCTURE JOINT","Tunnel / blast door / freight-lock reference / 1950s heavy steel")
    # main illustration panel
    d.rounded_rectangle((70,300,1640,1660),radius=26,fill=(216,215,202),outline=(150,151,141),width=3)
    # shadow below hub
    shadow=Image.new("RGBA",im.size,(0,0,0,0)); sd=ImageDraw.Draw(shadow)
    sd.ellipse((470,840,1300,1260),fill=(0,0,0,45)); shadow=shadow.filter(ImageFilter.GaussianBlur(28)); im.paste(shadow,(0,0),shadow); d=ImageDraw.Draw(im)
    center=(860,930)
    endpoints=[(225,540),(815,360),(1460,540),(1515,1160),(870,1510),(250,1325)]
    for e in endpoints:
        steel_beam(d,center,e,112)
    # central cast connector: octagonal boss + side thickness
    pts=[]
    for i in range(8):
        a=pi/8+i*pi/4; pts.append((center[0]+190*cos(a),center[1]+145*sin(a)))
    side=[(x+28,y+32) for x,y in pts]
    poly(d,side,STEEL_D,INK,4); poly(d,pts,STEEL_L,INK,5)
    # cast rim and inspection opening
    ellipse(d,(center[0]-115,center[1]-88,center[0]+115,center[1]+88),STEEL,INK,5)
    ellipse(d,(center[0]-63,center[1]-47,center[0]+63,center[1]+47),STEEL_D,INK,4)
    # perimeter bolts
    for i in range(12):
        a=i*2*pi/12
        x=center[0]+148*cos(a); y=center[1]+111*sin(a)
        ellipse(d,(x-10,y-10,x+10,y+10),STEEL_D,INK,2)
        line(d,[(x-6,y),(x+6,y)],STEEL_L,2)
    # triangular gusset fins
    for a in (0.35,2.45,4.55):
        ux,uy=cos(a),sin(a); nx,ny=-uy,ux
        p=[(center[0]+ux*95+nx*18,center[1]+uy*70+ny*18),
           (center[0]+ux*235+nx*16,center[1]+uy*175+ny*16),
           (center[0]+ux*160-nx*16,center[1]+uy*120-ny*16)]
        poly(d,p,STEEL_D,INK,3)
    # casting texture / part line
    for r in (132,145):
        d.arc((center[0]-r,center[1]-r*.72,center[0]+r,center[1]+r*.72),190,350,fill=(167,171,158),width=3)
    # water/rust trails down lower members
    weather(d,[[(890,1065),(905,1160),(900,1305),(920,1425)],[(665,1030),(580,1130),(465,1220),(350,1280)],[(1060,970),(1180,1015),(1320,1090),(1435,1145)]])
    # weld beads at lugs
    for a in [i*pi/3 for i in range(6)]:
        x=center[0]+190*cos(a); y=center[1]+145*sin(a)
        for k in range(-3,4):
            ellipse(d,(x+k*5-3,y+k*2-3,x+k*5+3,y+k*2+3),RUST_L,None,1)
    # scale figure + scale note
    line(d,[(145,1535),(420,1535)],INK,6); line(d,[(145,1522),(145,1548)],INK,4); line(d,[(420,1522),(420,1548)],INK,4)
    d.text((160,1552),"REFERENCE SPAN ≈ 600 mm",font=font(21,mono=True),fill=MUTED)

    callout(d,(1030,800),(1660,510),(1680,480),1,"Cast central connector","Sand-cast or cast-steel hub with generous radii, draft, a visible parting line, and machined lug faces. Keep it chunky: this is the showpiece load-transfer part, not a thin plate.",560)
    callout(d,(1120,640),(1660,730),(1680,700),2,"Bolted splice plates","Paired web plates plus flange cover plates. Use period hex-head structural bolts, washers, and nuts; slightly irregular clocking, but disciplined engineering spacing.",560)
    callout(d,(660,855),(1660,970),(1680,940),3,"Gusset fins + welds","Triangular stiffeners carry rib forces into the cast boss. Model broad fillets and proud, continuous weld beads where fabricated plates meet machined lugs.",560)
    callout(d,(915,1290),(1660,1210),(1680,1180),4,"Drainage weathering","Rain/condensation begins at horizontal ledges, tracks around fasteners, then runs vertically down webs and lower flange edges. Keep rust directional; avoid uniform orange noise.",560)
    note_box(d,(1665,1420,2310,1660),"Material / surface callout","Lead-based industrial enamel over zinc-rich primer on structural steel. Surviving paint is satin and desaturated blue-green; exposed edges are dark burnished steel; rust is layered brown-black at wet seams, orange only at fresh scale. Cast surfaces are subtly pebbled; machined faces and bolt heads are smoother.")
    path=OUT/"sealed_steel_infrastructure_joint_reference_2400x1800.png"; im.save(path,optimize=True)
    return path


def make_glazing():
    im=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(im)
    title(d,"02","GREENHOUSE GLAZING DETAIL","Three-quarter modelling reference / layered original hardware + later gasket repair")
    d.rounded_rectangle((70,300,1640,1660),radius=26,fill=(218,219,208),outline=(150,151,141),width=3)
    # main frame: isometric vertical mullion with horizontal transom
    # glass panes as translucent overlays
    glass=Image.new("RGBA",im.size,(0,0,0,0)); gd=ImageDraw.Draw(glass)
    gd.polygon([(185,420),(742,520),(742,940),(175,790)],fill=GLASS,outline=(83,124,122,190))
    gd.polygon([(955,540),(1510,665),(1500,1085),(955,930)],fill=GLASS,outline=(83,124,122,190))
    gd.polygon([(180,900),(742,1035),(742,1490),(170,1340)],fill=GLASS,outline=(83,124,122,190))
    gd.polygon([(955,1020),(1500,1145),(1490,1510),(955,1405)],fill=(144,184,181,90),outline=(83,124,122,190))
    im=Image.alpha_composite(im.convert("RGBA"),glass).convert("RGB"); d=ImageDraw.Draw(im)
    # central steel T/mullion and cap bar
    poly(d,[(720,390),(900,430),(985,1485),(808,1445)],STEEL,INK,4)
    poly(d,[(900,430),(946,403),(1030,1458),(985,1485)],STEEL_D,INK,4)
    poly(d,[(742,430),(765,405),(938,445),(915,470)],STEEL_L,INK,3)
    # horizontal glazing bar behind/through
    poly(d,[(155,820),(1510,1120),(1510,1195),(155,895)],STEEL,INK,4)
    poly(d,[(155,895),(1510,1195),(1495,1228),(140,928)],STEEL_D,INK,3)
    # raised cap / putty lines either side of mullion
    line(d,[(690,432),(777,1440)],PUTTY,18); line(d,[(970,475),(1042,1450)],PUTTY,18)
    line(d,[(675,430),(763,1440)],INK,3); line(d,[(980,475),(1052,1450)],INK,3)
    # spring fixing clips
    for t in (.18,.42,.67,.86):
        x=790+(930-790)*t; y=535+(1360-535)*t
        poly(d,[(x-42,y-10),(x+42,y),(x+28,y+18),(x-28,y+8)],STEEL_L,INK,3)
        ellipse(d,(x-8,y-7,x+8,y+9),STEEL_D,INK,2)
    # gaskets visible as black strips beneath cap
    line(d,[(714,438),(802,1438)],RUBBER,10); line(d,[(952,478),(1022,1448)],RUBBER,10)
    # broken upper-right pane, jagged remaining edge and missing shard region
    shard=[(970,540),(1130,575),(1085,650),(1245,700),(1160,780),(1320,835),(1215,930),(955,870)]
    poly(d,shard,(205,220,211), (78,111,108), 5)
    # cracks
    for pts in [[(1128,578),(1170,660),(1242,700)],[(1168,660),(1105,735),(1160,780)],[(1240,700),(1310,760),(1320,835)]]:
        line(d,pts,(74,104,103),3)
    # growth through break
    stems=[[(1180,760),(1260,720),(1315,650)],[(1185,760),(1290,825),(1390,800)],[(1200,770),(1210,655),(1160,595)]]
    for pts in stems: line(d,pts,GREEN,12)
    for x,y,a in [(1320,650,0),(1392,800,0),(1160,592,0),(1295,825,0),(1220,685,0)]:
        ellipse(d,(x-30,y-16,x+30,y+16),(62,111,66),GREEN,2)
    # water/grime trails beneath clips and putty gaps
    weather(d,[[(820,790),(828,900),(842,1040)],[(1005,885),(1015,1000),(1025,1145)],[(540,900),(550,1015),(545,1100)]])
    # inset section at lower left
    d.rounded_rectangle((115,1180,660,1600),radius=18,fill=(244,241,230),outline=MUTED,width=3)
    d.text((145,1208),"PROFILE / NOT TO SCALE",font=font(22,bold=True,mono=True),fill=MUTED)
    # steel T profile section
    poly(d,[(235,1340),(470,1340),(470,1385),(377,1385),(377,1535),(330,1535),(330,1385),(235,1385)],STEEL,INK,4)
    # glass, gasket, putty, clip
    poly(d,[(150,1300),(300,1300),(300,1322),(150,1322)],(151,190,187),INK,2)
    poly(d,[(490,1300),(630,1300),(630,1322),(490,1322)],(151,190,187),INK,2)
    d.rectangle((285,1322,330,1341),fill=RUBBER); d.rectangle((470,1322,510,1341),fill=RUBBER)
    poly(d,[(280,1265),(330,1265),(330,1298),(300,1320),(280,1310)],PUTTY,INK,2)
    poly(d,[(470,1265),(520,1265),(520,1310),(500,1320),(470,1298)],PUTTY,INK,2)
    line(d,[(285,1244),(515,1244)],STEEL_L,12); line(d,[(398,1244),(398,1345)],STEEL_D,10)
    d.text((150,1550),"original steel T-bar + clip cap",font=font(19,mono=True),fill=MUTED)

    callout(d,(860,655),(1660,470),(1680,440),1,"Rolled steel glazing bar","Use a slender T or proprietary greenhouse mullion, not a square tube. The deep stem carries load; shallow shoulders support glass and collect condensation.",560)
    callout(d,(774,995),(1660,700),(1680,670),2,"Gasket + putty stack","Show both as repair history: compressed black neoprene strip under a later cap, with older buff linseed-oil glazing compound still visible in irregular beveled beads.",560)
    callout(d,(845,1120),(1660,930),(1680,900),3,"Spring clips / fixings","Stamped galvanized clips bridge the cap at regular intervals. Give them thin spring-steel thickness, one central screw or rivet, and small bent returns—not chunky brackets.",560)
    callout(d,(1240,700),(1660,1160),(1680,1130),4,"Broken pane + growth","Glass breaks in sharp, planar shards held at the putty edge. Add hairline cracks before missing areas. Vines enter through the void and press against—not through—surviving glass.",560)
    note_box(d,(1665,1390,2310,1660),"Material / surface callout","Mullions: galvanized steel under chalked cream-grey enamel, with zinc bloom and rust only where coating is cut. Glass: imperfect 6–8 mm wired or horticultural panes, faint green edge tint, mineral spotting, algae at wet lower edges. Gasket: matte cracked black neoprene. Putty: buff-grey, crazed and locally missing. Clips: brighter galvanized spring steel with darker fasteners.")
    path=OUT/"greenhouse_glazing_detail_reference_2400x1800.png"; im.save(path,optimize=True)
    return path

if __name__ == "__main__":
    for p in (make_joinery(), make_glazing()):
        print(p)
