#!/usr/bin/env python3
"""Independent artifact parser/verifier; exits nonzero on any production fault."""
from __future__ import annotations
import json,math,sys
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"scripts"))
import rootstead_entrance_bulkhead_spec as S
from mesh_hygiene import assert_obj_hygiene
OBJ=ROOT/f"SourceMesh/architecture/{S.NAME}.obj";MTL=OBJ.with_suffix(".mtl");QA=ROOT/"qa/rootstead_entrance_bulkhead";MET=QA/f"{S.NAME}_metrics.json";COL=QA/"rootstead_entrance_bulkhead_collision_boxes.json";PNG=QA/"rootstead_entrance_bulkhead_production_render.png"
def fail(x): raise AssertionError(x)
def overlap(a,b,strict=False):
 lo=max(a[0],b[0]);hi=min(a[1],b[1]);return lo<hi-1e-6 if strict else lo<=hi+1e-6
def parse():
 v=[];uv=[];f=[];objs=[];groups=[];cur=None;used=set()
 for line in OBJ.read_text().splitlines():
  p=line.split()
  if not p or p[0].startswith("#"):continue
  if p[0]=="v":v.append(tuple(map(float,p[1:4])))
  elif p[0]=="vt":uv.append(tuple(map(float,p[1:3])))
  elif p[0]=="o":objs.append(p[1])
  elif p[0]=="g":groups.append(p[1:])
  elif p[0]=="usemtl":cur=p[1];used.add(cur)
  elif p[0]=="f":
   if cur is None:fail("face before material")
   ids=[]
   for q in p[1:]:
    a=q.split("/");
    if len(a)<2 or not a[1]:fail("missing UV index")
    vi,ti=int(a[0]),int(a[1]);
    if not 1<=vi<=len(v) or not 1<=ti<=len(uv):fail("invalid OBJ index")
    ids.append(vi-1)
   f.append((cur,tuple(ids)))
 return v,uv,f,objs,groups,used
