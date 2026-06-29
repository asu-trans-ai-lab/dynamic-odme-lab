"""Departure-time profile utilities: normalization, empirical envelope, and shape diagnostics."""
from __future__ import annotations
import numpy as np


def normalize(a) -> np.ndarray:
    """Non-negative profile normalized to sum 1."""
    a = np.maximum(np.asarray(a, float), 0.0)
    s = a.sum()
    return a / s if s > 0 else a


def envelope(profiles) -> tuple[np.ndarray, np.ndarray]:
    """Per-bin (min, max) empirical envelope across a list of normalized profiles."""
    M = np.vstack([normalize(p) for p in profiles])
    return M.min(0), M.max(0)


def in_envelope(profile, lo, hi) -> float:
    """Share of bins of `profile` inside [lo, hi]."""
    p = np.asarray(profile, float)
    return float(((p >= np.asarray(lo) - 1e-9) & (p <= np.asarray(hi) + 1e-9)).mean())


def profile_diagnostics(profile, h0: float = 0.0, dt: float = 0.25) -> dict:
    """Peak time, peak/avg, total variation (S1), curvature (S2), and early-shoulder ratio."""
    p = np.asarray(profile, float)
    T = len(p)
    pk = int(p.argmax())
    s1 = float(np.sum(np.abs(np.diff(p)))) if T > 1 else 0.0
    s2 = float(np.sum(np.diff(p, 2) ** 2)) if T > 2 else 0.0
    r_early = float(p[0] / p[min(4, T - 1)]) if p[min(4, T - 1)] > 0 else float("nan")
    return dict(peak_h=h0 + pk * dt, peak_to_avg=float(p.max() / p.mean()),
                S1_total_variation=s1, S2_curvature=s2, early_ratio=r_early)
