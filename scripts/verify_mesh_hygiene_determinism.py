#!/usr/bin/env python3
"""Run every affected generator/verifier twice and require byte-identical output."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "qa" / "mesh_hygiene" / "determinism_report.json"
COMMANDS = [
    ["python3", "scripts/generate_rootstead_entrance_bulkhead.py"],
    ["python3", "scripts/generate_rootstead_entrance_bulkhead_proto.py"],
    ["python3", "scripts/generate_rootstead_entry_vestibule.py"],
    ["python3", "scripts/generate_rootstead_west_endwall_entry.py"],
    ["python3", "scripts/generate_spire_landmark.py"],
    ["python3", "scripts/verify_rootstead_entrance_bulkhead.py"],
    ["python3", "scripts/verify_rootstead_entrance_bulkhead_proto.py"],
    ["python3", "scripts/verify_rootstead_entry_vestibule.py"],
    ["python3", "scripts/verify_rootstead_west_endwall_entry.py"],
    ["python3", "scripts/verify_spire_landmark.py"],
    ["python3", "scripts/audit_source_mesh_hygiene.py", "--baseline-ref", "origin/main"],
]


def run_all() -> None:
    for command in COMMANDS:
        process = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        if process.returncode:
            raise RuntimeError(
                f"failed: {' '.join(command)}\n{process.stdout}\n{process.stderr}"
            )


def changed_paths() -> list[str]:
    raw = subprocess.check_output(["git", "status", "--porcelain", "-z"], cwd=ROOT)
    entries = raw.split(b"\0")
    paths: list[str] = []
    index = 0
    while index < len(entries) and entries[index]:
        item = entries[index].decode()
        status = item[:2]
        path = item[3:]
        if status[0] in "RC":
            index += 1
            path = entries[index].decode()
        if ROOT / path != REPORT:
            paths.append(path)
        index += 1
    return sorted(set(paths))


def hashes(paths: list[str]) -> dict[str, str]:
    return {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        for path in paths
        if (ROOT / path).is_file()
    }


def main() -> int:
    run_all()
    paths = changed_paths()
    first = hashes(paths)
    run_all()
    second = hashes(paths)
    mismatches = {
        path: {"first": first.get(path), "second": second.get(path)}
        for path in sorted(set(first) | set(second))
        if first.get(path) != second.get(path)
    }
    report = {
        "all_pass": not mismatches,
        "runs": 2,
        "commands": [" ".join(command) for command in COMMANDS],
        "files_checked": len(second),
        "mismatches": mismatches,
        "sha256": second,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "all_pass": report["all_pass"],
        "files_checked": report["files_checked"],
        "mismatches": list(mismatches),
        "report": str(REPORT.relative_to(ROOT)),
    }, indent=2))
    return 0 if report["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
