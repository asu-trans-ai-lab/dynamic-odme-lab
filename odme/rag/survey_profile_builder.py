"""Build behavioral departure profiles by purpose from a generic survey CSV.

Expected schema (public, agency-agnostic):  profile_id, purpose, time_bin, profile_share
Returns {purpose: np.array(profile_share over time bins)}.  No private data is bundled; point this at a
local survey file (e.g. CHTS/NHTS-derived) under data_private/ when authorized.
"""
from __future__ import annotations
import csv
from collections import defaultdict
import numpy as np
from ..dynamic.profile_library import normalize


def load_survey_profiles(csv_path: str) -> dict:
    by = defaultdict(dict)
    for r in csv.DictReader(open(csv_path, encoding="utf-8-sig")):
        by[r["purpose"]][int(float(r["time_bin"]))] = float(r["profile_share"])
    out = {}
    for purp, d in by.items():
        T = max(d) + 1
        out[purp] = normalize([d.get(t, 0.0) for t in range(T)])
    return out
