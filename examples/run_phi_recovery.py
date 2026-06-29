"""Recover a departure profile phi(t) from synthetic link-time observations (public).

Builds a small time-expanded propagation operator G for a few OD pairs sharing a link, generates link-time
observations from a known peaked truth, then recovers phi from a flat seed and reports the fit.

Run:  python examples/run_phi_recovery.py
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import scipy.sparse as sp
from odme.dynamic import recover_phi, grid_columns, normalize
from odme.dynamic.profile_library import profile_diagnostics

rng = np.random.default_rng(0)
n_od, T = 6, 20
X = np.array([100.0, 80, 120, 60, 90, 110])          # fixed OD totals
groups = grid_columns(n_od, T)
ncols = n_od * T

# truth: a peaked departure profile shared by all OD (peak bin 12)
truth = normalize(np.exp(-0.5 * ((np.arange(T) - 12) / 3.0) ** 2))
# operator: each OD's columns map to ONE shared link, at the same time bin (1 cell per t)
rows, cols, dat = [], [], []
for od, gcols in enumerate(groups):
    for t, ci in enumerate(gcols):
        rows.append(t); cols.append(ci); dat.append(1.0)       # link 0 at time t
G = sp.csr_matrix((dat, (rows, cols)), shape=(T, ncols))
y_true = G @ np.concatenate([X[od] * truth for od in range(n_od)])

res = recover_phi(G, y_true, groups, X, T, seed=None, lam_curv=2.0, iters=200)
phi = res["phi_agg"]
r2 = 1 - np.sum((truth - phi) ** 2) / np.sum((truth - truth.mean()) ** 2)
print(f"recovered phi(t): peak bin {int(phi.argmax())} (truth 12), R^2 vs truth = {r2:.3f}")
print("diagnostics:", {k: round(v, 3) for k, v in profile_diagnostics(phi).items()})
print("conservation: sum(phi) =", round(float(phi.sum()), 6))
