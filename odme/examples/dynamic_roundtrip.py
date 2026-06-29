"""T>1 mechanism check — controlled round-trip on real Case 02 (Sioux Falls) columns.

Proves the SAME build_A + gradient_deviation machinery runs at T>1:
  1. take the 126 reconstructed columns,
  2. split each across T departure bins with a known profile phi (the "truth"),
  3. synthesize time-dependent targets y_{a,t} from that truth,
  4. perturb the per-bin volumes (uniform seed, wrong phi),
  5. solve with the unmodified solver and check it recovers y_{a,t}.

Also runs a T=1 regression guard: at T=1 the dynamic path reproduces the static fit.

Run:  python -m odme.examples.dynamic_roundtrip
"""
from __future__ import annotations

import copy

from ..readiness import load_case
from ..model import Column, Measurement, TimeGrid
from ..matrix import build_A, build_R
from ..solve import solve, ODMEParams
from ..report.validate import _metrics

CASE = "cases/02_sioux_falls"
PHI = [0.5, 0.3, 0.2]   # known departure-time profile (truth)


def _expand_time_columns(base_cols, phi, seed="phi"):
    """Replace each base column by T time-columns (one per departure bin tau)."""
    out = []
    T = len(phi)
    for gid, c in enumerate(base_cols):
        for tau in range(T):
            vol = c.volume * phi[tau] if seed == "phi" else c.volume / T
            out.append(Column(o_zone_id=c.o_zone_id, d_zone_id=c.d_zone_id, period="all",
                              volume=vol, link_ids=list(c.link_ids), tau=tau, group_id=gid))
    return out


def run_dynamic():
    case, _ = load_case(CASE)
    base = case.columns
    case.time_grid = TimeGrid(start_hour=7.0, end_hour=8.0,
                              interval_minutes=60.0 / len(PHI))   # -> T = len(PHI)
    print(f"T = {case.time_grid.T}  (interval {case.time_grid.interval_minutes:.0f} min), "
          f"phi = {PHI}, base columns = {len(base)}")

    # --- TRUTH: phi-split time-columns, synthesize y_{a,t} ---
    case.columns = _expand_time_columns(base, PHI, seed="phi")
    A_true = build_A(case, source="columns")
    true_vol = A_true.link_volume(case.columns)            # (link,t) -> true volume

    # --- PERTURB: reset to uniform seed (wrong temporal shape), observe every loaded cell ---
    case.columns = _expand_time_columns(base, PHI, seed="uniform")
    A = build_A(case, source="columns")
    A.measured_cells = {cell: Measurement(obs_volume=true_vol[cell]) for cell in A.incidence}

    pre = A.link_volume(case.columns)
    ys = [true_vol[c] for c in A.incidence]
    yhat0 = [pre[c] for c in A.incidence]
    print(f"  cells (link,t) = {len(A.incidence)}  | seed metrics  {_metrics(ys, yhat0)}")

    for gamma in (0.0, 0.2):
        case.columns = _expand_time_columns(base, PHI, seed="uniform")
        A2 = build_A(case, source="columns")
        A2.measured_cells = {cell: Measurement(obs_volume=true_vol[cell]) for cell in A2.incidence}
        solve(case, A2, build_R(case), ODMEParams(iterations=200, gradient_scale=1e-3, smooth_gamma=gamma))
        post = A2.link_volume(case.columns)
        yhat1 = [post[c] for c in A2.incidence]
        tag = "no-smooth" if gamma == 0 else f"smooth g={gamma}"
        bins = " ".join(f"t{t} R2={_metrics([true_vol[c] for c in A2.incidence if c[1]==t], [post[c] for c in A2.incidence if c[1]==t])['r2']}"
                        for t in range(case.time_grid.T))
        print(f"  [{tag:12}] overall {_metrics(ys, yhat1)} | {bins}")
    print("  note: on clean, fully-observed data with a non-flat true profile, smoothing only adds bias")
    print("        (correctly OFF by default); it is a regularizer for the noisy/sparse-data regime.")


def run_static_guard():
    """T=1 regression guard: the dynamic path with one bin == the static fit."""
    case, _ = load_case(CASE)
    case.time_grid = TimeGrid(7.0, 8.0, 60.0)  # T=1
    A = build_A(case, source="columns")
    # observe the same target_count measurements already loaded (path C)
    from ..readiness.checks import run_checks
    from ..readiness.field_reader import IssueLog
    run_checks(case, IssueLog())
    A = build_A(case, source="columns")
    log = solve(case, A, build_R(case), ODMEParams(iterations=80))
    post = A.link_volume(case.columns)
    ys = [m.obs_volume for c, m in A.measured_cells.items() if c in A.incidence]
    hh = [post[c] for c, m in A.measured_cells.items() if c in A.incidence]
    print(f"T=1 regression guard: {_metrics(ys, hh)}  (expect ~ static R2=0.9996)")


if __name__ == "__main__":
    print("=== T>1 dynamic round-trip (recover phi-split truth) ===")
    run_dynamic()
    print("\n=== T=1 regression guard ===")
    run_static_guard()