def aabb(v,face): return tuple((min(v[i][k] for i in face),max(v[i][k] for i in face)) for k in range(3))
def main():
 v,uv,faces,objs,groups,used=parse();checks={};failures=[]
 def check(name,cond,detail):
  checks[name]={"pass":bool(cond),"detail":detail}
  if not cond:failures.append(f"{name}: {detail}")
 check("obj_contract",objs==[S.NAME] and not groups and bool(faces),{"objects":objs,"groups":len(groups),"faces":len(faces),"uvs":len(uv)})
 mtl={p[1] for l in MTL.read_text().splitlines() if (p:=l.split()) and p[0]=="newmtl"}
 check("materials",used==mtl==S.MATERIALS and not any(b in x.lower() for x in used for b in S.BANNED),{"used":sorted(used),"mtl":sorted(mtl)})
 tri=Counter();edges=defaultdict(int);adj=defaultdict(set);deg=0
 for mat,f in faces:
  tri[mat]+=len(f)-2
  for i in range(1,len(f)-1):
   a,b,c=(v[f[j]] for j in(0,i,i+1));ab=[b[k]-a[k] for k in range(3)];ac=[c[k]-a[k] for k in range(3)];cr=(ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]);deg+=math.sqrt(sum(x*x for x in cr))<2e-4
  for a,b in zip(f,f[1:]+f[:1]):edges[tuple(sorted((a,b)))]+=1;adj[a].add(b);adj[b].add(a)
 unseen=set(range(len(v)));comps=[]
 while unseen:
  q=[next(iter(unseen))];c=set()
  while q:
   x=q.pop()
   if x in c:continue
   c.add(x);unseen.discard(x);q.extend(adj[x]-c)
  comps.append(c)
 badedges=sum(n!=2 for n in edges.values());hygiene=assert_obj_hygiene(OBJ);detail:dict[str,object]=dict(hygiene);detail["components"]=len(comps);detail["non_two_face_edges_advisory"]=badedges;detail["manifold_note"]="assembled touching primitives are welded for render hygiene; edge incidence is advisory";check("mesh_hygiene",bool(hygiene["pass"]),detail)
 mins=tuple(min(x[i] for x in v) for i in range(3));maxs=tuple(max(x[i] for x in v) for i in range(3));check("bounds_and_placement",maxs[0]==112 and mins[0]==-465.2 and mins[1]==-1300 and maxs[1]==1300 and mins[2]==0 and maxs[2]==825,{"placement":S.PLACEMENT,"local_min":mins,"local_max":maxs,"required_exact_y":[-1300,1300],"east_limit":maxs[0]})
 metrics=json.loads(MET.read_text());check("metrics_exact",metrics["triangles"]==sum(tri.values()) and metrics["triangles_by_material"]==dict(tri) and metrics["local_bounds"]=={"min":list(mins),"max":list(maxs)},{"parsed_total":sum(tri.values()),"metrics_total":metrics["triangles"],"by_material":dict(tri)})
 # Every parsed face AABB against each real occupied volume. Merely touching
 # the clear doorway y boundary is allowed; occupied hardware boundaries are not.
 intr={k:0 for k in S.EXCLUSIONS}
 for _,f in faces:
  b=aabb(v,f)
  for name,e in S.EXCLUSIONS.items():
   if overlap(b[0],e[0],True) and overlap(b[1],e[1],True) and overlap(b[2],e[2],True):intr[name]+=1
 check("true_exclusions",not any(intr.values()),{"intrusion_faces":intr,"wend_entry_rule":"east-plane only"})
 inside_v=sum(-424+1e-6<x[1]<424-1e-6 for x in v);cross_f=sum(min(v[i][1] for i in f)<424-1e-6<max(v[i][1] for i in f) and max(v[i][1] for i in f)>-424+1e-6 for _,f in faces)
 check("strict_doorway_global",inside_v==0 and cross_f==0,{"vertices_strict_inside":inside_v,"faces_crossing":cross_f})
 # Structural analytic coverage, dense deterministic grid against collision-box union.
 boxes=json.loads(COL.read_text())["boxes"]
 def in_box(p,b):
  q=b["bounds_world"];return q["x"][0]<=p[0]<=q["x"][1] and q["y"][0]<=p[1]<=q["y"][1] and q["z"][0]-3500<=p[2]<=q["z"][1]-3500
 miss=0;unexpected=0;samples=0
 for x in [-461+i*573/24 for i in range(25)]:
  for ay in [424+i*876/24 for i in range(25)]:
   for y in (-ay,ay):
    for z in [i*825/16 for i in range(17)]:
     intended=not(abs(y)<462 and -412<x<-350 and z<450);covered=any(in_box((x,y,z),b) for b in boxes);miss+=intended and not covered;unexpected+=(not intended) and covered;samples+=1
 check("structural_solid_coverage",not miss and not unexpected,{"samples":samples,"missing":miss,"inside_declared_notches":unexpected,"walkable_internal_pocket":False})
 # Flat mounting rectangles: boundary faces must cover all deterministic samples;
 # no joint/seal face may project through the rectangles.
 mounts={}
 for name,m in S.MOUNTS.items():
  covered=0;bad=0;total=0
  for ix in range(9):
   for iz in range(9):
    x=m["x"][0]+(m["x"][1]-m["x"][0])*ix/8;z=m["z"][0]+(m["z"][1]-m["z"][0])*iz/8;total+=1
    hits=[]
    for mat,f in faces:
     b=aabb(v,f)
     if abs(b[1][0]-m["y"])<1e-5 and abs(b[1][1]-m["y"])<1e-5 and b[0][0]-1e-6<=x<=b[0][1]+1e-6 and b[2][0]-1e-6<=z<=b[2][1]+1e-6:hits.append(mat)
    covered+=S.MAT_PRECAST in hits;bad+=any(q in hits for q in(S.MAT_JOINT,S.MAT_SEAL))
  clearance=min(m["x"][0]-(-90.),-10.-m["x"][1],m["z"][0]-120.,330.-m["z"][1])
  mounts[name]={"plane_y":m["y"],"normal":m["normal"],"samples":total,"covered":covered,"joint_or_recess_hits":bad,"minimum_course_or_joint_clearance":clearance}
 check("mounting_faces",all(x["covered"]==x["samples"] and x["joint_or_recess_hits"]==0 for x in mounts.values()),mounts)
 # Derive joint width from parsed precast backing vertices at every authored
 # module boundary; metadata alone cannot satisfy this regression gate.
 pv={i for mat,f in faces if mat==S.MAT_PRECAST for i in f}
 half_offsets=[]
 for i in pv:
  x,y,z=v[i]
  if x<-460.9:
   ds=[abs(y-q) for q in S.WEST_BOUNDS];ds=[d for d in ds if 1e-4<d<10]
  else:
   ds=[abs(x-q) for q in S.RETURN_BOUNDS];ds=[d for d in ds if 1e-4<d<10]
  half_offsets.extend(ds)
 derived_joint=round(2*min(half_offsets),6) if half_offsets else None
 joint_ok=derived_joint is not None and 2.5<=derived_joint<=4.0 and S.JOINT<=4.0 and metrics["joints"]=={"width_uu":S.JOINT,"reveal_depth_uu":S.RECESS,"credible_range_uu":[2.5,4.0]}
 check("architectural_joint_scale",joint_ok,{"parsed_width_uu":derived_joint,"contract_width_uu":S.JOINT,"maximum_uu":4.0,"reveal_depth_uu":S.RECESS})
 # Aggregate components and per-family density/variation by parsed topology and
 # normalized component centroids. No generator-side module identifiers exist.
 vf=defaultdict(set)
 for fi,(_,f) in enumerate(faces):
  for i in f:vf[i].add(fi)
 def comp_mats(c):return {faces[fi][0] for i in c for fi in vf[i]}
 def locate(c):
  p=tuple(sum(v[i][k] for i in c)/len(c) for k in range(3));x,y,z=p
  if x<-461.001: family="west";u=y;bounds=S.WEST_BOUNDS
  elif abs(y)>1000: family="outer_return";u=x;bounds=S.RETURN_BOUNDS
  else: family="door_return";u=x;bounds=S.RETURN_BOUNDS
  pairs=[(a,b) for a,b in zip(bounds,bounds[1:]) if not(a==-424 and b==424)]
  col=next((j for j,(a,b) in enumerate(pairs) if a-1e-3<=u<=b+1e-3),None)
  row=next((j for j,(a,b) in enumerate(zip(S.COURSE_BOUNDS,S.COURSE_BOUNDS[1:])) if a-1e-3<=z<=b+1e-3),None)
  side=-1 if y<0 else 1
  return family,(side,col,row),p
 aggcomps=[]
 for c in comps:
  mats=comp_mats(c)
  if mats=={S.MAT_AGG}:aggcomps.append(c)
 modules=defaultdict(list)
 for c in aggcomps:
  fam,key,p=locate(c);modules[(fam,)+key].append(p)
 density=Counter(k[0] for k,a in modules.items() if len(a)==14)
 signatures=defaultdict(set)
 for key,pts in modules.items():
  fam,side,col,row=key
  ub=S.WEST_BOUNDS if fam=="west" else S.RETURN_BOUNDS;pairs=[(a,b) for a,b in zip(ub,ub[1:]) if not(a==-424 and b==424)];a,b=pairs[col];za,zb=S.COURSE_BOUNDS[row:row+2]
  vals=[]
  for x,y,z in pts: vals.append((round(((y if fam=="west" else x)-a)/(b-a),3),round((z-za)/(zb-za),3)))
  signatures[fam].add(tuple(sorted(vals)))
 variation={fam:{"modules":sum(k[0]==fam for k in modules),"unique_centroid_signatures":len(sigs)} for fam,sigs in signatures.items()}
 dense=(len(aggcomps)==72*14 and len(modules)==72 and all(len(a)==14 for a in modules.values()) and density==Counter({"west":36,"outer_return":18,"door_return":18}))
 check("aggregate_density",dense,{"components":len(aggcomps),"expected":1008,"modules":len(modules),"per_module":14,"dense_modules_by_family":dict(density),"return_reduction":False})
 varied=variation.get("west",{}).get("unique_centroid_signatures",0)>=30 and variation.get("outer_return",{}).get("unique_centroid_signatures",0)>=15 and variation.get("door_return",{}).get("unique_centroid_signatures",0)>=15
 metric_agg={k:v["unique_centroid_signatures"] for k,v in variation.items()}
 varied=varied and metrics["aggregate"]["parsed_signature_unique_by_family"]==metric_agg
 check("aggregate_stamp_variation",varied,{"method":"sorted normalized parsed component-centroid signatures rounded to 0.001","families":variation,"minimum_unique":{"west":30,"outer_return":15,"door_return":15}})
 streak_faces=[f for m,f in faces if m==S.MAT_STREAK];streak_comps=[]
 for c in comps:
  mats=comp_mats(c)
  if mats=={S.MAT_STREAK}:streak_comps.append(c)
 badstreak=0
 for c in streak_comps:
  b=tuple((min(v[i][k] for i in c),max(v[i][k] for i in c)) for k in range(3));badstreak+=(b[2][1]-b[2][0])<=min(x for x in (b[0][1]-b[0][0],b[1][1]-b[1][0]) if x>1e-6)
 origin_tops=sum(any(abs(aabb(v,f)[2][1]-q)<1e-5 for q in tuple(z-S.JOINT/2 for z in S.COURSE_BOUNDS[1:])+tuple(z+S.JOINT/2+26 for z in S.COURSE_BOUNDS[:-1])) for f in streak_faces)
 streakmods=defaultdict(list)
 for c in streak_comps:
  fam,key,p=locate(c);b=tuple((min(v[i][k] for i in c),max(v[i][k] for i in c)) for k in range(3));u=p[1] if fam=="west" else p[0];streakmods[(fam,)+key].append((round(u,2),round(b[2][1],2),round(b[2][1]-b[2][0],2),round(min(q[1]-q[0] for q in b[:2] if q[1]-q[0]>1e-5),2)))
 streak_unique=defaultdict(set)
 for k,runs in streakmods.items():streak_unique[k[0]].add(tuple(sorted(runs)))
 streak_variation={k:len(x) for k,x in streak_unique.items()};weather_varied=len(streakmods)==72 and all(x>=15 for x in streak_variation.values())
 weather_varied=weather_varied and metrics["weather_streaks"]["components"]==len(streak_comps) and metrics["weather_streaks"]["parsed_profile_unique_by_family"]==streak_variation
 check("geometry_obedient_weather",badstreak==0 and origin_tops>=216 and weather_varied,{"streak_faces":len(streak_faces),"streak_components":len(streak_comps),"non_vertical_components":badstreak,"joint_sill_fixing_origin_top_faces":origin_tops,"module_profiles":len(streakmods),"unique_profiles_by_family":streak_variation,"orientation":"vertical local Z","identical_stamp":False})
 # Spalls and rebar are independently classified from parsed topology/materials.
 spallcomps=[c for c in comps if comp_mats(c)=={S.MAT_SPALL}]
 rebarcomps=[c for c in comps if comp_mats(c)=={S.MAT_REBAR}]
 sfam=Counter();footprints=[];corners=set();associated=0
 rebar_centres=[tuple(sum(v[i][k] for i in c)/len(c) for k in range(3)) for c in rebarcomps]
 for c in spallcomps:
  p=tuple(sum(v[i][k] for i in c)/len(c) for k in range(3));span=[max(v[i][k] for i in c)-min(v[i][k] for i in c) for k in range(3)]
  if span[1]>span[0]: fam="west";u=p[1];bounds=S.WEST_BOUNDS;side=-1 if p[1]<0 else 1
  else: fam="outer_return" if abs(p[1])>1000 else "door_return";u=p[0];bounds=S.RETURN_BOUNDS;side=-1 if p[1]<0 else 1
  pairs=[(a,b) for a,b in zip(bounds,bounds[1:]) if not(a==-424 and b==424)];col=next(j for j,(a,b) in enumerate(pairs) if a-1e-3<=u<=b+1e-3);row=next(j for j,(a,b) in enumerate(zip(S.COURSE_BOUNDS,S.COURSE_BOUNDS[1:])) if a-1e-3<=p[2]<=b+1e-3);key=(side,col,row);sfam[fam]+=1
  axes=(1,2) if fam=="west" else (0,2);pts={(round(v[i][axes[0]],4),round(v[i][axes[1]],4)) for i in c}
  footprints.append((len(c),len(pts),round(max(q[0] for q in pts)-min(q[0] for q in pts),2),round(max(q[1] for q in pts)-min(q[1] for q in pts),2)))
  side,col,row=key;ub=S.WEST_BOUNDS if fam=="west" else S.RETURN_BOUNDS;pairs=[(a,b) for a,b in zip(ub,ub[1:]) if not(a==-424 and b==424)];a,b=pairs[col];za,zb=S.COURSE_BOUNDS[row:row+2];u=p[1] if fam=="west" else p[0]
  corners.add(("L" if abs(u-a)<abs(u-b) else "R")+("B" if abs(p[2]-za)<abs(p[2]-zb) else "T"))
  associated+=any(math.dist(p,r)<24 for r in rebar_centres)
 non_rect=all(nv!=8 and np>=5 for nv,np,_,_ in footprints);irregular=len(set(footprints))>=6 and len(corners)>=4
 spall_ok=len(spallcomps)==14 and sfam==Counter({"west":6,"outer_return":4,"door_return":4}) and non_rect and irregular and len(rebarcomps)==14 and associated==14
 check("irregular_corner_spalls",spall_ok,{"components":len(spallcomps),"family_distribution":dict(sfam),"vertex_projected_width_height_signatures":len(set(footprints)),"all_non_box_non_rectangular":non_rect,"corner_signatures":sorted(corners),"rebar_components":len(rebarcomps),"rebar_associated_within_24uu":associated})
 cintr={k:0 for k in S.EXCLUSIONS};bridges=0
 for b in boxes:
  q=b["bounds_world"];lb=(tuple(q["x"]),tuple(q["y"]),(q["z"][0]-3500,q["z"][1]-3500));bridges+=q["y"][0]<-424 and q["y"][1]>424
  for name,e in S.EXCLUSIONS.items():
   if overlap(lb[0],e[0],True) and overlap(lb[1],e[1],True) and overlap(lb[2],e[2],True):cintr[name]+=1
 check("collision",not any(cintr.values()) and not bridges,{"box_count":len(boxes),"intrusions":cintr,"doorway_bridging_boxes":bridges,"render_mesh_collision":"disabled"})
 from PIL import Image
 with Image.open(PNG) as im: png={"size":list(im.size),"mode":im.mode}
 ev=metrics["render_evidence"];vs=ev["view_stats"];required={"FULL WEST ELEVATION","WEST FRACTURE DETAIL - 9 MODULES","DOOR RETURN - FROM PASSAGE","OUTER RETURN - FROM OUTSIDE"}
 render_ok=png["size"][0]>=2400 and png["mode"]=="RGB" and ev["image_size"]==png["size"] and ev["z_buffer"] is True and ev["parsed_obj_vertices"]==len(v) and ev["parsed_obj_faces"]==len(faces) and ev["parsed_obj_triangles"]==sum(tri.values()) and set(ev["view_names"])==required
 check("faithful_render",render_ok,png|{k:ev[k] for k in ("renderer","z_buffer","two_sided","parsed_obj_vertices","parsed_obj_faces","parsed_obj_triangles","view_names")})
 visual_ok=vs["FULL WEST ELEVATION"]["coverage"]>=.5 and all(vs[n]["coverage"]>=.35 for n in required) and vs["DOOR RETURN - FROM PASSAGE"]["semantic_color_count"]>=5 and vs["OUTER RETURN - FROM OUTSIDE"]["semantic_color_count"]>=5 and vs["DOOR RETURN - FROM PASSAGE"]["structural_fraction_of_ink"]<.72 and vs["OUTER RETURN - FROM OUTSIDE"]["structural_fraction_of_ink"]<.72
 check("render_visual_sanity",visual_ok,{"thresholds":{"viewport_coverage_min":.35,"west_coverage_min":.5,"return_semantic_colors_min":5,"return_structural_fraction_max":.72},"measured":vs})
 check("render_spall_no_rectangle_stamp",non_rect and len(set(footprints))>=6,{"source":"actual parsed MAT_SPALL topology projected in each face plane","components":len(footprints),"identical_axis_aligned_rectangle_components":sum(nv==8 or np==4 for nv,np,_,_ in footprints),"unique_signatures":len(set(footprints))})
 check("production_paths",all("Proto" not in str(p) and "proto" not in str(p) for p in(OBJ,MTL,MET,COL,PNG)),{"prototype_geometry_contamination":False})
 report={"verified":not failures,"failures":failures,"checks":checks,"parsed":{"vertices":len(v),"faces":len(faces),"components":len(comps),"triangles":sum(tri.values()),"triangles_by_material":dict(tri),"local_bounds":{"min":mins,"max":maxs}},"variation":{"aggregate":variation,"weather_unique_profiles":streak_variation},"intrusion_faces":intr,"mounts":mounts,"collision_box_count":len(boxes)}
 (QA/"rootstead_entrance_bulkhead_verification.json").write_text(json.dumps(report,indent=2)+"\n")
 if failures:fail("; ".join(failures))
 print(json.dumps(report,indent=2))
if __name__=="__main__":
 try:main()
 except (AssertionError,ValueError,KeyError) as e:print(f"VERIFY FAILED: {e}",file=sys.stderr);raise SystemExit(1)
