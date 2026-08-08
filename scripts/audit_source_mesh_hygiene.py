#!/usr/bin/env python3
"""Hard-gate every delivered OBJ against duplicate and degenerate faces.

Optionally compares the working tree with a Git baseline so topology reductions
are explicit in the review artifact rather than inferred from a binary-sized
diff.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from mesh_hygiene import audit_obj, parse_obj

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "SourceMesh"
DEFAULT_REPORT = ROOT / "qa" / "mesh_hygiene" / "source_mesh_hygiene_report.json"


def baseline_audit(ref: str, relative_path: str) -> dict[str, int | bool] | None:
    proc = subprocess.run(
        ["git", "show", f"{ref}:{relative_path}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / Path(relative_path).name
        path.write_text(proc.stdout, encoding="utf-8")
        return audit_obj(parse_obj(path))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-ref", default="origin/main")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    baseline_sha = subprocess.check_output(
        ["git", "rev-parse", args.baseline_ref], cwd=ROOT, text=True
    ).strip()
    assets: dict[str, object] = {}
    for path in sorted(SOURCE.rglob("*.obj")):
        relative = str(path.relative_to(ROOT))
        before = baseline_audit(args.baseline_ref, relative)
        after = audit_obj(parse_obj(path))
        assets[relative] = {
            "before": before,
            "after": after,
            "delta": None if before is None else {
                "triangles": int(after["triangles"]) - int(before["triangles"]),
                "duplicate_face_groups": (
                    int(after["duplicate_face_groups"])
                    - int(before["duplicate_face_groups"])
                ),
                "stacked_face_pairs_1cm": (
                    int(after["stacked_face_pairs_1cm"])
                    - int(before["stacked_face_pairs_1cm"])
                ),
                "stacked_faces_1cm": (
                    int(after["stacked_faces_1cm"])
                    - int(before["stacked_faces_1cm"])
                ),
                "degenerate_faces": (
                    int(after["degenerate_faces"])
                    - int(before["degenerate_faces"])
                ),
            },
        }

    failures = [
        path for path, record in assets.items()
        if not record["after"]["pass"]  # type: ignore[index]
    ]
    report = {
        "all_pass": not failures,
        "hard_gate": {
            "duplicate_face_groups": 0,
            "stacked_face_pairs_1cm": 0,
            "degenerate_faces": 0,
            "strict_manifold": "advisory; not a render-mesh acceptance gate",
        },
        "baseline_ref": args.baseline_ref,
        "baseline_sha": baseline_sha,
        "asset_count": len(assets),
        "failures": failures,
        "assets": assets,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "all_pass": report["all_pass"],
        "asset_count": len(assets),
        "failures": failures,
        "report": str(args.report.relative_to(ROOT)),
    }, indent=2))
    return 0 if report["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
