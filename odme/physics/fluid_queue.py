"""Deterministic point (fluid) queue -- the building block of the queue diagnostics.

    s_t       = min( mu, lambda_t + Q_t/dt )                 (discharge / outflow, capped at mu)
    Q_{t+dt}  = max( 0, Q_t + dt*(lambda_t - s_t) )          (non-negative queue)

All quantities are flows (veh/h) and queue in vehicles; dt in hours.
"""
from __future__ import annotations
import numpy as np


def point_queue(lam, mu: float, dt: float) -> dict:
    """Run a point queue with arrival rate lam(t), discharge capacity mu, step dt.

    Returns dict with s (outflow per bin), Q (queue per bin), P (duration, h),
    and onset/trough/recovery bin indices t0/t2/t3 (-1 if no queue forms).
    """
    lam = np.asarray(lam, float)
    T = len(lam)
    Q = np.zeros(T + 1)
    s = np.zeros(T)
    for t in range(T):
        s[t] = min(mu, lam[t] + Q[t] / dt)
        Q[t + 1] = max(0.0, Q[t] + dt * (lam[t] - s[t]))
    Qb = Q[:T]
    busy = Qb > 1e-9
    P = float(dt * busy.sum())
    t0 = int(np.argmax(busy)) if busy.any() else -1
    t3 = int(T - np.argmax(busy[::-1])) if busy.any() else -1
    t2 = int(np.argmax(Qb)) if Qb.max() > 0 else -1
    return dict(s=s, Q=Qb, P=P, t0=t0, t2=t2, t3=t3, queue_forms=bool(busy.any()))
