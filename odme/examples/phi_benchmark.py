"""Rigorous time-dependent OD / phi(t) benchmark with realistic regularization.

Addresses the "results too good to believe" critique: instead of seeding with the turnkey's
TRUE time-dependent columns (trivial reproduction), we start from a naive departure profile
and measure recovery. Single-path corridors => link flow y_{a,t} is determined by OD totals
times phi(t), so this is a clean phi-recovery problem.

Base cases (benchmarks):
  - FLAT      phi_t = 1/T  (no peaking knowledge)
  - PIECEWISE K-step approximation of the AGGREGATE profile (knows overall peaking, not per-OD)
Realistic regularizer: OD-total CONSERVATION (sum_t x_{od,t} = known X_od) re-imposed each iter.

MOEs: link-flow fit (R2/RMSE/MAPE on covered cells), phi recovery (R2 of x_{od,t} vs truth),
and congestion-duration error (hours where D/C>threshold), vs each baseline.

Run:  python -m odme.examples.phi_benchmark [case_dir]
"""
from __future__ import annotations

import sys
from collections import defaultdict

from ..io.timedependent import load_dynamic_case
from ..model import Column
from ..matrix import build_A
from ..report.validate import _metrics

DEFAULT = "cases/07_i405_pm"
K_PIECES = 4
DC_THRESH = 0.90


def _paths():
    import os
    cd = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    return (cd, cd + "/network", cd + "/columns_timedependent.csv",
            cd + "/linkflow_timedependent.csv")


def _grid_columns(od_path, od_total, T, phi_by_od):
    """One column per (od, tau) over the full time grid, volume = X_od * phi[od][tau]."""
    cols = []
    for gi, (od, path) in enumerate(od_path.items()):
        X = od_total[od]
        for t in range(T):
            cols.append(Column(o_zone_id=od[0], d_zone_id=od[1], period="all",
                               volume=X * phi_by_od[od][t], link_ids=list(path),
                               tau=t, group_id=gi))
    return cols


def _od_index(cols):
    """group_id -> {tau: col_idx}  and  group_id -> X target."""
    g = defaultdict(dict)
    for ci, c in enumerate(cols):
        g[c.group_id][c.tau] = ci
    return g


def _conserve(cols, groups, X_by_group):
    """Re-impose sum_tau x = X_od per OD (the realistic regularizer)."""
    for gid, by_tau in groups.items():
        s = sum(cols[ci].volume for ci in by_tau.values())
        if s <= 1e-9:
            continue
        k = X_by_group[gid] / s
        for ci in by_tau.values():
            cols[ci].volume *= k


def _fit(A, cols, obs, covered):
    v = A.link_volume(cols)
    return _metrics([obs[c] for c in covered], [v[c] for c in covered])


def _phi_r2(cols, groups, true_x_by_group):
    """R2 of recovered x_{od,t} vs true x_{od,t} across all (od,t)."""
    ys, hh = [], []
    for gid, by_tau in groups.items():
        for t, ci in by_tau.items():
            ys.append(true_x_by_group[gid].get(t, 0.0))
            hh.append(cols[ci].volume)
    return _metrics(ys, hh)


def _congestion_hours(A, cols, links, T, dt_h):
    """Per-link congestion duration (hours with D/C>thresh), summed over links."""
    v = A.link_volume(cols)
    by_link = defaultdict(lambda: [0.0] * T)
    for (lid, t), vol in v.items():
        by_link[lid][t] = vol
    total_h = 0.0
    for lid, prof in by_link.items():
        lk = links.get(lid)
        if not lk or lk.link_capacity <= 0:
            continue
        cap15 = lk.link_capacity * dt_h
        total_h += dt_h * sum(1 for x in prof if x / cap15 > DC_THRESH)
    return total_h


