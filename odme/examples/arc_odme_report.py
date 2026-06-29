"""ARC super-zone ODME — matrix-free, calibration-target-driven, before/after + compression levels.

Steps B-D of the plan:
  B. before/after ODME calibration report (count RMSE, VMT, VHT, ratio, stratified, OD distortion)
  C. regularized ODME: min ||M ΔR d - y_obs||^2 + λ||d-d0||^2  (projected gradient, matrix-free)
  D. compare compression levels (exact / top-1 / cum-95%) by calibration gates, not matrix error.

Target = OBSERVED counts (DIRAADT15 x AM-factor) from the shapefile; NOT a dense matrix.
Run:  python -m odme.examples.arc_odme_report
"""
from __future__ import annotations

import csv
import time

import numpy as np
import scipy.sparse as sp

from ..operator import build_operator, prune_paths
from ..gates import calibration_layers as CL

import os
# ARC raw network (~3.7 GB) is NOT bundled in this repo. Set ARC_DATA to a local copy.
A = os.environ.get("ARC_DATA", "100_arc_atlanta")
SZ = A + "/gmns_superzone"


def load_counts(op):
    """Map observed counts -> operator link index; return sensors, y_obs, factype, screenline."""
    lix = {a: i for i, a in enumerate(op.link_ids)}
    sens, y, fac, scr = [], [], [], []
    for r in csv.DictReader(open("cases/09_arc_atlanta/arc_observed_counts.csv", encoding="utf-8-sig")):
        lid = int(float(r["link_id"]))
        if lid in lix:
            sens.append(lix[lid]); y.append(float(r["am_observed_est"]))
            fac.append(CL.FACILITY.get(int(float(r["factype"])), "other")); scr.append(int(float(r["screenline"])))
    return np.array(sens), np.array(y), fac, np.array(scr)


def reg_odme(op, M, y, d0, lam=0.1, iters=60):
    """min ||M ΔR d - y||^2 + λ||d-d0||^2, projected onto d>=0 (matrix-free)."""
    MT = M.T.tocsr()
    def Ad(d):
        return M @ op.matvec(d)
    def ATr(r):
        return op.rmatvec(MT @ r)
    # power iteration for Lipschitz of A^T A
    v = np.random.default_rng(0).standard_normal(op.n_od)
    for _ in range(12):
        v = ATr(Ad(v)); v /= np.linalg.norm(v) + 1e-12
    Lip = np.linalg.norm(ATr(Ad(v))) + lam + 1e-9
    lr = 1.0 / Lip
    d = d0.astype(float).copy()
    for k in range(iters):
        g = ATr(Ad(d) - y) + lam * (d - d0)
        d = np.maximum(0.0, d - lr * g)
    return d


def stratified(sens_x, y, fac, op, sens):
    rows = [dict(assigned=float(xi), observed=float(yi), facility=fi, screenline=0, length=1.0)
            for xi, yi, fi in zip(sens_x, y, fac)]
    return rows


def calib(op, d, sens, y, fac, label):
    x = op.matvec(d)
    xs = x[sens]
    rows = [dict(assigned=float(a), observed=float(o), facility=f, length=1.0)
            for a, o, f in zip(xs, y, fac)]
    vol = CL.by_volume_group(rows)
    rmse = np.sqrt(np.mean((xs - y) ** 2)); pct = 100 * rmse / max(y.mean(), 1)
    ratio = xs.sum() / max(y.sum(), 1)
    agg = op.aggregate(x)
    print(f"  [{label:6}] count %RMSE={pct:5.1f}%  ratio={ratio:.3f}  VMT={agg['VMT']:,.0f}  VHT={agg['VHT']:,.0f}")
    return dict(pct_rmse=pct, ratio=ratio, vmt=agg["VMT"], vht=agg["VHT"], vol=vol)


def main():
    t0 = time.time()
    print("building ARC super-zone operator (matrix-free) ...")
    op = build_operator(SZ + "/route_assignment.csv", SZ + "/link.csv")
    print(f"  operator: {op.n_od} OD, {op.P} paths, {op.L} links, {op.memory_mb():.0f} MB, build {time.time()-t0:.0f}s")
    sens, y, fac, scr = load_counts(op)
    M = sp.csr_matrix((np.ones(len(sens)), (range(len(sens)), sens)), shape=(len(sens), op.L))
    print(f"  observed counts mapped: {len(sens)} sensor links\n")

    print("=== B/C: before vs after regularized ODME (exact operator) ===")
    before = calib(op, op.d0, sens, y, fac, "BEFORE")
    t = time.time(); d_hat = reg_odme(op, M, y, op.d0, lam=0.1); todme = time.time() - t
    after = calib(op, d_hat, sens, y, fac, "AFTER")
    dist = 100 * np.abs(d_hat - op.d0).sum() / max(op.d0.sum(), 1)
    print(f"  ODME: {todme:.0f}s | OD distortion (|Δd|/d0) = {dist:.1f}%  "
          f"| dVMT={100*(after['vmt']-before['vmt'])/before['vmt']:+.1f}% dVHT={100*(after['vht']-before['vht'])/before['vht']:+.1f}%")
    print(f"  count %RMSE {before['pct_rmse']:.0f}% -> {after['pct_rmse']:.0f}%")

    print("\n=== D: compression-level comparison (ODME under each, judged by gates) ===")
    print(f"  {'operator':>14} {'paths%':>7} {'before%RMSE':>11} {'after%RMSE':>11} {'dVHT%':>7} {'ODdist%':>8}")
    for name, kw in [("exact", None), ("top-1", dict(top_k=1)), ("cum-95%", dict(cum_flow=0.95))]:
        o = op if kw is None else prune_paths(op, **kw)
        Mo = sp.csr_matrix((np.ones(len(sens)), (range(len(sens)), sens)), shape=(len(sens), o.L))
        b = np.sqrt(np.mean((o.matvec(o.d0)[sens] - y) ** 2)) / max(y.mean(), 1) * 100
        dh = reg_odme(o, Mo, y, o.d0, lam=0.1, iters=40)
        xa = o.matvec(dh)
        a = np.sqrt(np.mean((xa[sens] - y) ** 2)) / max(y.mean(), 1) * 100
        vb = o.aggregate(o.matvec(o.d0))["VHT"]; va = o.aggregate(xa)["VHT"]
        od = 100 * np.abs(dh - o.d0).sum() / max(o.d0.sum(), 1)
        print(f"  {name:>14} {100*o.P/op.P:>6.0f}% {b:>10.1f}% {a:>10.1f}% {100*(va-vb)/vb:>+6.1f} {od:>7.1f}%")

    # outputs
    with open("cases/09_arc_atlanta/before_after_calibration_summary.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["stage", "count_pct_rmse", "vol_count_ratio", "VMT", "VHT"])
        w.writerow(["before", round(before["pct_rmse"], 1), round(before["ratio"], 3), round(before["vmt"]), round(before["vht"])])
        w.writerow(["after", round(after["pct_rmse"], 1), round(after["ratio"], 3), round(after["vmt"]), round(after["vht"])])
    print("\n-> cases/09_arc_atlanta/before_after_calibration_summary.csv")


if __name__ == "__main__":
    main()
