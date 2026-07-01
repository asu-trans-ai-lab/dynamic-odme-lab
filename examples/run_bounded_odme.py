"""Bounded low-rank ODME on a small SYNTHETIC network (public, self-contained).

Shows ODME as a small, bounded, interpretable refinement:
  V0  no ODME (baseline loading fit)
  V1  unconstrained low-rank ODME (fits counts but distorts origins/destinations)
  V2  bounded +-10% low-rank ODME (preferred: every OD pair / origin / destination within +-10%)

Run:  python examples/run_bounded_odme.py
"""
from __future__ import annotations
import os, sys
import numpy as np
import scipy.sparse as sp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from odme.bounded import three_version_comparison   # noqa: E402


def synthetic_case(seed=0):
    rng = np.random.default_rng(seed)
    n_zones, L = 20, 120
    ods = [(i, j) for i in range(n_zones) for j in range(n_zones) if i != j]
    oi = np.array([o for o, _ in ods]); di = np.array([d for _, d in ods]); n_od = len(ods)
    # 2 paths per OD, each crossing ~4 random links
    rows, cols, od_of, share = [], [], [], []
    for k in range(n_od):
        for _ in range(2):
            p = len(od_of); od_of.append(k); share.append(0.5)
            for a in rng.choice(L, size=4, replace=False):
                rows.append(p); cols.append(a)
    PL = sp.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(od_of), L))
    PLt = PL.T.tocsr(); od_of = np.array(od_of); share = np.array(share)

    def matvec(d):  return PLt @ (share * d[od_of])
    def rmatvec(r):
        g = np.zeros(n_od); np.add.at(g, od_of, share * (PL @ r)); return g

    d_true = rng.uniform(5, 50, n_od)                     # ground-truth OD
    # count-incidence: group links into 12 "screenlines"
    grp = rng.integers(0, 12, L)
    S = sp.csr_matrix((np.ones(L), (grp, np.arange(L))), shape=(12, L))
    y = S @ matvec(d_true)                                 # observed screenline counts (from truth)
    # base OD carries a STRUCTURED origin bias (some origins 0.75x, some 1.3x) + small noise -> the
    # correction some OD pairs "want" exceeds +-10%, so V1 goes out of band and V2 must clip.
    o_bias = rng.uniform(0.75, 1.30, n_zones)
    d0 = d_true * o_bias[oi] * rng.uniform(0.95, 1.05, n_od)
    return matvec, rmatvec, d0, oi, di, S, y


def main():
    matvec, rmatvec, d0, oi, di, S, y = synthetic_case()
    rows, v2 = three_version_comparison(matvec, rmatvec, d0, oi, di, S, y, bound=0.10, rank=2)
    print(f"{'version':18s} {'R2':>7} {'WMAPE':>7} {'med_th':>8} {'%OD>10':>8} {'%orig>10':>9} "
          f"{'%dest>10':>9} {'d_tot%':>8}")
    for r in rows:
        print(f"{r['version']:18s} {r['R2']:7.3f} {r['WMAPE']:7.3f} {r['median_theta']:8.3f} "
              f"{r['pct_outside']:8.1f} {r['origin_pct_outside']:9.1f} {r['dest_pct_outside']:9.1f} "
              f"{r['total_change_pct']:8.1f}")
    print(f"\nV2 bounded: O+D structure explains {rows[2].get('od_explained_pct', float('nan')):.0f}% of "
          f"log(theta); every OD pair/origin/destination within +-10%.")
    print("Interpretation: unconstrained ODME (V1) fits counts but pushes origins/destinations beyond +-10%;")
    print("bounded ODME (V2) keeps the adjustment small, low-rank, and interpretable.")


if __name__ == "__main__":
    main()
