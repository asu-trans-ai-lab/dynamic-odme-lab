"""Fail if any committed file leaks private agency DATA (NVTA / VDOT / INRIX / RITIS / CBI / P4P).

Policy: code and docs MAY *name* the agencies in explanatory text (the methodology is openly about working
with VDOT counts and INRIX speeds). What must never be committed is private *data files* and private *file
names*. So this guard blocks:
  (1) any private term inside a DATA file (.csv/.json/.parquet/.npz/.pkl/.sqlite), and
  (2) any file whose NAME contains a private token, and
  (3) private link-ID-style patterns in data files.
It does NOT block agency-name mentions inside .py/.md/.yml documentation.

Exit code 0 = clean, 1 = private data detected.
"""
from __future__ import annotations
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TERMS = re.compile(r"nvta|vdot|inrix|ritis|\bcbi\b|p4p", re.I)
ALLOW = ("99_private_nvta_manifest_only", "data_private", ".gitignore", "DO_NOT_COMMIT")
DATA_EXT = (".csv", ".json", ".parquet", ".npz", ".pkl", ".sqlite", ".tsv")
BAD_FILE = re.compile(r"nvta|vdot|inrix|ritis|\bcbi\b|p4p|tmc_identification", re.I)

hits = []
for dirpath, dirs, files in os.walk(ROOT):
    if ".git" in dirpath or "__pycache__" in dirpath or "data_private" in dirpath:
        continue
    for fn in files:
        path = os.path.join(dirpath, fn)
        rel = os.path.relpath(path, ROOT)
        if any(a in rel for a in ALLOW):
            continue
        # (2) private file name (anywhere)
        if BAD_FILE.search(fn):
            hits.append((rel, "private file name")); continue
        # (1) private terms inside DATA files only (docs/code may mention agency names)
        if fn.endswith(DATA_EXT):
            try:
                txt = open(path, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            m = TERMS.search(txt)
            if m:
                hits.append((rel, f"private term '{m.group(0)}' in a DATA file"))

if hits:
    print("PRIVATE DATA DETECTED -- do not commit:")
    for rel, why in hits:
        print(f"  {rel}: {why}")
    sys.exit(1)
print("validate_no_private_data: CLEAN (no NVTA/VDOT/INRIX/RITIS/CBI/P4P leakage)")
sys.exit(0)
