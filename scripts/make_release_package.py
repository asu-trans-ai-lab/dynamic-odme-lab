"""Validate privacy, run the reproducibility check, then report release readiness.

Does NOT zip private data. Intended to gate the v0.1.0-reproducible-kernel release.
"""
from __future__ import annotations
import os, sys, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def step(name, args):
    r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    print(f"[{'OK' if r.returncode == 0 else 'FAIL'}] {name}")
    if r.returncode != 0:
        print(r.stdout[-600:], r.stderr[-600:])
    return r.returncode == 0


ok = step("privacy guard", [sys.executable, "scripts/validate_no_private_data.py"])
ok = step("reproducibility", [sys.executable, "examples/run_full_reproducibility_check.py"]) and ok
print("\nRELEASE READINESS (v0.1.0-reproducible-kernel):", "READY" if ok else "NOT READY")
sys.exit(0 if ok else 1)
