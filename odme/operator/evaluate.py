"""Evaluate compression by ASSIGNMENT-VISIBLE calibration metrics, not matrix reconstruction.

E_link, E_count, E_VMT, E_VHT, E_screenline/corridor — the quantities the ARC Section-7 report
validates. The whole point: a compressed operator is acceptable iff these stay within the
calibration gates, regardless of how much of the raw operator was discarded.
"""
from __future__ import annotations

import numpy as np


def rel_l1(a, b):
    den = np.abs(a).sum()
    return float(np.abs(a - b).sum() / den) if den > 0 else float("nan")


def compression_error(exact, comp, M_count=None, M_screen=None, length=None, fftt=None):
    """exact, comp: AssignmentOperator. Compare forward responses at the base demand d0."""
    d0 = exact.d0
    x = exact.matvec(d0)
    xc = comp.matvec(d0)
    out = {
        "paths_ratio": comp.P / exact.P,
        "nnz_ratio": comp.nnz / exact.nnz,
        "E_link": 100 * rel_l1(x, xc),
        "E_VMT": 100 * abs(x @ exact.length - xc @ exact.length) / max(x @ exact.length, 1),
        "E_VHT": 100 * abs(x @ exact.fftt - xc @ exact.fftt) / max(x @ exact.fftt, 1),
    }
    if M_count is not None:
        out["E_count"] = 100 * rel_l1(M_count @ x, M_count @ xc)
    if M_screen is not None:
        out["E_screenline"] = 100 * rel_l1(M_screen @ x, M_screen @ xc)
    return out
