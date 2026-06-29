"""Gate runner.

  python -m odme.gates verify cases/00_tiny_panel      # Gate 1-7 verification (matrices, rank)
  python -m odme.gates review cases/07_i405_pm         # reasonableness: FLAT vs ODME, flag what count-R2 hides
"""
from __future__ import annotations

import sys
from collections import defaultdict

from .verification import run_verification
from . import reasonableness as RZ


def cmd_verify(case_dir):
    print(f"=== VERIFICATION GATES (G1-G7) : {case_dir} ===")
    for g in run_verification(case_dir):
        print(g.line())


def _agg_phi(cols):
    by_t = defaultdict(float); tot = 0.0
    for c in cols:
        by_t[c.tau] += c.volume; tot += c.volume
    T = (max(by_t) + 1) if by_t else 0
    return [by_t[t] / tot for t in range(T)] if tot else [0.0] * T


def cmd_review(case_dir):
    from ..examples.phi_benchmark import _grid_columns, _od_index, _odme, _set_cols
    from ..io.timedependent import load_dynamic_case
    from ..matrix import build_A

    case, ref, _ = load_dynamic_case(case_dir + "/network",
                                     case_dir + "/columns_timedependent.csv",
                                     case_dir + "/linkflow_timedependent.csv")
    T = case.time_grid.T
    dt_h = case.time_grid.interval_minutes / 60.0
    links = case.links

    od_path, od_total, true_x = {}, defaultdict(float), defaultdict(dict)
    for c in case.columns:
        od = (c.o_zone_id, c.d_zone_id)
        od_path.setdefault(od, c.link_ids); od_total[od] += c.volume
        true_x[od][c.tau] = true_x[od].get(c.tau, 0.0) + c.volume
    od_list = list(od_path)
    gid_of = {od: i for i, od in enumerate(od_list)}

    flat = {od: [1.0 / T] * T for od in od_list}
    flat_cols = _grid_columns(od_path, od_total, T, flat)
    A0 = build_A(_set_cols(case, flat_cols), source="columns")
    obs = {c: m.obs_volume for c, m in A0.measured_cells.items()}
    covered = [c for c in A0.measured_cells if c in A0.incidence]
    groups = _od_index(flat_cols)
    Xg = {gid_of[od]: od_total[od] for od in od_list}

    truth_cols = _grid_columns(od_path, od_total, T,
                               {od: [true_x[od].get(t, 0.0) / (od_total[od] or 1.0) for t in range(T)] for od in od_list})
    truth_vol = build_A(_set_cols(case, truth_cols), source="columns").link_volume(truth_cols)

    def vols_and_resid(cols):
        A = build_A(_set_cols(case, cols), source="columns"); A.measured_cells = A0.measured_cells
        v = A.link_volume(cols)
        resid = defaultdict(float)
        for c in covered:
            resid[c[0]] += v[c] - obs[c]
        return v, resid

    print(f"=== REASONABLENESS GATES : {case_dir}  (T={T}, OD={len(od_list)}) ===")
    for tag, cols in (("FLAT baseline", flat_cols),
                      ("ODME (from flat)", None)):
        if cols is None:
            cols = _grid_columns(od_path, od_total, T, flat)
            A = build_A(_set_cols(case, cols), source="columns"); A.measured_cells = A0.measured_cells
            _odme(cols, A, obs, covered, groups, Xg, iters=150)
        v, resid = vols_and_resid(cols)
        y = [obs[c] for c in covered]; yh = [v[c] for c in covered]
        phi = _agg_phi(cols)
        d_now = {od: od_total[od] for od in od_list}   # totals conserved
        print(f"\n-- {tag} --")
        print(" ", RZ.gate_count_quality(y, yh).line())
        print(" ", RZ.gate_vmt_vht(truth_vol, v, links, dt_h).line())
        print(" ", RZ.gate_od_distortion(d_now, {od: od_total[od] for od in od_list}).line())
        print(" ", RZ.gate_departure_profile(phi).line())
        print(" ", RZ.gate_corridor_residual(resid).line())


def main(argv):
    if len(argv) < 2:
        print(__doc__); return 1
    cmd, case = argv[0], argv[1]
    if cmd == "verify":
        cmd_verify(case)
    elif cmd == "review":
        cmd_review(case)
    else:
        print(__doc__); return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