def run(case_dir, net, cols_csv, lf_csv):
    case, ref, _ = load_dynamic_case(net, cols_csv, lf_csv)
    T = case.time_grid.T
    dt_h = case.time_grid.interval_minutes / 60.0
    obs_links = case.links

    # truth from the turnkey TD columns
    od_path, od_total, true_x = {}, defaultdict(float), defaultdict(dict)
    for c in case.columns:
        od = (c.o_zone_id, c.d_zone_id)
        od_path.setdefault(od, c.link_ids)
        od_total[od] += c.volume
        true_x[od][c.tau] = true_x[od].get(c.tau, 0.0) + c.volume
    od_list = list(od_path)
    gid_of = {od: i for i, od in enumerate(od_list)}

    # aggregate profile (for piecewise base case)
    agg = [0.0] * T
    for od in od_list:
        for t, x in true_x[od].items():
            agg[t] += x
    tot = sum(agg) or 1.0
    agg = [a / tot for a in agg]
    # K-step piecewise = block-average of aggregate
    pw = [0.0] * T
    step = max(1, T // K_PIECES)
    for s in range(0, T, step):
        blk = agg[s:s + step]
        m = sum(blk) / len(blk)
        for t in range(s, min(s + step, T)):
            pw[t] = m
    pw_sum = sum(pw) or 1.0
    pw = [p / pw_sum for p in pw]

    phi_flat = {od: [1.0 / T] * T for od in od_list}
    phi_pw = {od: list(pw) for od in od_list}

    # observed targets + index helpers
    base_cols = _grid_columns(od_path, od_total, T, phi_flat)
    A0 = build_A(_set_cols(case, base_cols), source="columns")
    obs = {c: m.obs_volume for c, m in A0.measured_cells.items()}
    covered = [c for c in A0.measured_cells if c in A0.incidence]
    groups = _od_index(base_cols)
    X_by_group = {gid_of[od]: od_total[od] for od in od_list}
    true_x_by_group = {gid_of[od]: true_x[od] for od in od_list}

    print(f"=== {case_dir.split('/')[-1]} === T={T} bins, OD_pairs={len(od_list)}, "
          f"grid_columns(TD)={len(base_cols)}, covered_cells={len(covered)}/{len(A0.measured_cells)}")

    def report(tag, cols, A):
        f = _fit(A, cols, obs, covered)
        pr = _phi_r2(cols, groups, true_x_by_group)
        ch = _congestion_hours(A, cols, obs_links, T, dt_h)
        print(f"  {tag:24} link[R2={f['r2']:.3f} RMSE={f['rmse']:.0f} MAPE={f['mape_pct']:.1f}%]  "
              f"phi[R2={pr['r2']:.3f}]  cong_hrs={ch:.1f}")
        return f, pr, ch

    # truth reference
    truth_cols = _grid_columns(od_path, od_total, T, {od: [true_x[od].get(t, 0.0) / (od_total[od] or 1.0)
                                                           for t in range(T)] for od in od_list})
    At = build_A(_set_cols(case, truth_cols), source="columns")
    print("  -- references --")
    report("TRUTH (turnkey phi)", truth_cols, At)

    print("  -- base cases (no ODME) --")
    flat_cols = _grid_columns(od_path, od_total, T, phi_flat)
    Af = build_A(_set_cols(case, flat_cols), source="columns")
    report("FLAT phi", flat_cols, Af)
    pw_cols = _grid_columns(od_path, od_total, T, phi_pw)
    Ap = build_A(_set_cols(case, pw_cols), source="columns")
    report("PIECEWISE phi (K=%d)" % K_PIECES, pw_cols, Ap)

    print("  -- ODME from each base (gradient + OD conservation) --")
    for seedtag, seedphi in (("from FLAT", phi_flat), ("from PIECEWISE", phi_pw)):
        cols = _grid_columns(od_path, od_total, T, seedphi)
        A = build_A(_set_cols(case, cols), source="columns")
        A.measured_cells = A0.measured_cells
        _odme(cols, A, obs, covered, groups, X_by_group, iters=150)
        report(f"ODME {seedtag}", cols, A)


def _set_cols(case, cols):
    case.columns = cols
    return case


def _odme(cols, A, obs, covered, groups, X_by_group, iters):
    col_cells = defaultdict(list)
    for cell in A.measured_cells:
        for (ci, prop) in A.incidence.get(cell, ()):
            col_cells[ci].append((cell, prop))
    for k in range(iters):
        v = A.link_volume(cols)
        dev = {c: v[c] - obs[c] for c in covered}
        step = 1.0 / (k + 2.0)
        for ci, cells in col_cells.items():
            g = sum(dev.get(c, 0.0) * p for c, p in cells)
            if g == 0.0:
                continue
            change = step * 1e-3 * g * max(cols[ci].volume, 1.0)
            lim = 0.25 * max(cols[ci].volume, 1.0)
            cols[ci].volume = max(0.0, cols[ci].volume - max(-lim, min(lim, change)))
        _conserve(cols, groups, X_by_group)   # realistic regularizer: keep OD totals fixed


if __name__ == "__main__":
    run(*_paths())
