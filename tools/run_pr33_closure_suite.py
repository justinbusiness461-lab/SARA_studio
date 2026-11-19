#!/usr/bin/env python3
"""Fail-closed PR #33 source/test gate. No production certification."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

REQUIRED = {
    "SARA_studio": [
        "tools/studio_server.py", "tools/m045_native_owner.py",
        "tools/m045_bs1770_reference.py", "tools/m045_dsp_repairs.py",
        "tools/m045_http_probe.py", "tests/test_m045_bs1770_reference.py",
        "tests/test_project_authority.py", "tests/test_m044_r3_durability.py",
    ],
    "dj_rezrxtion": [
        "tools/pf_cinema_021l_hardened.py", "tools/streaming_frame_decoder.py",
        "tools/semantic_registry_loader.py", "tools/seam_continuity_checker.py",
        "tools/djrx_verify.py", "tests/test_pf_cinema_021l_hardened.py",
    ],
}
TESTS = {
    "SARA_studio": [
        "tests/test_project_authority.py", "tests/test_m044_r3_durability.py",
        "tools/m045_http_probe.py", "tests/test_m045_bs1770_reference.py",
    ],
    "dj_rezrxtion": ["tests/test_pf_cinema_021l_hardened.py"],
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for data in iter(lambda: f.read(1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def execute(root: Path, timeout: int) -> dict:
    result = {"gate": "PR33_CLOSURE", "stage": "SOURCE_INSPECTED",
              "files": {}, "missing": [], "tests": {},
              "production_certified": False, "creative_approved": False,
              "all_tests_passed": False}
    for repo, files in REQUIRED.items():
        for rel in files:
            name = f"{repo}/{rel}"
            path = root / name
            if path.is_file():
                result["files"][name] = sha(path)
            else:
                result["missing"].append(name)
    if result["missing"]:
        result["stage"] = "BLOCKED_SOURCE_MISSING"
        return result
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        (str(root / "SARA_studio"), str(root / "dj_rezrxtion")))
    for repo, test_files in TESTS.items():
        for rel in test_files:
            key = f"{repo}/{rel}"
            try:
                p = subprocess.run(
                    [sys.executable, str(root / key)],
                    cwd=root / repo, env=env, capture_output=True,
                    text=True, timeout=timeout, check=False)
                combined = p.stdout + "\n" + p.stderr
                skipped = "skipped=" in combined.lower() or "skipped " in combined.lower()
                ok = p.returncode == 0 and not skipped and "ran " in combined.lower()
                result["tests"][key] = {
                    "status": "PASS" if ok else "FAIL_OR_SKIPPED",
                    "exit_code": p.returncode, "output_tail": combined[-2000:]}
            except subprocess.TimeoutExpired:
                result["tests"][key] = {"status": "TIMEOUT",
                                        "timeout_seconds": timeout}
    result["all_tests_passed"] = bool(result["tests"]) and all(
        t["status"] == "PASS" for t in result["tests"].values())
    result["stage"] = ("TESTED_BOUNDED" if result["all_tests_passed"]
                       else "BLOCKED_TESTS")
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path.cwd())
    ap.add_argument("--receipt", type=Path)
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args()
    if args.timeout <= 0:
        ap.error("--timeout must be positive")
    result = execute(args.root.resolve(), args.timeout)
    result["recorded_at_unix"] = time.time()
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["all_tests_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
