"""ARC super-zone — reasonableness-constrained ODME λ-sweep (matrix-free).

Objective:  min ‖MΔR d − y_obs‖²  + λ_OD‖(d−d0)/(d0+ε)‖²
                                   + λ_VMT((VMT(d)−VMT*)/VMT*)²
                                   + λ_VHT((VHT(d)−VHT*)/VHT*)²
VMT(d)=c_vmtᵀd, VHT(d)=c_vhtᵀd are LINEAR in d (c_vmt=(ΔR)ᵀ·length, c_vht=(ΔR)ᵀ·fftt),
so the constraint gradients are exact rank-1 terms. Projected gradient, FIXED 50 iters, lr=1/L
(combined Lipschitz) — one canonical config for reproducibility.

Stage 1: λ_OD sweep (VMT/VHT off). Stage 2: VMT/VHT-constrained grid. Plus a deliberately-bad case,
a gate-balanced operating point, and the compression comparison. Targets = base (anti-inflation
placeholder; replace with regional GDOT VMT). Gate Δ% reported vs base AND vs under-load-corrected target.

Run:  python -m odme.examples.arc_odme_lambda_sweep
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
EPS = 1.0
ITERS = 50
CASE = "cases/09_arc_atlanta"


def load_cached_operator():
    import os, pickle
    from ..operator.assignment_operator import AssignmentOperator
    if not os.path.exists("cache_arc_pathlink.npz"):
        return None
    pl = sp.load_npz("cache_arc_pathlink.npz")
    a = np.load("cache_arc_arrays.npz", allow_pickle=True)
    odk = pickle.load(open("cache_arc_odkeys.pkl", "rb"))
    return AssignmentOperator(pl, a["path_od"], a["share"], odk, list(a["link_ids"]),
                              a["length"], a["fftt"], a["d0"])


def load_counts(op):
    lix = {a: i for i, a in enumerate(op.link_ids)}
    sens, y, fac = [], [], []
    for r in csv.DictReader(open(CASE + "/arc_observed_counts.csv", encoding="utf-8-sig")):
        lid = int(float(r["link_id"]))
        if lid in lix:
            sens.append(lix[lid]); y.append(float(r["am_observed_est"]))
            fac.append(CL.FACILITY.get(int(float(r["factype"])), "other"))
    return np.array(sens), np.array(y), fac


def solve(op, M, y, d0, c_vmt, c_vht, vmt_t, vht_t, L0, s_count, lam_od, lam_vmt, lam_vht):
    """Normalized objective: count term divided by base count SSE so λ are O(1) dimensionless weights."""
    MT = M.T.tocsr()
    inv = 1.0 / (d0 + EPS) ** 2
    # Lipschitz of the SCALED objective
    L = (L0 / s_count + lam_od * 2 * inv.max()
         + lam_vmt * 2 * float(c_vmt @ c_vmt) / vmt_t ** 2
         + lam_vht * 2 * float(c_vht @ c_vht) / vht_t ** 2)
    lr = 1.0 / (L + 1e-12)
    d = d0.astype(float).copy()
    for k in range(ITERS):
        g = op.rmatvec(MT @ (M @ op.matvec(d) - y)) / s_count          # scaled count term
        if lam_od:
            g = g + lam_od * 2 * (d - d0) * inv
        if lam_vmt:
            g = g + lam_vmt * 2 * (float(c_vmt @ d) - vmt_t) / vmt_t ** 2 * c_vmt
        if lam_vht:
            g = g + lam_vht * 2 * (float(c_vht @ d) - vht_t) / vht_t ** 2 * c_vht
        d = np.maximum(0.0, d - lr * g)
    return d


def metrics(op, d, sens, y, fac, base_vmt, base_vht, vmt_t, vht_t, d0):
    x = op.matvec(d); xs = x[sens]
    rmse = np.sqrt(np.mean((xs - y) ** 2)); pct = 100 * rmse / max(y.mean(), 1)
    ratio = xs.sum() / max(y.sum(), 1)
    vmt = float(x @ op.length); vht = float(x @ op.fftt)
    od = 100 * np.abs(d - d0).sum() / max(d0.sum(), 1)
    return dict(pct_rmse=pct, ratio=ratio,
                dVMT_base=100 * (vmt - base_vmt) / base_vmt, dVHT_base=100 * (vht - base_vht) / base_vht,
                dVMT_tgt=100 * (vmt - vmt_t) / vmt_t, od=od)


def gate(m):
    g = []
    g.append("count" + ("PASS" if m["pct_rmse"] < 60 else "WARN"))
    g.append("VMT" + ("PASS" if abs(m["dVMT_base"]) <= 10 else "WARN"))
    g.append("OD" + ("PASS" if m["od"] <= 20 else "WARN"))
    return " ".join(g)


def main():
    t0 = time.time()
    op = load_cached_operator()
    if op is None:
        print("building ARC super-zone operator ...")
        op = build_operator(SZ + "/route_assignment.csv", SZ + "/link.csv")
    print(f"  {op.n_od} OD, {op.P} paths, {op.L} links, load/build {time.time()-t0:.0f}s")
    sens, y, fac = load_counts(op)
    M = sp.csr_matrix((np.ones(len(sens)), (range(len(sens)), sens)), shape=(len(sens), op.L))
    c_vmt = op.rmatvec(op.length); c_vht = op.rmatvec(op.fftt)
    x0 = op.matvec(op.d0); base_vmt = float(x0 @ op.length); base_vht = float(x0 @ op.fftt)
    base_ratio = x0[sens].sum() / max(y.sum(), 1)
    s_count = float(((x0[sens] - y) ** 2).sum())          # base count SSE (term normalizer)
    vmt_t, vht_t = base_vmt, base_vht                     # anti-inflation placeholder
    vmt_corr = base_vmt / max(base_ratio, 0.1)            # under-load-corrected (regional proxy)
    # power-iteration Lipschitz of count operator A=MΔR
    v = np.random.default_rng(0).standard_normal(op.n_od)
    for _ in range(12):
        v = op.rmatvec(M.T @ (M @ op.matvec(v))); v /= np.linalg.norm(v) + 1e-12
    L0 = float(np.linalg.norm(op.rmatvec(M.T @ (M @ op.matvec(v)))))
    print(f"  base: count %RMSE={100*np.sqrt(np.mean((x0[sens]-y)**2))/y.mean():.1f}%  ratio={base_ratio:.3f}  "
          f"VMT={base_vmt:,.0f}  (regional-proxy VMT*={vmt_corr:,.0f})\n")

    rows = []
    def run(tag, lod, lvmt, lvht):
        d = solve(op, M, y, op.d0, c_vmt, c_vht, vmt_t, vht_t, L0, s_count, lod, lvmt, lvht)
        m = metrics(op, d, sens, y, fac, base_vmt, base_vht, vmt_t, vht_t, op.d0)
        row = dict(tag=tag, lod=lod, lvmt=lvmt, lvht=lvht, **m, gate=gate(m))
        rows.append(row)
        return row

    print("=== Stage 1: OD-prior λ sweep (VMT/VHT off) ===")
    print(f" {'λ_OD':>6} {'%RMSE':>6} {'ratio':>6} {'dVMT%':>7} {'dVHT%':>7} {'ODdist%':>8}  gate")
    for lod in (0, 1e-5, 3e-5, 1e-4, 3e-4, 1e-3, 3e-3, 1e-2):
        m = run(f"s1_od{lod}", lod, 0, 0)
        print(f" {lod:>6} {m['pct_rmse']:>5.1f}% {m['ratio']:>6.2f} {m['dVMT_base']:>+6.1f} "
              f"{m['dVHT_base']:>+6.1f} {m['od']:>7.1f}%  {m['gate']}")

    print("\n=== Stage 2: VMT/VHT-constrained grid ===")
    print(f" {'λ_OD':>5} {'λ_VMT':>6} {'λ_VHT':>6} {'%RMSE':>6} {'ratio':>6} {'dVMT%':>7} {'dVHT%':>7} {'ODdist%':>8}  gate")
    for lod in (1e-4, 3e-4):
        for lvmt, lvht in [(0, 0), (1e4, 0), (1e5, 0), (1e6, 0), (1e6, 1e6)]:
            m = run(f"s2_od{lod}_v{lvmt}_h{lvht}", lod, lvmt, lvht)
            print(f" {lod:>5} {lvmt:>6} {lvht:>6} {m['pct_rmse']:>5.1f}% {m['ratio']:>6.2f} "
                  f"{m['dVMT_base']:>+6.1f} {m['dVHT_base']:>+6.1f} {m['od']:>7.1f}%  {m['gate']}")

    # bad vs constrained contrast
    print("\n=== Bad (free) vs constrained ODME ===")
    bad = next(r for r in rows if r["tag"] == "s1_od0.01")
    con = min((r for r in rows if "WARN" not in r["gate"]), key=lambda r: r["pct_rmse"], default=None)
    print(f"  BAD (λ_OD=0.01):       %RMSE={bad['pct_rmse']:.0f}%  dVMT={bad['dVMT_base']:+.0f}%  ODdist={bad['od']:.0f}%  -> {bad['gate']}")
    if con:
        print(f"  CONSTRAINED (best all-pass): λ_OD={con['lod']} λ_VMT={con['lvmt']} λ_VHT={con['lvht']}  "
              f"%RMSE={con['pct_rmse']:.0f}%  dVMT={con['dVMT_base']:+.0f}%  ODdist={con['od']:.0f}%  -> {con['gate']}")

    # operating point = best gate-balanced (count improves AND VMT/OD pass), else best VMT-bounded
    cands = [r for r in rows if "WARN" not in r["gate"] and r["pct_rmse"] < 82]
    sel = min(cands, key=lambda r: r["pct_rmse"]) if cands else \
        min(rows, key=lambda r: (abs(r["dVMT_base"]) > 10, r["pct_rmse"]))

    # compression comparison at the selected λ
    print(f"\n=== Compression comparison at selected λ (OD={sel['lod']} VMT={sel['lvmt']} VHT={sel['lvht']}) ===")
    comp = []
    print(f"  {'operator':>10} {'paths%':>7} {'%RMSE':>6} {'dVMT%':>7} {'ODdist%':>8}")
    for name, kw in [("exact", None), ("top-1", dict(top_k=1)), ("cum-95%", dict(cum_flow=0.95))]:
        o = op if kw is None else prune_paths(op, **kw)
        Mo = sp.csr_matrix((np.ones(len(sens)), (range(len(sens)), sens)), shape=(len(sens), o.L))
        cv = o.rmatvec(o.length); ch = o.rmatvec(o.fftt)
        x0o = o.matvec(o.d0); bv = float(x0o @ o.length); bh = float(x0o @ o.fftt)
        sco = float(((x0o[sens] - y) ** 2).sum())
        vv = np.random.default_rng(0).standard_normal(o.n_od)
        for _ in range(8):
            vv = o.rmatvec(Mo.T @ (Mo @ o.matvec(vv))); vv /= np.linalg.norm(vv) + 1e-12
        L0o = float(np.linalg.norm(o.rmatvec(Mo.T @ (Mo @ o.matvec(vv)))))
        d = solve(o, Mo, y, o.d0, cv, ch, bv, bh, L0o, sco, sel["lod"], sel["lvmt"], sel["lvht"])
        m = metrics(o, d, sens, y, fac, bv, bh, bv, bh, o.d0)
        comp.append(dict(operator=name, paths=100*o.P/op.P, **m))
        print(f"  {name:>10} {100*o.P/op.P:>6.0f}% {m['pct_rmse']:>5.1f}% {m['dVMT_base']:>+6.1f} {m['od']:>7.1f}%")

    # write outputs
    with open(CASE + "/lambda_sweep_summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["tag", "lod", "lvmt", "lvht", "pct_rmse", "ratio",
                                          "dVMT_base", "dVHT_base", "dVMT_tgt", "od", "gate"])
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()})
    with open(CASE + "/selected_operating_point.md", "w", encoding="utf-8") as f:
        f.write(f"# ARC selected ODME operating point\n\n")
        f.write(f"Selected: λ_OD={sel['lod']}, λ_VMT={sel['lvmt']}, λ_VHT={sel['lvht']} — reduces count %RMSE "
                f"from 82.8% to {sel['pct_rmse']:.0f}% while keeping VMT Δ within {sel['dVMT_base']:+.0f}% (vs base), "
                f"VHT Δ {sel['dVHT_base']:+.0f}%, OD distortion {sel['od']:.0f}%.  Gate: {sel['gate']}.\n\n")
        f.write(f"VMT target = base (anti-inflation placeholder); under-load-corrected regional proxy = {vmt_corr:,.0f} "
                f"(base/{base_ratio:.2f}). Replace with regional GDOT VMT when available.\n")
    with open(CASE + "/compression_lambda_comparison.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["operator", "paths", "pct_rmse", "ratio", "dVMT_base", "dVHT_base", "od"])
        w.writeheader()
        for c in comp:
            w.writerow({k: (round(v, 2) if isinstance(v, float) else v) for k, v in c.items() if k in w.fieldnames})

    print(f"\n>>> SELECTED: λ_OD={sel['lod']} λ_VMT={sel['lvmt']} λ_VHT={sel['lvht']}: "
          f"%RMSE 82.8%->{sel['pct_rmse']:.0f}%, dVMT {sel['dVMT_base']:+.0f}%, OD dist {sel['od']:.0f}%  [{sel['gate']}]")
    print("-> lambda_sweep_summary.csv, selected_operating_point.md, compression_lambda_comparison.csv")


if __name__ == "__main__":
    main()
