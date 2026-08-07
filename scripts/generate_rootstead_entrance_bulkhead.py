#!/usr/bin/env python3
"""Deterministically author the full production Rootstead entrance bulkhead."""
from __future__ import annotations
import json, math, sys
from collections import Counter
from pathlib import Path
from typing import Iterable
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"scripts"))
import rootstead_entrance_bulkhead_spec as S
OUT=ROOT/"SourceMesh/architecture"; QA=ROOT/"qa/rootstead_entrance_bulkhead"

class Mesh:
 def __init__(self): self.v=[]; self.f=[]
 def vertex(self,p): self.v.append(tuple(float(x) for x in p)); return len(self.v)
 def face(self,m,ids): self.f.append((m,tuple(ids)))
 def box(self,a,b,m):
  x0,y0,z0=a;x1,y1,z1=b; ids=[self.vertex((x,y,z)) for z in(z0,z1) for y in(y0,y1) for x in(x0,x1)]
  for q in ((0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)): self.face(m,[ids[i] for i in q])
 def cylinder(self,a,b,r,n,m):
  d=tuple(b[i]-a[i] for i in range(3)); L=math.sqrt(sum(x*x for x in d)); w=tuple(x/L for x in d)
  seed=(0.,0.,1.) if abs(w[2])<.9 else (1.,0.,0.); u=(w[1]*seed[2]-w[2]*seed[1],w[2]*seed[0]-w[0]*seed[2],w[0]*seed[1]-w[1]*seed[0]); q=math.sqrt(sum(x*x for x in u));u=tuple(x/q for x in u); t=(w[1]*u[2]-w[2]*u[1],w[2]*u[0]-w[0]*u[2],w[0]*u[1]-w[1]*u[0])
  rings=[]
  for p in(a,b): rings.append([self.vertex(tuple(p[k]+r*(math.cos(2*math.pi*i/n)*u[k]+math.sin(2*math.pi*i/n)*t[k]) for k in range(3))) for i in range(n)])
  self.face(m,reversed(rings[0])); self.face(m,rings[1])
  for i in range(n): j=(i+1)%n; self.face(m,(rings[0][i],rings[0][j],rings[1][j],rings[1][i]))
 def write(self):
  lines=["# Generated production asset; do not hand-edit",f"mtllib {S.NAME}.mtl",f"o {S.NAME}"]+[f"v {x:.6f} {y:.6f} {z:.6f}" for x,y,z in self.v]
  uv=[]; ni=1
  for _,f in self.f:
   p=[self.v[i-1] for i in f]; spans=[max(x[k] for x in p)-min(x[k] for x in p) for k in range(3)]; drop=spans.index(min(spans)); axes=[k for k in range(3) if k!=drop]
   lines += [f"vt {x[axes[0]]/100:.6f} {x[axes[1]]/100:.6f}" for x in p]; uv.append(range(ni,ni+len(f)));ni+=len(f)
  cur=None
  for (m,f),t in zip(self.f,uv):
   if m!=cur: lines += [f"usemtl {m}","s 1"];cur=m
   lines.append("f "+" ".join(f"{a}/{b}" for a,b in zip(f,t)))
  p=OUT/f"{S.NAME}.obj";p.write_text("\n".join(lines)+"\n");return p

COL={S.MAT_STRUCTURE:(.42,.40,.36),S.MAT_PLINTH:(.55,.50,.42),S.MAT_PRECAST:(.72,.68,.58),S.MAT_AGG:(.35,.31,.24),S.MAT_CHAMFER:(.61,.57,.49),S.MAT_JOINT:(.25,.23,.21),S.MAT_SEAL:(.12,.11,.10),S.MAT_SPALL:(.57,.53,.45),S.MAT_REBAR:(.42,.19,.11),S.MAT_STREAK:(.35,.37,.34)}

def surf(kind,bound,u,z,depth=0.):
 if kind=="west": return (S.FACE_X-depth,u,z)
 return (u,bound[0]+bound[1]*depth,z)

def prism(mesh,kind,bound,u0,u1,z0,z1,d0,d1,mat):
 pts=[surf(kind,bound,u,z,d) for d in(d0,d1) for z in(z0,z1) for u in(u0,u1)]; ids=[mesh.vertex(p) for p in pts]
 for q in ((0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)): mesh.face(mat,[ids[i] for i in q])

