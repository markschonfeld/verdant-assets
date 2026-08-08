#!/usr/bin/env python3
"""Pack VERDANT's separate AO / roughness / metallic maps into ORM textures.

WHY THIS EXISTS
    The Unreal project does not sample the separate `_ao` and `_roughness`
    files this repository ships. It samples a single packed texture whose
    channels are, by this project's convention:

        R = ambient occlusion
        G = roughness
        B = metallic

    That packed file used to be produced by hand outside the repository, so a
    fresh clone could not reproduce what the engine actually renders. This
    script closes that gap: it is the recorded, deterministic step between the
    authored maps and the texture the material samples.

DETERMINISM
    Packing is a straight per-channel byte copy. There is no resampling, no
    colour management and no randomness, so the output is bit-identical on
    every run and on every machine. `--check` re-packs in memory and compares
    against what is on disk, which is what CI should call.

LINEAR DATA, NOT COLOUR
    ORM carries measurements, not colour. The bytes are copied verbatim and the
    texture must be imported with sRGB OFF and compression TC_MASKS, matching
    /Game/Textures/PBR/precast_exposed_aggregate_orm. Importing it as sRGB
    silently gamma-shifts roughness and AO.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PBR = ROOT / "textures" / "pbr"
QA = ROOT / "qa" / "orm_packing"
MANIFEST = PBR / "material_scale_manifest.json"

# Only sets whose material actually samples an ORM slot are packed. Adding a
# set here is a one-line change; see the survey note in README.md for why
# alu_oxidised is deliberately absent.
ORM_SETS = ("precast_exposed_aggregate", "concrete_formed")


def load_channel(name: str, suffix: str) -> np.ndarray:
    """Read one authored map as a single 8-bit channel."""
    path = PBR / f"{name}_{suffix}.png"
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing; cannot pack {name}")
    with Image.open(path) as im:
        if im.mode not in ("L", "RGB", "RGBA"):
            raise ValueError(f"{path.name} has unexpected mode {im.mode}")
        # A greyscale mask authored as RGB has three equal channels; take one
        # rather than luminance-weighting it, which would alter the values.
        arr = np.array(im.convert("L") if im.mode == "L" else im)
        if arr.ndim == 3:
            if not np.array_equal(arr[..., 0], arr[..., 1]):
                raise ValueError(f"{path.name} is not greyscale; refusing to guess a channel")
            arr = arr[..., 0]
    return arr.astype(np.uint8)


def pack(name: str, metallic: int) -> tuple[np.ndarray, dict[str, Any]]:
    """Compose one ORM image and the facts worth recording about it."""
    ao = load_channel(name, "ao")
    rough = load_channel(name, "roughness")
    if ao.shape != rough.shape:
        raise ValueError(f"{name}: ao {ao.shape} and roughness {rough.shape} differ")

    metal_path = PBR / f"{name}_metallic.png"
    if metal_path.exists():
        metal = load_channel(name, "metallic")
        metal_source = f"{name}_metallic.png"
        if metal.shape != ao.shape:
            raise ValueError(f"{name}: metallic {metal.shape} does not match ao {ao.shape}")
    else:
        # A dielectric with no authored map gets the manifest's flat constant.
        metal = np.full(ao.shape, metallic * 255, np.uint8)
        metal_source = f"constant {metallic} from material_scale_manifest.json"

    orm = np.dstack((ao, rough, metal))
    report = {
        "resolution": [int(ao.shape[1]), int(ao.shape[0])],
        "channels": {
            "R": {"content": "ambient occlusion", "source": f"{name}_ao.png"},
            "G": {"content": "roughness", "source": f"{name}_roughness.png"},
            "B": {"content": "metallic", "source": metal_source},
        },
        "stats": {
            ch: {
                "min": int(a.min()), "max": int(a.max()),
                "mean": round(float(a.mean()), 3),
                "stddev": round(float(a.std()), 3),
            }
            for ch, a in (("R", ao), ("G", rough), ("B", metal))
        },
        "unreal_import": {"srgb": False, "compression": "TC_MASKS", "address": "wrap"},
    }
    return orm, report


def encode(orm: np.ndarray) -> bytes:
    """Serialise exactly as write() does, so --check compares like with like."""
    import io

    buf = io.BytesIO()
    Image.fromarray(orm, "RGB").save(buf, "PNG", optimize=True)
    return buf.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="verify on-disk ORMs match a fresh pack; write nothing")
    args = ap.parse_args()

    manifest = json.loads(MANIFEST.read_text())["materials"]
    QA.mkdir(parents=True, exist_ok=True)
    results: dict[str, Any] = {}
    failed: list[str] = []

    for name in ORM_SETS:
        if name not in manifest:
            raise KeyError(f"{name} has no entry in {MANIFEST.name}")
        orm, report = pack(name, int(manifest[name].get("metallic", 0)))
        blob = encode(orm)
        report["sha256"] = hashlib.sha256(blob).hexdigest()
        out = PBR / f"{name}_orm.png"

        if args.check:
            if not out.exists():
                report["check"] = "MISSING"
                failed.append(f"{out.name} does not exist")
            elif hashlib.sha256(out.read_bytes()).hexdigest() != report["sha256"]:
                report["check"] = "MISMATCH"
                failed.append(f"{out.name} differs from a fresh pack")
            else:
                report["check"] = "PASS"
        else:
            out.write_bytes(blob)
            report["check"] = "WRITTEN"

        results[name] = report
        print(f"{report['check']:8} {out.name}  {report['sha256'][:16]}  "
              f"AO {report['stats']['R']['mean']:.1f} / "
              f"rough {report['stats']['G']['mean']:.1f} / "
              f"metal {report['stats']['B']['mean']:.1f}")

    (QA / "orm_packing_report.json").write_text(
        json.dumps({"convention": "R=AO, G=Roughness, B=Metallic",
                    "materials": results}, indent=2) + "\n")

    if failed:
        for f in failed:
            print(f"FAIL: {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
