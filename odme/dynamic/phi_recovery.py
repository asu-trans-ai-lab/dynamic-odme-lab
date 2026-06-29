"""Departure-profile phi(t) recovery -- projected first-order solver.

Recovers the time-of-day split phi_{r,tau} (OD totals FIXED) so a time-expanded propagation operator G
reproduces observed link-time flows y. Enforces phi>=0 and sum_tau phi_{r,tau}=1 by projection, with
optional smoothness / curvature / target-profile penalties.

This is the *validated baseline solver*: projected gradient with conservation projection -- NOT BFGS.
(L-BFGS-B is reserved for bounded physical parameters; see odme.solvers.)
"""
from __future__ import annotations
import numpy as np
import scipy.sparse as sp


def grid_columns(n_od: int, T: int):
    """Column index layout: column (od, tau) -> flat index od*T + tau. Returns groups[od] = [cols...]."""
    return [[od * T + t for t in range(T)] for od in range(n_od)]


def recover_phi(G, y, groups, X, T, seed=None, lam_smooth=0.0, lam_curv=0.0,
                lam_target=0.0, target=None, iters=150) -> dict:
    """G: (n_cells x n_cols) sparse propagation; y: observed cell flows; groups: per-OD column lists;
    X: per-OD totals (len n_od); seed: length-T base profile (default flat)."""
    G = sp.csr_matrix(G)
    ncols = G.shape[1]
    sp_prof = np.full(T, 1.0 / T) if seed is None else np.asarray(seed, float)
    vol = np.zeros(ncols)
    for gi, cols in enumerate(groups):
        for t, ci in enumerate(cols):
            vol[ci] = X[gi] * sp_prof[t]
    pt = np.asarray(target, float) if target is not None else None
    for k in range(iters):
        dev = G @ vol - y
        grad = G.T @ dev
        step = 1.0 / (k + 2.0)
        ch = step * 1e-3 * grad * np.maximum(vol, 1.0)
        lim = 0.25 * np.maximum(vol, 1.0)
        vol = np.maximum(0.0, vol - np.clip(ch, -lim, lim))
        if lam_smooth or lam_curv or (lam_target and pt is not None):
            for gi, cols in enumerate(groups):
                Xg = X[gi] or 1.0
                phi = vol[cols] / Xg
                gp = np.zeros_like(phi)
                if lam_smooth:
                    d = np.zeros_like(phi); d[:-1] += phi[:-1] - phi[1:]; d[1:] += phi[1:] - phi[:-1]
                    gp += 2 * lam_smooth * d
                if lam_curv and T > 2:
                    lap = phi[:-2] - 2 * phi[1:-1] + phi[2:]; c2 = np.zeros_like(phi)
                    c2[:-2] += lap; c2[1:-1] += -2 * lap; c2[2:] += lap
                    gp += 2 * lam_curv * c2
                if lam_target and pt is not None:
                    gp += 2 * lam_target * (phi - pt)
                phi = np.maximum(0.0, phi - step * gp)
                vol[cols] = Xg * phi
        # OD-conservation projection: sum_tau vol over each OD == X
        for gi, cols in enumerate(groups):
            ssum = vol[cols].sum()
            if ssum > 1e-12:
                vol[cols] *= X[gi] / ssum
    agg = np.zeros(T)
    for cols in groups:
        agg += vol[cols]
    s = agg.sum()
    return dict(vol=vol, phi_agg=(agg / s if s > 0 else agg))
