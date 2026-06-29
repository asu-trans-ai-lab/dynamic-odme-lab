"""Remove generated outputs / caches (keeps inputs and code)."""
from __future__ import annotations
import os, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for dirpath, dirs, files in os.walk(ROOT):
    for d in list(dirs):
        if d in ("__pycache__", ".pytest_cache") or d.endswith(".egg-info"):
            shutil.rmtree(os.path.join(dirpath, d), ignore_errors=True)
    for f in files:
        if f.endswith((".pyc", ".log")) or f.endswith((".npz", ".pkl")):
            try:
                os.remove(os.path.join(dirpath, f))
            except OSError:
                pass
print("clean_outputs: done")
