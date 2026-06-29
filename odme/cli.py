"""Command-line entrance.

    python -m odme check <case_dir>          # Stage 0 only: readiness + filler, writes report
    python -m odme run   <case_dir> [--source columns]   # Stage 0 + build A + solve at T

Static vs dynamic is decided by the time grid (T), never a flag.
"""
from __future__ import annotations

import argparse
import sys

from .readiness import load_case, run_checks, build_report, write_report
from .matrix import build_A, build_R, dump_matrix_A
from .solve import solve, write_log, ODMEParams
from .report import validate


def _check(case_dir: str):
    case, log = load_case(case_dir)
    stats = run_checks(case, log)
    text = build_report(case, log, stats)
    print(text)
    out = write_report(case_dir, text)
    print(f"\n-> {out}")
    return case, log, stats


def cmd_check(args):
    case, log, _ = _check(args.case_dir)
    return 0 if log.ready else 2


def cmd_run(args):
    case, log, stats = _check(args.case_dir)
    if not log.ready:
        print("\nNOT READY -> not solving. Fix the fatals above.")
        return 2

    if args.approx and stats.get("measurements_uncovered"):
        from .matrix.sources.approximate import augment
        added = augment(case, stats["measurements_uncovered"])
        print(f"\n[approximate] synthesized {len(added)} forced-through column(s) for uncovered "
              f"measured links {sorted(set(stats['measurements_uncovered']))} (seeded, flagged approximate)")

    A = build_A(case, source=args.source)
    R = build_R(case)
    mpath = dump_matrix_A(A, case, args.case_dir)
    n_cells = len(A.incidence)
    n_meas_cells = len(A.measured_cells)
    n_covered = sum(1 for c in A.measured_cells if c in A.incidence)
    print(f"\n[build_A] source={args.source} T={A.T}  cells={n_cells}  "
          f"measured_cells={n_meas_cells} (covered={n_covered})  -> {mpath}")

    params = ODMEParams(iterations=args.iterations)
    log_rows = solve(case, A, R, params)
    lpath = write_log(args.case_dir, log_rows)
    vpath, metrics = validate(case, A, args.case_dir)

    print(f"[solve] iterations run={len(log_rows)}")
    if log_rows:
        first, last = log_rows[0], log_rows[-1]
        print(f"   MAPE {first['mape_pct']:.2f}% -> {last['mape_pct']:.2f}% | "
              f"MAE {first['mae']:.1f} -> {last['mae']:.1f}")
    print(f"[validate] fit on covered cells: {metrics}")
    print(f"-> {lpath}\n-> {vpath}")
    if n_covered < n_meas_cells:
        print(f"\nNOTE: {n_meas_cells - n_covered} measured cell(s) have NO column coverage "
              f"and cannot be fit by `columns` source alone -> needs the approximate/external adapter.")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="odme")
    sub = p.add_subparsers(dest="cmd", required=True)
    pc = sub.add_parser("check", help="Stage 0 readiness check only")
    pc.add_argument("case_dir")
    pc.set_defaults(func=cmd_check)
    pr = sub.add_parser("run", help="readiness + build A + solve")
    pr.add_argument("case_dir")
    pr.add_argument("--source", default="columns")
    pr.add_argument("--iterations", type=int, default=40)
    pr.add_argument("--approx", action="store_true",
                    help="synthesize forced-through columns for uncovered measured links")
    pr.set_defaults(func=cmd_run)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
