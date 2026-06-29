"""Matrix-free operator + compression benchmark.

  python -m odme.operator.benchmark            # Chicago Sketch (118k paths, multi-path)
  python -m odme.operator.benchmark <cols.csv> <link.csv>

Experiment 1 — exact sparse baseline: nnz, memory, matvec/rmatvec runtime (proves it scales).
Experiment 2 — active path pruning: compression ratio vs calibration-visible error (E_link, E_VMT, E_VHT, E_count).
"""
from __future__ import annotations

import sys
import time

import numpy as np
import scipy.sparse as sp

from .assignment_operator import build_operator
from .compress import prune_paths
from .evaluate import compression_error

CHIC = ("compressed-optimization_0131_2026/compressed-optimization/data/10_Chicago_Sketch/columns.csv",
        "compressed-optimization_0131_2026/compressed-optimization/data/10_Chicago_Sketch/link.csv")


def count_matrix(op, frac=0.5, seed=1):
    """A sensor/count aggregation M (rows=sensors, cols=links) on a fraction of loaded links."""
    x = op.matvec(op.d0)
    cand = np.where(x > 50)[0]
    rng = np.random.default_rng(seed)
    sens = rng.choice(cand, size=int(frac * len(cand)), replace=False)
    M = sp.csr_matrix((np.ones(len(sens)), (range(len(sens)), sens)), shape=(len(sens), op.L))
    return M


def main(argv):
    cols, link = (argv[0], argv[1]) if len(argv) >= 2 else CHIC
    print(f"building operator from\n  {cols}\n  {link}")
    t0 = time.time()
    op = build_operator(cols, link)
    print(f"\n=== Experiment 1: exact sparse operator (A = Δ R, never dense) ===")
    print(f" OD pairs={op.n_od}  paths={op.P}  links={op.L}  avg path len={op.nnz/op.P:.1f}")
    print(f" nnz(Δ)={op.nnz:,}   operator memory={op.memory_mb():.1f} MB   build={time.time()-t0:.1f}s")
    dense_gb = op.L * op.n_od * 8 / 1e9
    print(f" (dense |L|×|OD| would be {dense_gb:,.0f} GB — never materialized)")
    d0 = op.d0
    t = time.time(); [op.matvec(d0) for _ in range(5)]; tm = (time.time()-t)/5
    r = op.matvec(d0)
    t = time.time(); [op.rmatvec(r) for _ in range(5)]; tr = (time.time()-t)/5
    agg = op.aggregate(r)
    print(f" matvec={tm*1000:.1f} ms   rmatvec={tr*1000:.1f} ms   VMT={agg['VMT']:,.0f}  VHT={agg['VHT']:,.0f}")

    print(f"\n=== Experiment 2: active path pruning vs calibration-visible error ===")
    M = count_matrix(op)
    print(f" (count gate on {M.shape[0]} sensor links)")
    print(f" {'scheme':>16} {'paths%':>7} {'E_link%':>8} {'E_VMT%':>7} {'E_VHT%':>7} {'E_count%':>9}")
    schemes = [("top-1", dict(top_k=1)), ("top-2", dict(top_k=2)), ("top-3", dict(top_k=3)),
               ("share>=0.01", dict(share_min=0.01)), ("cum-95%", dict(cum_flow=0.95)),
               ("cum-99%", dict(cum_flow=0.99))]
    for name, kw in schemes:
        c = prune_paths(op, **kw)
        e = compression_error(op, c, M_count=M)
        print(f" {name:>16} {100*e['paths_ratio']:>6.0f}% {e['E_link']:>7.2f}% {e['E_VMT']:>6.2f}% "
              f"{e['E_VHT']:>6.2f}% {e.get('E_count', float('nan')):>8.2f}%")
    print("\n-> compression is acceptable iff E_count/E_VMT/E_VHT stay inside the calibration gates,")
    print("   NOT iff the matrix reconstruction error is small.")


if __name__ == "__main__":
    main(sys.argv[1:])
