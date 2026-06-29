"""Gradient-deviation ODME — port of DTALite ODME.h, operating on (link,t) cells.

Decision variables are the route-column volumes (as in ODME.h). At T=1 these are the
per-link deviations; at T>1 the same loop runs over (link,t) cells. One solver, all T.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass


@dataclass
class ODMEParams:
    iterations: int = 40
    weight_of_measurements: float = 1.0   # w_meas; (1-w) would weight a UE_gap term (off in v0)
    bound: float = 0.10                   # max +/- fractional change per column per iter
    gradient_scale: float = 1.0e-3        # maps vehicle-deviation to a volume step (tunable)
    smooth_gamma: float = 0.0             # temporal smoothing strength (T>1 only); 0 = off


def _build_groups(columns):
    """group_id -> {tau: col_idx} for time-columns sharing a base route."""
    groups: dict = {}
    for ci, col in enumerate(columns):
        if col.group_id >= 0:
            groups.setdefault(col.group_id, {})[col.tau] = ci
    return groups


def _smooth(columns, groups, gamma, step):
    """Gentle temporal regularizer: pull each time-column toward its tau-neighbor mean, scaled by
    the decaying `step` so it does NOT compound to a flat profile over many iterations (plan step 7)."""
    eff = gamma * step
    updates = {}
    for g, by_tau in groups.items():
        for tau, ci in by_tau.items():
            neigh = [by_tau[t] for t in (tau - 1, tau + 1) if t in by_tau]
            if not neigh:
                continue
            target = sum(columns[n].volume for n in neigh) / len(neigh)
            updates[ci] = (1.0 - eff) * columns[ci].volume + eff * target
    for ci, v in updates.items():
        columns[ci].volume = max(0.0, v)


def _moe(A, columns):
    """Mean abs error / MAPE / mean pct error over measured, column-covered cells."""
    n, mae, mape, mpe = 0, 0.0, 0.0, 0.0
    vols = A.link_volume(columns)
    for cell, m in A.measured_cells.items():
        if cell not in A.incidence:
            continue  # uncovered: skip from fit MOE (reported separately by readiness)
        est = vols.get(cell, 0.0)
        obs = m.obs_volume
        n += 1
        mae += abs(est - obs)
        if obs > 1e-9:
            mape += abs(est - obs) / obs
            mpe += (est - obs) / obs
    if n == 0:
        return dict(n=0, mae=0.0, mape_pct=0.0, mpe_pct=0.0)
    return dict(n=n, mae=mae / n, mape_pct=100.0 * mape / n, mpe_pct=100.0 * mpe / n)


def solve(case, A, R, params: ODMEParams):
    columns = case.columns
    log_rows = []
    n_active = sum(1 for cell in A.measured_cells if cell in A.incidence)
    groups = _build_groups(columns) if (A.T > 1 and params.smooth_gamma > 0) else {}

    # precompute, once, the measured cells each column passes through (was O(cols*cells)/iter)
    col_cells: dict = {}
    for cell in A.measured_cells:
        for (ci, prop) in A.incidence.get(cell, ()):  # only measured cells matter for the gradient
            col_cells.setdefault(ci, []).append((cell, prop))

    for k in range(params.iterations):
        vols = A.link_volume(columns)

        # per measured cell deviation (with upper-bound masking)
        dev = {}
        for cell, m in A.measured_cells.items():
            if cell not in A.incidence:
                continue
            d = vols.get(cell, 0.0) - m.obs_volume   # + preload (0 in v0)
            if m.upper_bound_flag and d < 0:
                d = 0.0                              # at capacity: penalize only over-prediction
            dev[cell] = d

        step = 1.0 / (k + 2.0)

        # per-column gradient = sum of deviations on the measured cells it hits
        for ci, col in enumerate(columns):
            cells = col_cells.get(ci)
            if not cells:
                continue
            grad = 0.0
            for (cell, prop) in cells:
                grad += dev.get(cell, 0.0) * prop
            if grad == 0.0:
                continue
            change = step * params.weight_of_measurements * params.gradient_scale * grad * col.volume
            lim = params.bound * max(col.volume, 1.0)
            change = max(-lim, min(lim, change))
            col.volume = max(0.0, col.volume - change)

        if groups:
            _smooth(columns, groups, params.smooth_gamma, step)

        moe = _moe(A, columns)
        log_rows.append(dict(iter=k, step_size=round(step, 5), **moe, n_active_counts=n_active))
        # convergence: stop after iter 5 if MAPE gap small
        if k >= 5 and moe["mape_pct"] < 1.0:
            break

    return log_rows


def write_log(out_dir: str, log_rows) -> str:
    path = os.path.join(out_dir, "odme_log.csv")
    cols = ["iter", "step_size", "n", "mae", "mape_pct", "mpe_pct", "n_active_counts"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in log_rows:
            w.writerow({c: r.get(c, "") for c in cols})
    return path
