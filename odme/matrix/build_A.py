"""Assemble the one sparse assignment matrix A from a chosen source adapter.

A rows = measurement cells (link_id, t); A cols = route columns (the ODME decision vars,
as in DTALite ODME.h). At T=1 every cell has t=0 and A reduces to the static B incidence.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field

from ..model import CaseData, Measurement
from .sources import ADAPTERS


@dataclass
class AssignmentMatrix:
    T: int
    source: str
    # (link_id, t) -> list of (col_idx, proportion)
    incidence: dict = field(default_factory=dict)
    # (link_id, t) -> Measurement  (only cells we observe)
    measured_cells: dict = field(default_factory=dict)

    def cells_through_column(self, col_idx: int):
        """Measured cells a given column passes through (for the path gradient)."""
        out = []
        for cell, lst in self.incidence.items():
            if cell in self.measured_cells:
                for (ci, prop) in lst:
                    if ci == col_idx:
                        out.append((cell, prop))
        return out

    def link_volume(self, columns):
        """Rebuild estimated volume on every (link_id, t) cell from current column volumes."""
        vol = {}
        for cell, lst in self.incidence.items():
            vol[cell] = sum(columns[ci].volume * prop for (ci, prop) in lst)
        return vol


def build_A(case: CaseData, source: str = "columns") -> AssignmentMatrix:
    if source not in ADAPTERS:
        raise ValueError(f"unknown A source '{source}'; have {list(ADAPTERS)}")
    T = case.time_grid.T
    A = AssignmentMatrix(T=T, source=source)
    for (lid, t, ci, prop) in ADAPTERS[source].entries(case):
        A.incidence.setdefault((lid, t), []).append((ci, prop))

    # attach measurements to cells. Time-keyed (t_bin) measurements -> (link, t_bin); else t=0.
    for m in case.measurements:
        if m.link_id is None:
            continue
        t = m.t_bin if (m.t_bin is not None and T > 1) else 0
        A.measured_cells[(m.link_id, t)] = m
    return A


def dump_matrix_A(A: AssignmentMatrix, case: CaseData, out_dir: str) -> str:
    path = os.path.join(out_dir, "matrix_A.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["link_id", "t", "col_idx", "o_zone_id", "d_zone_id", "proportion", "is_measured"])
        for (lid, t), lst in sorted(A.incidence.items()):
            for (ci, prop) in lst:
                col = case.columns[ci]
                w.writerow([lid, t, ci, col.o_zone_id, col.d_zone_id, prop,
                            int((lid, t) in A.measured_cells)])
    return path
