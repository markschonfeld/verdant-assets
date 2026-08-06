#!/usr/bin/env python3
"""Generate seamless 2K mature-stem bark PBR sets for VERDANT climbers.

Two sets are intentional. Solandra maxima needs heavier ropey cork; Aristolochia
macrophylla needs a slimmer, finer shallow-split surface. One shared bark normal
would erase the species distinction established by Botanical Study 05.

UV convention: image Y/V follows the stem axis; image X/U wraps circumference.
Contact flattening and polish belong to mesh/contact masks, not the repeating tile.
Normals are Unreal DirectX tangent-space (green-down).
"""
from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"textures"/"pbr"
QA=ROOT/"qa"/"climber_bark_pbr"
OUT.mkdir(parents=True,exist_ok=True)
QA.mkdir(parents=True,exist_ok=True)
N=2048
TAU=2*math.pi


def seal(a):
    a[-1,...]=a[0,...]; a[:,-1,...]=a[:,0,...]
    return a


def norm01(a,lo=1.0,hi=99.0):
    q0,q1=np.percentile(a,(lo,hi))
    return np.clip((a-q0)/max(float(q1-q0),1e-6),0,1).astype(np.float32)


def periodic_noise(seed,layers):
    rng=np.random.default_rng(seed); z=np.zeros((N,N),np.float32)
    for sigma,weight in layers:
        raw=rng.standard_normal((N,N),dtype=np.float32)
        v=gaussian_filter(raw,sigma=sigma,mode="wrap")
        v=(v-v.mean())/max(float(v.std()),1e-6); z+=weight*v
    return norm01(z)


def longitudinal_lines(seed,count,width,length):
    """Wandering fissures elongated along V, repeated safely on a torus."""
    rng=random.Random(seed); im=Image.new("L",(N,N),0); d=ImageDraw.Draw(im)
    for _ in range(count):
        x,y=rng.randrange(N),rng.randrange(N); total=rng.randint(*length)
        pts=[(float(x),float(y))]; steps=rng.randint(5,10)
        phase=rng.random()*TAU
        for j in range(1,steps+1):
            t=total*j/steps
            px=x+rng.uniform(-11,11)+12*math.sin(phase+j*.78)
            py=y+t
            pts.append((px,py))
        w=rng.randint(*width)
        for ox in (-N,0,N):
            for oy in (-N,0,N):
                d.line([(px+ox,py+oy) for px,py in pts],fill=255,width=w,joint="curve")
    return np.asarray(im,np.float32)/255


def rope_field(seed,frequency,warp_strength):
    yy,xx=np.mgrid[0:N,0:N].astype(np.float32)
    warp=periodic_noise(seed,((35,.30),(90,.42),(240,.28)))
    phase=TAU*frequency*xx/N + warp_strength*(warp-.5)
    # Rounded cords, not sinusoidal machining grooves.
    cord=(.5+.5*np.cos(phase))**1.7
    long_mod=.82+.18*np.sin(TAU*yy/N*3 + .7*np.sin(TAU*xx/N*2))
    return norm01(cord*long_mod)


def normal_dx(height,strength):
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))*strength
    dy=(np.roll(height,-1,0)-np.roll(height,1,0))*strength
    nx,ny,nz=-dx,dy,np.ones_like(height)
    inv=1/np.sqrt(nx*nx+ny*ny+nz*nz)
    return np.clip(np.stack((nx*inv*.5+.5,ny*inv*.5+.5,nz*inv*.5+.5),-1)*255,0,255).astype(np.uint8)


def ao_from_height(height,amount):
    small=gaussian_filter(height,6,mode="wrap")
    broad=gaussian_filter(height,26,mode="wrap")
    cavity=np.maximum(small-height,0)+.7*np.maximum(broad-height,0)
    return np.clip(255*(1-amount*norm01(cavity,8,99.4)),0,255).astype(np.uint8)


def colorize(base,terms):
    out=np.empty((N,N,3),np.float32); out[:]=np.array(base,np.float32)
    for mask,delta in terms: out+=mask[...,None]*np.array(delta,np.float32)
    return np.clip(out,0,255).astype(np.uint8)


def save_set(name,base,height,rough,normal_strength,ao_amount):
    Image.fromarray(seal(base.copy()),"RGB").save(OUT/f"{name}_basecolor.png",optimize=True)
    Image.fromarray(seal(normal_dx(height,normal_strength)),"RGB").save(OUT/f"{name}_normal.png",optimize=True)
    Image.fromarray(seal(np.clip(rough,0,255).astype(np.uint8)),"L").save(OUT/f"{name}_roughness.png",optimize=True)
    Image.fromarray(seal(ao_from_height(height,ao_amount)),"L").save(OUT/f"{name}_ao.png",optimize=True)


def bark_solandra_mature():
    macro=periodic_noise(8101,((24,.28),(70,.40),(190,.32)))
    fine=periodic_noise(8102,((2,.20),(6,.34),(15,.30),(42,.16)))
    rope=rope_field(8103,frequency=22,warp_strength=2.5)
    fiss=gaussian_filter(longitudinal_lines(8104,150,(2,7),(170,820)),.7,mode="wrap")
    hair=gaussian_filter(longitudinal_lines(8105,310,(1,3),(90,430)),.45,mode="wrap")
    # Rounded rope cords with real dark crevices and dry cork micro-breakup.
    height=.40+.16*(rope-.5)+.050*(macro-.5)+.035*(fine-.5)-.25*fiss-.08*hair
    pigment=periodic_noise(8106,((18,.30),(57,.42),(160,.28)))
    base=colorize((103,78,45),[
        (pigment-.5,(34,27,16)),(macro-.5,(17,12,7)),
        (fiss,(-47,-37,-24)),(hair,(-22,-16,-9)),
    ])
    rough=158+45*fine+30*macro+32*rope+38*fiss+14*hair
    save_set("bark_solandra_mature",base,height,rough,normal_strength=23,ao_amount=.76)


def bark_aristolochia_mature():
    macro=periodic_noise(8201,((32,.34),(96,.40),(240,.26)))
    fine=periodic_noise(8202,((3,.22),(9,.35),(24,.29),(61,.14)))
    grain=rope_field(8203,frequency=38,warp_strength=1.35)
    split=gaussian_filter(longitudinal_lines(8204,92,(1,4),(230,980)),.65,mode="wrap")
    hair=gaussian_filter(longitudinal_lines(8205,150,(1,2),(80,330)),.42,mode="wrap")
    # Shallower and smoother than Solandra: retain a cylindrical, thin-barked read.
    height=.42+.060*(grain-.5)+.026*(macro-.5)+.020*(fine-.5)-.145*split-.035*hair
    pigment=periodic_noise(8206,((22,.34),(72,.41),(190,.25)))
    base=colorize((92,74,47),[
        (pigment-.5,(25,21,14)),(macro-.5,(12,10,6)),
        (split,(-35,-29,-20)),(hair,(-14,-11,-7)),
    ])
    rough=128+42*fine+28*macro+20*grain+60*split+12*hair
    save_set("bark_aristolochia_mature",base,height,rough,normal_strength=18,ao_amount=.72)


def main():
    bark_solandra_mature(); bark_aristolochia_mature()
    print(f"generated 8 aligned seamless bark PBR maps in {OUT}")


if __name__=="__main__": main()
