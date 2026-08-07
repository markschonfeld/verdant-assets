#!/usr/bin/env python3
"""Independently parse and verify the Rootstead bulkhead budget prototype."""
from __future__ import annotations
import json, math, sys
from collections import Counter, defaultdict, deque
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"scripts"))
import rootstead_entrance_bulkhead_proto_spec as spec
OBJ=ROOT/"SourceMesh/architecture/VD_RootsteadEntranceBulkhead_Proto.obj"
MTL=ROOT/"SourceMesh/architecture/VD_RootsteadEntranceBulkhead_Proto.mtl"
MET=ROOT/"qa/rootstead_entrance_bulkhead/prototype/VD_RootsteadEntranceBulkhead_Proto_metrics.json"

def fail(msg): raise AssertionError(msg)
def close(a,b,t=1e-4): return abs(a-b)<=t
def main():
    verts=[]; uvs=[]; faces=[]; objects=[]; groups=[]; used=set(); current=None
    for line in OBJ.read_text(encoding="utf-8").splitlines():
        p=line.split()
        if not p or p[0].startswith("#"): continue
        if p[0]=="o": objects.append(" ".join(p[1:]))
        elif p[0]=="g": groups.append(p[1:])
        elif p[0]=="v": verts.append(tuple(map(float,p[1:4])))
        elif p[0]=="vt": uvs.append(tuple(map(float,p[1:3])))
        elif p[0]=="usemtl": current=p[1]; used.add(current)
        elif p[0]=="f":
            if current is None: fail("face before usemtl")
            corners=[]
            for token in p[1:]:
                bits=token.split("/")
                if len(bits)<2 or not bits[1]: fail("face corner missing UV")
                vi,ti=int(bits[0]),int(bits[1])
                if not 1<=vi<=len(verts) or not 1<=ti<=len(uvs): fail("invalid vertex/UV index")
                corners.append(vi-1)
            faces.append((current,tuple(corners)))
    if len(objects)!=1 or objects[0]!=spec.OBJ_NAME: fail(f"expected exactly one object: {objects}")
    if groups: fail("OBJ contains forbidden g records")
    if not faces: fail("no faces")
    mtlset={p[1] for line in MTL.read_text(encoding="utf-8").splitlines() if (p:=line.split()) and p[0]=="newmtl"}
    if used!=mtlset: fail(f"OBJ/MTL material mismatch: {used ^ mtlset}")
    if not used<=spec.ALLOWED_MATERIALS: fail(f"non-semantic materials: {used-spec.ALLOWED_MATERIALS}")
    for name in used:
        if any(b in name.lower() for b in spec.BANNED_NAME_SUBSTRINGS): fail(f"banned fabricated-metal material: {name}")
    mins=tuple(min(v[i] for v in verts) for i in range(3)); maxs=tuple(max(v[i] for v in verts) for i in range(3))
    for got,want in zip(mins,spec.EXPECTED_MIN):
        if not close(got,want,spec.TOL_BOUNDS): fail(f"local min bounds {mins} != {spec.EXPECTED_MIN}")
    for got,want in zip(maxs,spec.EXPECTED_MAX):
        if not close(got,want,spec.TOL_BOUNDS): fail(f"local max bounds {maxs} != {spec.EXPECTED_MAX}")
    counts=Counter(); edges=defaultdict(list); adjacency=defaultdict(set)
    for fi,(mat,f) in enumerate(faces):
        counts[mat]+=len(f)-2
        for i in range(1,len(f)-1):
            a,b,c=(verts[f[j]] for j in (0,i,i+1)); ab=tuple(b[k]-a[k] for k in range(3)); ac=tuple(c[k]-a[k] for k in range(3))
            cross=(ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0])
            if .5*math.sqrt(sum(x*x for x in cross))<=spec.DEGENERATE_AREA_EPS: fail(f"degenerate fan triangle in face {fi}")
        for a,b in zip(f,f[1:]+f[:1]):
            e=tuple(sorted((a,b))); edges[e].append(fi); adjacency[a].add(b); adjacency[b].add(a)
    # Components are based on indexed topology; each authored primitive must close itself.
    unseen=set(range(len(verts))); components=[]
    while unseen:
        seed=next(iter(unseen)); q=[seed]; comp=set()
        while q:
            v=q.pop()
            if v in comp: continue
            comp.add(v); unseen.discard(v); q.extend(adjacency[v]-comp)
        components.append(comp)
    for ci,comp in enumerate(components):
        ce=[e for e in edges if e[0] in comp or e[1] in comp]
        if any(len(edges[e])!=2 for e in ce): fail(f"component {ci} is not closed/manifold")
    metrics=json.loads(MET.read_text(encoding="utf-8"))
    if dict(counts)!=metrics["triangle_counts_by_category"]: fail("parsed per-material triangle counts differ from metrics")
    if sum(counts.values())!=metrics["total_prototype_triangles"]: fail("parsed triangle total differs from metrics")
    if any(not close(metrics["local_bounds_uu"]["min"][i],mins[i]) or not close(metrics["local_bounds_uu"]["max"][i],maxs[i]) for i in range(3)): fail("parsed bounds differ from metrics")
    # Aggregate components, variation and non-grid distribution.
    agg=[]
    for comp in components:
        fis={fi for e in edges for fi in edges[e] if e[0] in comp and e[1] in comp}
        if fis and all(faces[fi][0]==spec.MAT_AGGREGATE for fi in fis):
            bmin=tuple(min(verts[v][i] for v in comp) for i in range(3)); bmax=tuple(max(verts[v][i] for v in comp) for i in range(3))
            agg.append((bmin,bmax))
    if len(agg)!=spec.AGGREGATE_COUNT: fail(f"aggregate component count {len(agg)}")
    sizes=[max(b[1][1]-b[0][1],b[1][2]-b[0][2])/2 for b in agg]
    if min(sizes)<spec.AGGREGATE_RADIUS_RANGE[0]*.65 or max(sizes)>spec.AGGREGATE_RADIUS_RANGE[1]*1.2: fail("aggregate size range invalid")
    if len({round(s,1) for s in sizes})<7: fail("insufficient aggregate size/form variation")
    centers=[((a[1]+b[1])/2,(a[2]+b[2])/2) for a,b in agg]
    if len({round(y,1) for y,z in centers})<12 or len({round(z,1) for y,z in centers})<12: fail("aggregate distribution resembles a grid")
    # Every streak top must coincide with one of the declared joint/fixing origins.
    streak_comps=[]
    for comp in components:
        mats={faces[fi][0] for e in edges for fi in edges[e] if e[0] in comp and e[1] in comp}
        if mats=={spec.MAT_STREAK}: streak_comps.append(comp)
    expected_tops={spec.PLINTH_H+spec.MODULE_H-spec.JOINT_WIDTH/2, spec.PLINTH_H+spec.JOINT_WIDTH/2+26.0}
    streak_runs=defaultdict(list)
    for c in streak_comps:
        yc=sum(verts[v][1] for v in c)/len(c); streak_runs[round(yc,2)].append(max(verts[v][2] for v in c))
    if len(streak_runs)!=3 or any(not any(close(max(tops),z) for z in expected_tops) for tops in streak_runs.values()): fail("streak origin is not under joint/fixing source")
    precast_x=min(verts[v][0] for mat,f in faces if mat==spec.MAT_PRECAST for v in f)
    if not close(precast_x,spec.FACE_X): fail(f"expected world-aligned west face x=-461, got {precast_x}")
    span=tuple(maxs[i]-mins[i] for i in range(3))
    if span[1]>spec.MODULE_W+2 or span[2]>spec.PLINTH_H+spec.MODULE_H+2 or len(verts)>3000: fail("prototype appears accidentally full-wall scale")
    if metrics["modules_represented"]!=1: fail("metrics does not declare one represented module")
    layout=metrics["projection"]["module_layout"]
    if layout["module_count_full_wall"]!=72 or sum(f["module_equivalents"] for f in layout["face_families"].values())!=72: fail("full-wall face-family module projection is incomplete")
    if metrics["expected_world_face_x_uu"]!=-461.0: fail("metrics expected west face is not replacement extent")
    print(json.dumps({"verified":True,"object_records":1,"group_records":0,"vertices":len(verts),"components":len(components),"aggregate_components":len(agg),"local_bounds":{"min":mins,"max":maxs},"triangles":sum(counts.values()),"triangles_by_material":dict(counts)},indent=2))
if __name__=="__main__":
    try: main()
    except (AssertionError,ValueError,KeyError) as e:
        print(f"VERIFY FAILED: {e}",file=sys.stderr); raise SystemExit(1)
