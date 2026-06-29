import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np, scipy.sparse as sp
from odme.dynamic import recover_phi, grid_columns, normalize


def test_recovers_peaked_profile_and_conserves():
    n_od, T = 4, 16
    X = np.array([100.0, 80, 120, 60]); groups = grid_columns(n_od, T)
    truth = normalize(np.exp(-0.5 * ((np.arange(T) - 9) / 2.5) ** 2))
    rows, cols, dat = [], [], []
    for od, g in enumerate(groups):
        for t, ci in enumerate(g):
            rows.append(t); cols.append(ci); dat.append(1.0)
    G = sp.csr_matrix((dat, (rows, cols)), shape=(T, n_od * T))
    y = G @ np.concatenate([X[od] * truth for od in range(n_od)])
    res = recover_phi(G, y, groups, X, T, lam_curv=1.0, iters=200)
    phi = res["phi_agg"]
    assert abs(phi.sum() - 1.0) < 1e-6                       # conservation
    assert (phi >= -1e-9).all()                              # nonnegativity
    assert abs(int(phi.argmax()) - 9) <= 1                   # peak recovered


if __name__ == "__main__":
    test_recovers_peaked_profile_and_conserves(); print("test_phi_recovery: OK")
