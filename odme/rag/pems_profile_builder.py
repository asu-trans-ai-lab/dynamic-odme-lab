"""Build a detector-based PASSAGE-time profile from generic 5-min/15-min detector data.

Expected schema:  sensor_id, time_min, flow_vph   (agency-agnostic public detector export).
NOTE: this is a detector PASSAGE-time profile, NOT a trip-departure profile. Apply a travel-time shift
(phi^PeMS_{r,tau} ~ p^PeMS_{a, tau+TT}) and prefer entry-screenline detectors before using as a
departure prior.
"""
from __future__ import annotations
import csv
from collections import defaultdict
import numpy as np
from ..dynamic.profile_library import normalize


def detector_profile(csv_path: str, t_start_min: int = 0, step_min: int = 15, T: int = 96) -> np.ndarray:
    bf = defaultdict(float)
    for r in csv.DictReader(open(csv_path, encoding="utf-8-sig")):
        tm = int(float(r["time_min"]))
        b = (tm - t_start_min) // step_min
        if 0 <= b < T:
            bf[b] += float(r["flow_vph"])
    return normalize([bf.get(b, 0.0) for b in range(T)])
