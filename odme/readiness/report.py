"""Readiness report — console summary + readiness_report.md. The Stage-0 verdict."""
from __future__ import annotations

import os

from ..model import CaseData
from .field_reader import IssueLog


def _measurement_paths(case: CaseData) -> str:
    paths = sorted({m.source_path for m in case.measurements})
    return "+".join(paths) if paths else "none"


def build_report(case: CaseData, log: IssueLog, stats: dict) -> str:
    tg = case.time_grid
    n_meas = len(case.measurements)
    resolved = stats.get("measurements_resolved", 0)
    usable = stats.get("measurements_usable", 0)
    n_links = len(case.links)
    cov_pct = (100.0 * resolved / n_links) if n_links else 0.0
    filled = ", ".join(f"{k}({v})" for k, v in sorted(log.filled.items())) or "none"
    verdict = "READY" if log.ready else "NOT READY"
    regime = "static (T=1)" if tg.is_static else f"dynamic (T={tg.T})"

    lines = []
    lines.append(f"[READINESS] case={case.name}")
    lines.append(f" nodes={len(case.nodes)}  zones={stats.get('zones',0)}  links={n_links}  "
                 f"columns={len(case.columns)}  OD_pairs(cols)={stats.get('od_pairs_in_columns',0)}")
    lines.append(f" time grid: {tg.start_hour}-{tg.end_hour}h interval={tg.interval_minutes}min -> {regime}")
    lines.append(f" measurements: {n_meas} (path {_measurement_paths(case)}) | "
                 f"resolved {resolved}/{n_links} links ({cov_pct:.1f}%) | usable(with column coverage)={usable}")
    unc = sorted(set(stats.get("measurements_uncovered", [])))
    if unc:
        shown = unc[:20]
        more = f" … (+{len(unc)-20} more)" if len(unc) > 20 else ""
        lines.append(f" UNCOVERED measured links (no column through them): {shown}{more}")
    lines.append(f" filled-by-default: {filled}")
    for w in log.warnings:
        lines.append(f" warn: {w}")
    for e in log.errors:
        lines.append(f" drop: {e}")
    for fz in log.fatals:
        lines.append(f" FATAL: {fz}")
    lines.append(f" VERDICT: {verdict}  ({regime})")
    return "\n".join(lines)


def write_report(case_dir: str, text: str) -> str:
    out = os.path.join(case_dir, "readiness_report.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("# ODME readiness report\n\n```\n" + text + "\n```\n")
    return out
