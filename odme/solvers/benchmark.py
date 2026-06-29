"""Benchmark the four ODME solvers on one problem: accuracy, convergence, runtime, gates.

  python -m odme.solvers.benchmark              # Chicago static, uniform + random perturbation
  python -m odme.solvers.benchmark dynamic      # Corridor dynamic (flattened time-dependent operator)
"""
from __future__ import annotations

import sys
from collections import defaultdict

import numpy as np
import scipy.sparse as sp

from .core import Problem, SOLVERS
from ..gates.reasonableness import gate_count_quality


def _metrics(y, yh):
    y = np.asarray(y, float); yh = np.asarray(yh, float)
    m = y.mean(); sst = ((y - m) ** 2).sum()
    r2 = 1 - ((y - yh) ** 2).sum() / sst if sst > 1e-9 else float("nan")
    mask = y > 1
    mape = 100 * np.mean(np.abs(y[mask] - yh[mask]) / y[mask]) if mask.any() else float("nan")
    return r2, mape


# ---------------------------------------------------------------- build problems
def chicago_problem(pert, frac=0.50, seed=7):
    from ..examples.chicago_qvdf_sensitivity import load_chicago, base_case, vmt_vht
    net = load_chicago(); base = base_case(net)
    real = base["real"]; x_true = base["x"]
    od_of = net["od_of"]; od_keys = list(set(od_of)); kix = {k: i for i, k in enumerate(od_keys)}
    rows = [kix[od] for od in od_of]
    P = sp.csr_matrix((np.ones(len(rows)), (rows, range(len(od_of)))), shape=(len(od_keys), len(od_of)))
    d_true = np.asarray(P @ net["h_true"]).ravel()
    rng = np.random.default_rng(seed)
    cand = np.where(real & (x_true > 50))[0]
    sensors = rng.choice(cand, size=int(frac * len(cand)), replace=False)
    held = np.setdiff1d(cand, sensors)
    G = net["Delta"][sensors, :].tocsr()
    y = x_true[sensors]
    if pert == "rand":
        fac = 1 + rng.uniform(-0.10, 0.10, size=len(od_keys))
    else:
        fac = np.full(len(od_keys), 1 + pert)
    h0 = net["h_true"] * np.array([fac[kix[od]] for od in od_of])
    d_prior = d_true * fac
    prob = Problem(G=G, y=y, x0=h0, P=P, d_prior=d_prior, name=f"chicago/{pert}")
    ctx = dict(net=net, base=base, sensors=sensors, held=held, P=P, d_true=d_true,
               x_true=x_true, vmt_vht=vmt_vht)
    return prob, ctx


def dynamic_problem():
    """Dynamic case: FLATTEN the time-dependent incidence to a 2D sparse G (cells x time-columns)."""
    from ..io.timedependent import load_dynamic_case
    from ..matrix import build_A
    C = "cases/07_i405_pm"
    case, ref, _ = load_dynamic_case(C + "/network", C + "/columns_timedependent.csv",
                                     C + "/linkflow_timedependent.csv")
    A = build_A(case, source="columns")
    covered = [c for c in A.measured_cells if c in A.incidence]      # (link,t) rows
    cell_ix = {c: i for i, c in enumerate(covered)}
    n = len(case.columns)
    rows, cols = [], []
    for cell in covered:
        for (ci, prop) in A.incidence[cell]:
            rows.append(cell_ix[cell]); cols.append(ci)
    G = sp.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(covered), n))  # FLATTENED
    h_true = np.array([c.volume for c in case.columns])
    y = np.array([A.measured_cells[c].obs_volume for c in covered])
    rng = np.random.default_rng(7)
    h0 = h_true * rng.uniform(0.5, 1.5, size=n)                      # degraded prior
    prob = Problem(G=G, y=y, x0=h0, name="i405_dynamic(flattened)")
    return prob, dict(h_true=h_true, y=y, T=case.time_grid.T, n_cells=len(covered))


# ---------------------------------------------------------------- run + report
def vmt_vht_np(net, vmt_vht, x):
    return vmt_vht(net["Delta"] @ x, net["length"], net["vf"], net["alpha"], net["beta"], net["cap"])


def run_chicago(pert):
    prob, ctx = chicago_problem(pert)
    net, sensors, held, P = ctx["net"], ctx["sensors"], ctx["held"], ctx["P"]
    x_true, d_true = ctx["x_true"], ctx["d_true"]
    vmt_t, vht_t = vmt_vht_np(net, ctx["vmt_vht"], net["h_true"])
    print(f"\n===== Chicago static, perturbation={pert}  (m={prob.G.shape[0]} sensors, n={prob.G.shape[1]} paths) =====")
    print(f"{'solver':20} {'iters':>5} {'time_s':>7} {'held MAPE':>9} {'OD R2':>7} {'OD MAPE':>8} "
          f"{'dVHT%':>7} {'gate:count':>22}")
    for name, fn in SOLVERS.items():
        kw = {"rank": 80} if name == "low_rank" else {}
        res = fn(prob, **kw) if name != "low_rank" else fn(prob, rank=80)
        x = res.x
        xl = net["Delta"] @ x
        _, mape_h = _metrics(x_true[held], xl[held])
        d = np.asarray(P @ x).ravel()
        r2_od, mape_od = _metrics(d_true, d)
        _, vht = vmt_vht_np(net, ctx["vmt_vht"], x)
        gate = gate_count_quality(x_true[held].tolist(), xl[held].tolist())
        print(f"{res.solver:20} {res.iters:>5} {res.runtime_s:>7.2f} {mape_h:>8.1f}% {r2_od:>7.3f} "
              f"{mape_od:>7.1f}% {100*(vht-vht_t)/vht_t:>+6.1f} {gate.status+': '+gate.finding[:14]:>22}")


def run_dynamic():
    prob, ctx = dynamic_problem()
    h_true = ctx["h_true"]
    print(f"\n===== Corridor dynamic, FLATTENED operator  (T={ctx['T']} bins -> G is "
          f"{prob.G.shape[0]} cells x {prob.G.shape[1]} time-columns) =====")
    print(f"seed fit MAPE = {_metrics(prob.y, prob.G @ prob.x0)[1]:.1f}%")
    print(f"{'solver':20} {'iters':>5} {'time_s':>7} {'fit MAPE':>9} {'flow R2':>8}")
    for name, fn in SOLVERS.items():
        res = fn(prob, rank=80) if name == "low_rank" else fn(prob)
        _, mape = _metrics(prob.y, prob.G @ res.x)
        r2, _ = _metrics(h_true, res.x)
        print(f"{res.solver:20} {res.iters:>5} {res.runtime_s:>7.2f} {mape:>8.1f}% {r2:>8.3f}")


def main(argv):
    if argv and argv[0] == "dynamic":
        run_dynamic()
    else:
        for pert in (0.10, "rand"):
            run_chicago(pert)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
