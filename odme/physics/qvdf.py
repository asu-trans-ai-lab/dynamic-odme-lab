"""QVDF discharge-rate and fundamental-diagram relations.

Queueing-based Volume-Delay Function (Zhou) on top of Newell/Cheng polynomial-arrival queues:

  congestion duration   P       = f_d * (D/C)^n                 (D/C -> duration; Step 1)
  consistency                     D = P * mu
  => discharge rate     mu(D/C)  = (C / f_d) * (D/C)^(1-n)  <  C    (capacity drop; decreasing in D/C)

S3 three-parameter speed-density:  v(k) = v_f / (1 + (k/k_c)^m)^(2/m),  q = k*v.
"""
from __future__ import annotations
import numpy as np


def mu_of_dc(C: float, f_d: float, n: float, DC: float) -> float:
    """Calibrated queue discharge rate as a function of the demand/capacity ratio (< ultimate capacity C)."""
    return (C / f_d) * DC ** (1.0 - n)


def duration_from_dc(f_d: float, n: float, DC: float) -> float:
    """QVDF Step 1: congestion duration P from the D/C ratio."""
    return f_d * DC ** n


def s3_speed(k, v_f: float, k_c: float, m: float):
    """S3 speed at density k."""
    k = np.asarray(k, float)
    return v_f / (1.0 + (k / k_c) ** m) ** (2.0 / m)


def s3_invert_flow(v: float, v_f: float, k_c: float, m: float, branch: str = "free") -> float:
    """Invert speed -> density on the requested branch ('free' k<k_c, 'cong' k>k_c), return q = k*v."""
    if v >= v_f:
        return 0.0
    lo, hi = (1e-6, k_c) if branch == "free" else (k_c, 12 * k_c)
    flo = s3_speed(lo, v_f, k_c, m) - v
    fhi = s3_speed(hi, v_f, k_c, m) - v
    if flo * fhi > 0:
        return float("nan")
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        fm = s3_speed(mid, v_f, k_c, m) - v
        if flo * fm <= 0:
            hi = mid
        else:
            lo, flo = mid, fm
    k = 0.5 * (lo + hi)
    return float(k * v)


def bpr_speed(q, C: float, v_f: float, alpha: float = 0.15, beta: float = 4.0):
    """BPR volume-delay speed."""
    q = np.asarray(q, float)
    return v_f / (1.0 + alpha * (q / C) ** beta)
