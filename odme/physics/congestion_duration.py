"""Congestion-duration: observed (speed-threshold) vs model (queue), and the hard gate.

The gate must PASS before the queue layer may be called "physics on" rather than diagnostic.
"""
from __future__ import annotations
import numpy as np


def observed_duration(speed, cutoff: float, dt: float) -> dict:
    """Observed onset/trough/recovery/duration from speed below a cutoff (e.g. speed-at-capacity)."""
    speed = np.asarray(speed, float)
    T = len(speed)
    cong = [t for t in range(T) if speed[t] < cutoff]
    if not cong:
        return dict(t0=-1, t2=-1, t3=-1, P=0.0)
    t0, t3 = min(cong), max(cong)
    t2 = int(np.argmin(speed))
    return dict(t0=t0, t2=t2, t3=t3, P=(t3 + 1 - t0) * dt)


def duration_gate(P_model, P_obs, rmse_pass: float = 0.5) -> dict:
    """E_P, RMSE_P and a PASS/FAIL verdict over a set of links.

    Passes only if a queue actually forms AND the duration RMSE is below rmse_pass (hours).
    """
    P_model = np.asarray(P_model, float)
    P_obs = np.asarray(P_obs, float)
    E_P = float(np.nanmean(np.abs(P_model - P_obs)))
    RMSE_P = float(np.sqrt(np.nanmean((P_model - P_obs) ** 2)))
    forms = bool(np.nanmax(P_model) > 0)
    return dict(E_P=E_P, RMSE_P=RMSE_P, queue_forms=forms,
                verdict="PASS" if (forms and RMSE_P < rmse_pass) else "FAIL")
