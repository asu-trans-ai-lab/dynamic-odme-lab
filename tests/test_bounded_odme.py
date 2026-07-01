"""Bounded low-rank ODME: the +-bound must be respected and the fit must not get worse than V0."""
import os, sys
import numpy as np
import scipy.sparse as sp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from odme.bounded import bounded_lowrank_odme, three_version_comparison  # noqa: E402


def _case(seed=1):
    rng = np.random.default_rng(seed)
    n_zones, L = 15, 90
    ods = [(i, j) for i in range(n_zones) for j in range(n_zones) if i != j]
    oi = np.array([o for o, _ in ods]); di = np.array([d for _, d in ods]); n_od = len(ods)
    rows, cols, od_of, share = [], [], [], []
    for k in range(n_od):
        for _ in range(2):
            p = len(od_of); od_of.append(k); share.append(0.5)
            for a in rng.choice(L, size=3, replace=False):
                rows.append(p); cols.append(a)
    PL = sp.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(od_of), L))
    PLt = PL.T.tocsr(); od_of = np.array(od_of); share = np.array(share)
    mv = lambda d: PLt @ (share * d[od_of])
    def rmv(r):
        g = np.zeros(n_od); np.add.at(g, od_of, share * (PL @ r)); return g
    d_true = rng.uniform(5, 40, n_od)
    grp = rng.integers(0, 10, L); S = sp.csr_matrix((np.ones(L), (grp, np.arange(L))), shape=(10, L))
    y = S @ mv(d_true); d0 = d_true * rng.uniform(0.9, 1.1, n_od)
    return mv, rmv, d0, oi, di, S, y


def test_hard_bound_respected():
    mv, rmv, d0, oi, di, S, y = _case()
    res = bounded_lowrank_odme(mv, rmv, d0, oi, di, S, y, bound=0.10, rank=2)
    theta = res.theta
    assert theta.min() >= 0.90 - 1e-6 and theta.max() <= 1.10 + 1e-6
    assert res.diagnostics["pct_outside"] == 0.0
    # origin production and destination attraction stay within +-10%
    assert res.diagnostics["origin_pct_outside"] == 0.0
    assert res.diagnostics["dest_pct_outside"] == 0.0


def test_bounded_not_worse_than_v0_and_lowrank():
    mv, rmv, d0, oi, di, S, y = _case(seed=3)
    rows, v2 = three_version_comparison(mv, rmv, d0, oi, di, S, y, bound=0.10, rank=2)
    v0, v1, v2r = rows
    # bounded ODME should not degrade the count fit relative to no-ODME
    assert v2r["R2"] >= v0["R2"] - 1e-6
    # unconstrained distorts more origins/destinations than bounded
    assert v1["origin_pct_outside"] >= v2r["origin_pct_outside"]
    # adjustment is low-rank / interpretable
    assert v2r["od_explained_pct"] >= 50.0


def test_tighter_bound_changes_less():
    mv, rmv, d0, oi, di, S, y = _case(seed=5)
    r05 = bounded_lowrank_odme(mv, rmv, d0, oi, di, S, y, bound=0.05, rank=2)
    r20 = bounded_lowrank_odme(mv, rmv, d0, oi, di, S, y, bound=0.20, rank=2)
    # a tighter bound clamps theta into a strictly tighter band
    assert r05.theta.max() <= 1.05 + 1e-6 and r05.theta.min() >= 0.95 - 1e-6
    assert r20.theta.max() <= 1.20 + 1e-6 and r20.theta.min() >= 0.80 - 1e-6
    dev05 = float(np.abs(r05.theta - 1).max()); dev20 = float(np.abs(r20.theta - 1).max())
    assert dev05 <= dev20 + 1e-6