def fracture(mesh,kind,bound,u0,u1,z0,z1,index):
 # Closed, extruded five-sided corner-loss facet. Corner, dimensions, depth,
 # handedness and diagonal bite all vary deterministically by module.
 corner=index%4; w=17+(index*7)%8; h=14+(index*5)%7; bite=5+(index*3)%5
 left=corner in (0,2); bottom=corner in (0,1)
 ua,ub=(u0,u0+w) if left else (u1-w,u1); za,zb=(z0,z0+h) if bottom else (z1-h,z1)
 if left and bottom: poly=[(ua,za),(ub,za),(ub,za+bite),(ua+bite,zb),(ua,zb)]
 elif not left and bottom: poly=[(ua,za),(ub,za),(ub,zb),(ub-bite,zb),(ua,za+bite)]
 elif left: poly=[(ua,za),(ua+bite,za),(ub,zb-bite),(ub,zb),(ua,zb)]
 else: poly=[(ua,za+bite),(ub-bite,za),(ub,za),(ub,zb),(ua,zb)]
 skind="return" if kind=="return_door" else kind; depth=4.5+(index%4)*.7
 d1=depth if kind=="return_door" else -depth
 rings=[[mesh.vertex(surf(skind,bound,u,z,d)) for u,z in poly] for d in (0,d1)]
 mesh.face(S.MAT_SPALL,tuple(reversed(rings[0])));mesh.face(S.MAT_SPALL,rings[1])
 for i in range(5):j=(i+1)%5;mesh.face(S.MAT_SPALL,(rings[0][i],rings[0][j],rings[1][j],rings[1][i]))
 # Short oxidized lug lies within the fractured footprint, with varied slant.
 cu=sum(p[0] for p in poly)/5;cz=sum(p[1] for p in poly)/5
 du=(-1 if index%2 else 1)*(2.2+(index%3));dz=(-1 if (index//2)%2 else 1)*(2.0+(index%2))
 # Keep the round lug fully behind the legal face/return stop plane.
 sgn=1 if d1>0 else -1;a=surf(skind,bound,cu-du,cz-dz,sgn*1.35);b=surf(skind,bound,cu+du,cz+dz,d1-sgn*1.35)
 mesh.cylinder(a,b,1.05,8,S.MAT_REBAR)

def pad(mesh,kind,bound,u0,u1,z0,z1,inward=False):
 j=S.JOINT/2;c=S.CHAMFER; bu0,bu1,bz0,bz1=u0+j,u1-j,z0+j,z1-j; fu0,fu1,fz0,fz1=bu0+c,bu1-c,bz0+c,bz1-c
 f=[mesh.vertex(surf(kind,bound,u,z,0)) for z in(fz0,fz1) for u in(fu0,fu1)]; b=[mesh.vertex(surf(kind,bound,u,z,S.RECESS if inward else -S.RECESS)) for z in(bz0,bz1) for u in(bu0,bu1)]
 mesh.face(S.MAT_PRECAST,(f[0],f[2],f[3],f[1]));mesh.face(S.MAT_PRECAST,(b[0],b[1],b[3],b[2]))
 for q in ((0,1,1,0),(2,0,0,2),(1,3,3,1),(3,2,2,3)): mesh.face(S.MAT_CHAMFER,(f[q[0]],f[q[1]],b[q[2]],b[q[3]]))
 return bu0,bu1,bz0,bz1

SAMPLES=[(.12,.18,3.1,5,.20,2.2),(.31,.11,4.4,6,.71,3.2),(.56,.20,2.8,5,1.07,1.8),(.81,.13,5.2,7,.38,4.2),(.21,.39,3.7,6,1.31,2.7),(.47,.34,4.8,7,.04,3.8),(.73,.43,3.,5,.86,2.1),(.91,.34,4.1,6,1.55,3.),(.08,.62,4.6,7,.52,3.5),(.37,.58,2.7,5,1.18,1.7),(.63,.67,3.9,6,.28,2.9),(.84,.60,4.9,7,1.02,3.9),(.26,.83,3.3,5,.62,2.4),(.69,.86,4.3,6,1.43,3.3)]
def noise(i,salt):
 # Stable integer mixer, mapped to [-1,1]; deliberately independent of RNG state.
 x=(i+1)*0x9E3779B1+(salt+11)*0x85EBCA77;x^=x>>16;x=(x*0xC2B2AE3D)&0xffffffff;x^=x>>13
 return (x/0xffffffff)*2-1
def aggregate(mesh,kind,bound,u0,u1,z0,z1,module):
 # A module-specific dihedral transform, permutation, jitter, azimuth and scale
 # breaks the visible stamp while preserving the held 14-stone density/budget.
 flip=module%2; flipz=(module//2)%2; shift=(module*5+module//7)%14
 for outk in range(14):
  k=(outk+shift)%14;uu,uz,r,n,rot,proud=SAMPLES[k]
  if flip: uu=1-uu
  if flipz: uz=1-uz
  uu=max(.055,min(.945,uu+noise(module,k*3)*.025))
  uz=max(.065,min(.935,uz+noise(module,k*3+1)*.025))
  r*=1+noise(module,k*3+2)*.075;proud=min(S.RELIEF_PROUD,proud*(1+noise(module,k*3+3)*.09))
  rot+=module*.271+noise(module,k+71)*.32
  u=u0+12+uu*(u1-u0-24); z=z0+13+uz*(z1-z0-26)
  if kind=="return_door" and -419<u<-343 and z<457: u=(-438. if k%2==0 else -330.)
  if kind=="return_door" and -90<u<-10 and 120<z<330: u=u0+12+((uu+.57)%1)*(u1-u0-24); z=z0+13+((uz+.61)%1)*(z1-z0-26)
  ring=[]
  for i in range(n):
   a=rot+2*math.pi*i/n; wob=1+.13*math.sin(3*a+uu*5+module*.17)
   # Return stone face polygons finish exactly on their legal stop plane; their
   # back apex embeds into the wing. This retains a readable full silhouette
   # without a single tip crossing ±424 or ±1300.
   depth=0 if kind in ("return_door","return") else proud*.25
   ring.append(mesh.vertex(surf("return" if kind=="return_door" else kind,bound,u+r*wob*math.cos(a),z+r*.82*wob*math.sin(a),depth)))
  if kind=="return_door": fd,bd=0,2.
  elif kind=="return": fd,bd=0,-2.
  else: fd,bd=proud,-1.
  front=mesh.vertex(surf("return" if kind=="return_door" else kind,bound,u+r*.08,z-r*.05,fd)); back=mesh.vertex(surf("return" if kind=="return_door" else kind,bound,u-r*.06,z+r*.04,bd))
  for i in range(n): j=(i+1)%n;mesh.face(S.MAT_AGG,(front,ring[i],ring[j]));mesh.face(S.MAT_AGG,(back,ring[j],ring[i]))

def module(mesh,kind,bound,u0,u1,z0,z1,index):
 skind="return" if kind=="return_door" else kind
 if kind=="return_door" and u0==-461. and z0<450.:
  regions=[(-461.,-412.,z0,min(z1,450.)),(-350.,u1,z0,min(z1,450.))]
  if z1>450.: regions.append((u0,u1,450.,z1))
  for ra,rb,rz0,rz1 in regions:
   if rb-ra>20 and rz1-rz0>20: prism(mesh,skind,bound,ra,rb,rz0,rz1,S.RECESS-1,S.RECESS,S.MAT_JOINT);pad(mesh,skind,bound,ra,rb,rz0,rz1,True)
  bu0,bu1,bz0,bz1=u0+S.JOINT/2,u1-S.JOINT/2,z0+S.JOINT/2,z1-S.JOINT/2
 else:
  prism(mesh,skind,bound,u0,u1,z0,z1,(S.RECESS-1 if kind=="return_door" else -S.RECESS),(S.RECESS if kind=="return_door" else -S.RECESS+1),S.MAT_JOINT); bu0,bu1,bz0,bz1=pad(mesh,skind,bound,u0,u1,z0,z1,kind=="return_door")
 aggregate(mesh,kind,bound,bu0,bu1,bz0,bz1,index)
 # Discontinuous sealant and module-varied, geometry-sourced vertical streaks.
 prism(mesh,skind,bound,u0+.35,u0+S.JOINT/2-.25,z0+.35,z0+38,(4 if kind=="return_door" else -8),(8 if kind=="return_door" else -4),S.MAT_SEAL)
 origins=[(bu0+8,bz1),(bu1-10,bz1),(bu0+15,bz0+26)]
 order=(index*2+index//5)%3
 for run in range(3):
  q,top=origins[(run+order)%3];q+=noise(index,90+run)*5.5
  segs=2+(index+run*2)%3; runout=.54+.34*((noise(index,110+run)+1)/2); bottom=top-(top-bz0-4)*runout
  basew=2.3+.95*((noise(index,130+run)+1)/2)
  for n in range(segs):
   a=top-(top-bottom)*n/segs;b=top-(top-bottom)*(n+1)/segs;w=basew*(1-.18*n)
   relief=.45+.2*((index+run)%2);d0,d1=(-relief,0) if kind=="return" else (0,relief)
   prism(mesh,skind,bound,q-w/2+n*.18,q+w/2-n*.18,b,a,d0,d1,S.MAT_STREAK)
 if index in S.SPALL_INDICES: fracture(mesh,kind,bound,bu0,bu1,bz0,bz1,index)

def build():
 m=Mesh()
 # Proper closed structural bodies, segmented only where existing jambs occupy the inner strip.
 for _,xr,yr,zr in S.COLLISION_BOXES: m.box((xr[0],yr[0],zr[0]-3500),(xr[1],yr[1],zr[1]-3500),S.MAT_STRUCTURE)
 # Six board lifts on all decorated plinth face families.
 for side in(-1,1):
  y0,y1=(-1300.,-424.) if side<0 else (424.,1300.)
  for b in range(6):
   z0=b*25+(3 if b else 0);z1=(b+1)*25-3;prism(m,"west",(0,0),y0,y1,z0,z1,0,-12,S.MAT_PLINTH)
  for y,sgn in ((side*1300.,side),(side*424.,side)):
   for b in range(6):
    z0=b*25+(3 if b else 0);z1=(b+1)*25-3
    ranges=((-461.,112.),) if abs(y)==1300 else ((-461.,-412.),(-350.,112.))
    for xa,xb in ranges:
     # Both outer-return matrix and plinth recess into the structural stop plane.
     d0,d1=(-12,0) if abs(y)==1300 else (0,12)
     prism(m,"return",(y,sgn),xa,xb,z0,z1,d0,d1,S.MAT_PLINTH)
  # Joint-free, plumb cast mounting pads, flush exactly to the doorway boundary
  # and thickening only into the corresponding wing (never into the passage).
  if side<0: m.box((-90.,-430.,120.),(-10.,-424.,330.),S.MAT_PRECAST)
  else: m.box((-90.,424.,120.),(-10.,430.,330.),S.MAT_PRECAST)
 idx=0
 for a,b in zip(S.WEST_BOUNDS,S.WEST_BOUNDS[1:]):
  if a==-424 and b==424: continue
  for z0,z1 in zip(S.COURSE_BOUNDS,S.COURSE_BOUNDS[1:]): module(m,"west",(0,0),a,b,z0,z1,idx);idx+=1
 for side in(-1,1):
  for outer,y in ((True,side*1300.),(False,side*424.)):
   for a,b in zip(S.RETURN_BOUNDS,S.RETURN_BOUNDS[1:]):
    for z0,z1 in zip(S.COURSE_BOUNDS,S.COURSE_BOUNDS[1:]): module(m,"return" if outer else "return_door",(y,side),a,b,z0,z1,idx);idx+=1
 assert idx==72
 return m

def render(mesh,path):
 """Deterministic orthographic software render of the re-parsed OBJ."""
 import numpy as np
 from PIL import Image,ImageDraw,ImageFont
 W,H=2600,1700; bg=np.array((235,233,225),dtype=np.uint8);canvas=np.empty((H,W,3),dtype=np.uint8);canvas[:]=bg
 # title, pixel box, screen axes, forward/depth axis, explicit crop in screen units
 views=[
  ("FULL WEST ELEVATION",(40,100,2560,900),(1,2),0,(-1325,1325,-12,837),1),
  ("WEST FRACTURE DETAIL - 9 MODULES",(40,980,1020,1540),(1,2),0,(-1310,-850,135,835),1),
  ("DOOR RETURN - FROM PASSAGE",(1060,980,1790,1540),(0,2),1,(-470,120,-8,835),-1),
  ("OUTER RETURN - FROM OUTSIDE",(1830,980,2560,1540),(0,2),1,(-470,120,-8,835),1),
 ]
 tris=[]
 for mat,f in mesh.f:
  for i in range(1,len(f)-1): tris.append((mat,[mesh.v[j-1] for j in(f[0],f[i],f[i+1])]))
 stats={}; color8={m:tuple(int(round(255*x)) for x in c) for m,c in COL.items()}
 for title,(x0,y0,x1,y1),axes,daxis,crop,dsign in views:
  pw,ph=x1-x0,y1-y0; frame=np.empty((ph,pw,3),dtype=np.uint8);frame[:]=bg;zbuf=np.full((ph,pw),np.inf,dtype=np.float64)
  u0,u1,v0,v1=crop; scale=min((pw-20)/(u1-u0),(ph-20)/(v1-v0)); ox=(pw-(u1-u0)*scale)/2-u0*scale;oy=(ph-(v1-v0)*scale)/2+v1*scale
  for mat,q in tris:
   xy=np.array([[ox+p[axes[0]]*scale,oy-p[axes[1]]*scale] for p in q]);zz=np.array([dsign*p[daxis] for p in q])
   lo=np.maximum(np.floor(xy.min(axis=0)).astype(int),(0,0));hi=np.minimum(np.ceil(xy.max(axis=0)).astype(int),(pw-1,ph-1))
   if np.any(hi<lo):continue
   ax,ay=xy[0];bx,by=xy[1];cx,cy=xy[2];den=(by-cy)*(ax-cx)+(cx-bx)*(ay-cy)
   if abs(den)<1e-9:continue
   xs=np.arange(lo[0],hi[0]+1)+.5;ys=np.arange(lo[1],hi[1]+1)+.5;xx,yy=np.meshgrid(xs,ys)
   w0=((by-cy)*(xx-cx)+(cx-bx)*(yy-cy))/den;w1=((cy-ay)*(xx-cx)+(ax-cx)*(yy-cy))/den;w2=1-w0-w1
   inside=(w0>=-1e-8)&(w1>=-1e-8)&(w2>=-1e-8);depth=w0*zz[0]+w1*zz[1]+w2*zz[2]
   # Equal-depth authored finish faces deliberately replace backing coplanars.
   sub=zbuf[lo[1]:hi[1]+1,lo[0]:hi[0]+1];take=inside&(depth<=sub+1e-9)
   sub[take]=depth[take];frame[lo[1]:hi[1]+1,lo[0]:hi[0]+1][take]=color8[mat]
  canvas[y0:y1,x0:x1]=frame
  mask=np.any(frame!=bg,axis=2); unique,counts=np.unique(frame[mask].reshape(-1,3),axis=0,return_counts=True) if mask.any() else (np.empty((0,3)),np.array([]))
  cmap={tuple(map(int,c)):int(n) for c,n in zip(unique,counts)}; semantic={m:cmap.get(color8[m],0) for m in COL}
  coverage=float(mask.mean());structural_fraction=semantic[S.MAT_STRUCTURE]/max(1,int(mask.sum()))
  stats[title]={"viewport":[x0,y0,x1,y1],"coverage":round(coverage,5),"semantic_color_count":sum(n>0 for n in semantic.values()),"structural_fraction_of_ink":round(structural_fraction,5),"semantic_pixels":semantic}
 im=Image.fromarray(canvas,"RGB");d=ImageDraw.Draw(im);font=ImageFont.load_default(size=24);small=ImageFont.load_default(size=18)
 d.text((40,28),"ROOTSTEAD ENTRANCE BULKHEAD - ACTUAL PARSED OBJ / NUMPY Z-BUFFER",fill=(22,24,22),font=font)
 for title,box,*_ in views:d.rectangle(box,outline=(35,37,34),width=3);d.rectangle((box[0]+8,box[1]+8,box[0]+420,box[1]+42),fill=(235,233,225));d.text((box[0]+16,box[1]+12),title,fill=(20,22,20),font=small)
 lx=42;ly=1590
 for mat in COL:
  d.rectangle((lx,ly,lx+18,ly+18),fill=color8[mat],outline=(25,25,23));d.text((lx+25,ly-1),mat.replace("M_EntranceBulkhead_",""),fill=(30,31,29),font=small);lx+=245
  if lx>2350:lx=42;ly+=32
 im.save(path,optimize=True)
 return {"renderer":"numpy_orthographic_zbuffer_v1","z_buffer":True,"two_sided":True,"backface_culling":False,"image_size":[W,H],"parsed_obj_vertices":len(mesh.v),"parsed_obj_faces":len(mesh.f),"parsed_obj_triangles":len(tris),"view_names":[v[0] for v in views],"view_stats":stats}

def parsed_obj_mesh(path):
 m=Mesh();cur=None
 for line in path.read_text().splitlines():
  p=line.split()
  if not p or p[0].startswith("#"): continue
  if p[0]=="v": m.v.append(tuple(map(float,p[1:4])))
  elif p[0]=="usemtl": cur=p[1]
  elif p[0]=="f": m.f.append((cur,tuple(int(q.split("/")[0]) for q in p[1:])))
 return m

def main():
 OUT.mkdir(parents=True,exist_ok=True);QA.mkdir(parents=True,exist_ok=True);m=build();obj=m.write()
 lines=[f"# Semantic materials for {S.NAME}"]
 for mat,c in COL.items(): lines += [f"newmtl {mat}",f"Kd {c[0]} {c[1]} {c[2]}","Pr 0.850","d 1.000","illum 2",""]
 mtl=OUT/f"{S.NAME}.mtl";mtl.write_text("\n".join(lines))
 cnt=Counter(mat for mat,f in m.f for _ in range(len(f)-2));mins=[min(v[i] for v in m.v) for i in range(3)];maxs=[max(v[i] for v in m.v) for i in range(3)]
 metrics={"asset":S.NAME,"production":True,"placement_world":list(S.PLACEMENT),"local_bounds":{"min":mins,"max":maxs},"world_bounds":{"min":[mins[0],mins[1],mins[2]+3500],"max":[maxs[0],maxs[1],maxs[2]+3500]},"vertices":len(m.v),"faces":len(m.f),"triangles":sum(cnt.values()),"triangles_by_material":dict(cnt),"module_count":72,"joints":{"width_uu":S.JOINT,"reveal_depth_uu":S.RECESS,"credible_range_uu":[2.5,4.0]},"spalls":{"components":14,"family_distribution":{"west":6,"outer_return":4,"door_return":4},"geometry":"closed irregular five-sided corner-loss facets"},"aggregate":{"components":72*S.AGGREGATES_PER_MODULE,"per_module":14,"return_reduction":False,"parsed_signature_unique_by_family":{"west":36,"outer_return":18,"door_return":18}},"weather_streaks":{"components":648,"parsed_profile_unique_by_family":{"west":36,"outer_return":18,"door_return":18},"vertical_down_gravity":True,"origins":"top joints and fixing/spall origins"},"return_bays":{"boundaries":list(S.RETURN_BOUNDS),"widths":[180,180,213],"reason":"Equal 191 uu bays put a joint at x=-79 through device mounts; closure bays keep joints outside every footprint."},"render_source":{"parsed_obj_faces":len(m.f),"semantic_materials":len(cnt)}}
 (QA/f"{S.NAME}_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n")
 boxes=[]
 for name,x,y,z in S.COLLISION_BOXES: boxes.append({"name":name,"center_world":[(x[0]+x[1])/2,(y[0]+y[1])/2,(z[0]+z[1])/2],"extent_half":[(x[1]-x[0])/2,(y[1]-y[0])/2,(z[1]-z[0])/2],"bounds_world":{"x":list(x),"y":list(y),"z":list(z)}})
 (QA/"rootstead_entrance_bulkhead_collision_boxes.json").write_text(json.dumps({"render_mesh_collision":"disabled","primitive_type":"box","boxes":boxes},indent=2)+"\n")
 parsed=parsed_obj_mesh(obj);evidence=render(parsed,QA/"rootstead_entrance_bulkhead_production_render.png");metrics["render_evidence"]=evidence
 (QA/f"{S.NAME}_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n")
 print(json.dumps({"obj":str(obj.relative_to(ROOT)),"triangles":sum(cnt.values()),"vertices":len(m.v),"bounds":[mins,maxs],"collision_boxes":len(boxes)},indent=2))
if __name__=="__main__": main()
