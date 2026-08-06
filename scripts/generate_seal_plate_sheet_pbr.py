#!/usr/bin/env python3
"""Generate the seamless 2K improvised seal-plate sheet PBR set.

This is unpainted, lightly galvanised rolled sheet cut and fixed over failed
triangular panes after construction. It deliberately shares no pigment or wear
field with `steel_painted`: pattern identity is material identity.

The edge dimple rows assume pane-local 0..1 UVs. If VD_TriPane uses world or
triplanar projection, use the bulk maps for the sheet and place edge fasteners
from pane barycentrics/geometry instead of expecting a texture to find edges.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

from generate_batch3_pbr import N, ao_from_height, norm01, normal_dx, periodic_noise, wrapped_lines

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"textures"/"pbr"
QA=ROOT/"qa"/"seal_plate_sheet"
OUT.mkdir(parents=True,exist_ok=True); QA.mkdir(parents=True,exist_ok=True)


def seal(a:np.ndarray)->np.ndarray:
    a[-1,...]=a[0,...]; a[:,-1,...]=a[:,0,...]; return a


def save_rgb(suffix:str,a:np.ndarray)->None:
    Image.fromarray(seal(a.copy()),"RGB").save(OUT/f"seal_plate_sheet_{suffix}.png",optimize=True)


def save_l(suffix:str,a:np.ndarray)->None:
    Image.fromarray(seal(a.copy()),"L").save(OUT/f"seal_plate_sheet_{suffix}.png",optimize=True)


def torus_dimple_rows()->tuple[np.ndarray,np.ndarray]:
    """Shallow improvised spot-weld/screw dimples 64 px inside each UV edge."""
    yy,xx=np.mgrid[0:N,0:N].astype(np.float32)
    pit=np.zeros((N,N),np.float32); ring=np.zeros_like(pit)
    spacing=256; inset=64
    centers=[]
    for p in range(128,N,spacing):
        centers.extend(((p,inset),(p,N-inset),(inset,p),(N-inset,p)))
    # Omit a few deterministically so the hurried closure is not machine-perfect.
    centers=[c for i,c in enumerate(centers) if i%11 not in (3,)]
    for cx,cy in centers:
        dx=np.minimum(np.abs(xx-cx),N-np.abs(xx-cx)); dy=np.minimum(np.abs(yy-cy),N-np.abs(yy-cy))
        r=np.sqrt(dx*dx+dy*dy)
        pit=np.maximum(pit,np.exp(-(r/13.0)**2))
        ring=np.maximum(ring,np.exp(-((r-24.0)/7.0)**2))
    return pit,ring


def generate()->None:
    yy,xx=np.mgrid[0:N,0:N].astype(np.float32)
    # Subtle zinc/mill-finish identity. Interest lives chiefly in roughness.
    micro=periodic_noise(9101,((2,.18),(5,.27),(13,.31),(31,.24)))
    spangle=periodic_noise(9102,((12,.20),(28,.36),(62,.30),(128,.14)))
    broad=periodic_noise(9103,((80,.46),(190,.36),(420,.18)))
    handling=periodic_noise(9104,((35,.30),(90,.42),(240,.28)))
    roll=.5+.5*np.sin(2*math.pi*(yy/N*118 + .020*np.sin(2*math.pi*xx/N*3)))
    roll=gaussian_filter(roll,sigma=(1.4,.5),mode="wrap")
    scratches=np.maximum(
        gaussian_filter(wrapped_lines(9105,26,horizontal=True,width=(1,3),length=(120,690)),.55,mode="wrap"),
        .65*gaussian_filter(wrapped_lines(9106,13,horizontal=False,width=(1,2),length=(90,420)),.55,mode="wrap"))
    scratches=np.clip(scratches,0,1)
    dimple,ring=torus_dimple_rows()

    # Base colour contains mill/zinc pigment and handling variation only: no
    # multiplication by height, AO, normal or any directional lighting term.
    base=np.empty((N,N,3),np.float32); base[:]=np.array((164,166,163),np.float32)
    base+=(spangle-.5)[...,None]*np.array((13,12,9),np.float32)
    base+=(broad-.5)[...,None]*np.array((8,9,8),np.float32)
    base+=(handling-.5)[...,None]*np.array((-9,-8,-6),np.float32)
    base+=(roll-.5)[...,None]*np.array((3.0,3.2,3.0),np.float32)
    base+=scratches[...,None]*np.array((11,10,8),np.float32)
    # Local metal-state change at hurried weld/dimple sites, not painted shadow.
    base+=ring[...,None]*np.array((-7,-6,-4),np.float32)
    base=np.clip(base,0,255).astype(np.uint8)

    # Flat sheet: shallow roll texture and handling scratches. Dimples provide the
    # only feature large enough to survive at a pane edge.
    height=(.014*(micro-.5)+.010*(spangle-.5)+.006*(roll-.5)+.020*scratches
            -.145*dimple+.030*ring)
    rough=108+74*spangle+38*broad-52*handling+62*scratches+34*ring+28*dimple
    rough=np.clip(rough,68,228).astype(np.uint8)
    ao=ao_from_height(height,.48)

    save_rgb("basecolor",base)
    save_rgb("normal",normal_dx(height,18.0))
    save_l("roughness",rough)
    save_l("ao",ao)
    print("Generated seal_plate_sheet_{basecolor,normal,roughness,ao}.png")


if __name__=="__main__": generate()
