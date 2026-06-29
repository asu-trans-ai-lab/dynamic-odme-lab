"""Assemble a per-link queue posterior from arrival demand and a (calibrated) discharge rate.

Forward queue:  lambda(t) (arrival demand)  +  mu (discharge, e.g. mu_of_dc)  ->  Q(t), s(t), P.
Returns the reviewer-schema posterior rows for one link.
"""
from __future__ import annotations
import numpy as np
from .fluid_queue import point_queue


def link_queue_posterior(link_id, lam, mu: float, dt: float, t0_obs=None, t3_obs=None,
                         P_obs=None, h0: float = 0.0):
    """One link's queue posterior over time. lam: arrival demand (vph) per bin; mu: discharge (vph)."""
    lam = np.asarray(lam, float)
    q = point_queue(lam, mu, dt)
    T = len(lam)
    rows = []
    for t in range(T):
        rows.append(dict(link_id=link_id, time_bin=t, clock_h=h0 + t * dt,
                         lambda_inflow=float(lam[t]), mu_discharge=mu,
                         outflow_s=float(q["s"][t]), queue_Q=float(q["Q"][t]),
                         queue_flag=int(q["Q"][t] > 1e-9),
                         P_model=q["P"], P_obs=(float(P_obs) if P_obs is not None else None)))
    summary = dict(link_id=link_id, P_model=q["P"], t0_model=q["t0"], t2_model=q["t2"],
                   t3_model=q["t3"], P_obs=P_obs, t0_obs=t0_obs, t3_obs=t3_obs,
                   P_error=(q["P"] - P_obs) if P_obs is not None else None)
    return rows, summary
