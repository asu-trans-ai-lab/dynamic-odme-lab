"""Adapter: build A entries from route columns (TAPLite or Path4GMNS route_assignment.csv).

Emits the uniform stream (link_id, t, col_idx, proportion). At T=1, t=0 and proportion=1.
For T>1, a column is spread across (link, t) cells using entry_times_min (when available).
"""
from __future__ import annotations

from ...model import CaseData


def entries(case: CaseData):
    T = case.time_grid.T
    if T == 1:
        for ci, col in enumerate(case.columns):
            for lid in col.link_ids:
                yield (lid, 0, ci, 1.0)
        return
    # T>1: place each link of the column in time.
    #   - with entry_times_min: use the per-link arrival bin (true dynamic, travel-time offset)
    #   - else: the whole column sits in its departure bin tau (phi-only spreading)
    interval = case.time_grid.interval_minutes
    start_min = case.time_grid.start_hour * 60.0
    for ci, col in enumerate(case.columns):
        et = col.entry_times_min
        for k, lid in enumerate(col.link_ids):
            if et is not None and k < len(et):
                t = int((et[k] - start_min) // interval)
            else:
                t = col.tau
            t = max(0, min(T - 1, t))
            yield (lid, t, ci, 1.0)
