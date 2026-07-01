"""Observability gate on a small SYNTHETIC network (public, self-contained).

Only OD pairs whose paths cross a sensor (observed) link may be adjusted; OD pairs that cross NO sensor are
unobservable and are frozen at theta = 1 (kept at seed). This is the dynamic-odme-lab twin of the
DTALite/TAPLite ODME sensor-point gate.

Run:  python examples/run_observability_gate.py
"""
from __future__ import annotations
import os, sys
import numpy as np
import scipy.sparse as sp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from odme.bounded import observability_mask, bounded_lowrank_odme   # noqa: E402


def synthetic_case(seed=0):
    rng = np.random.default_rng(seed)
    n_zones, L = 16, 100
    ods = [(i, j) for i in range(n_zones) for j in range(n_zones) if i != j]
    oi = np.array([o for o, _ in ods]); di = np.array([d for _, d in ods]); n_od = len(ods)
    rows, cols, od_of, share = [], [], [], []
    for k in range(n_od):
        for _ in range(2):
            p = len(od_of); od_of.append(k); share.append(0.5)
            for a in rng.choice(L, size=4, replace=False):
                rows.append(p); cols.append(a)
    PL = sp.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(od_of), L))
    PLt = PL.T.tocsr(); od_of = np.array(od_of); share = np.array(share)
    mv = lambda d: PLt @ (share * d[od_of])
    def rmv(r):
        g = np.zeros(n_od); np.add.at(g, od_of, share * (PL @ r)); return g
    d_true = rng.uniform(5, 40, n_od); d0 = d_true * rng.uniform(0.9, 1.1, n_od)
    # sensors on ~25% of links (a partial screenline system)
    sensor_cols = sorted(rng.choice(L, size=L // 4, replace=False).tolist())
    S = sp.csr_matrix((np.ones(len(sensor_cols)), (range(len(sensor_cols)), sensor_cols)),
                      shape=(len(sensor_cols), L))
    y = S @ mv(d_true)
    return PL, od_of, mv, rmv, d0, oi, di, S, y, sensor_cols, n_od


def main():
    PL, od_of, mv, rmv, d0, oi, di, S, y, sensor_cols, n_od = synthetic_case()

    # 1) observability: per-OD distinct sensor links crossed + adjustable mask
    num_sensor, adjustable = observability_mask(PL, od_of, sensor_cols, n_od)
    n_adj = int(adjustable.sum()); n_fix = int((~adjustable).sum())
    print(f"OD pairs: {n_od} | sensor links: {len(sensor_cols)}")
    print(f"  adjustable (cross >=1 sensor): {n_adj} ({100*n_adj/n_od:.0f}%), "
          f"demand {100*d0[adjustable].sum()/d0.sum():.0f}%")
    print(f"  UNOBSERVABLE (cross 0 sensors -> theta=1): {n_fix} ({100*n_fix/n_od:.0f}%), "
          f"demand {100*d0[~adjustable].sum()/d0.sum():.0f}%")
    print(f"  sensor points passed (adjustable): min={num_sensor[adjustable].min()} "
          f"max={num_sensor[adjustable].max()}")

    # 2) bounded ODME WITH the gate -> unobservable OD must stay at seed
    res = bounded_lowrank_odme(mv, rmv, d0, oi, di, S, y, bound=0.10, rank=2, observable=adjustable)
    frozen_ok = np.allclose(res.theta[~adjustable], 1.0)
    moved_fixed = int(np.sum(np.abs(res.d[~adjustable] - d0[~adjustable]) > 1e-9))
    print(f"\nWith the gate: unobservable OD frozen at theta=1? {frozen_ok}  "
          f"(unobservable OD that moved: {moved_fixed}, must be 0)")
    print("Only observable OD entered the adjustment stage; total regional trips stay anchored to the base OD.")


if __name__ == "__main__":
    main()
