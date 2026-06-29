"""Compression of the assignment operator — by ACTIVE PATH PRUNING (Option 2).

Keep only meaningful paths per OD (top-K / share threshold / cumulative-flow), renormalize the
remaining shares, and rebuild the sparse operator. Lossless baseline = keep all paths.
Error is measured downstream by calibration-visible metrics (evaluate.py), not matrix norm.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np
import scipy.sparse as sp

from .assignment_operator import AssignmentOperator


def prune_paths(op: AssignmentOperator, top_k=None, share_min=None, cum_flow=None):
    """Return a compressed AssignmentOperator keeping a subset of paths per OD."""
    by_od = defaultdict(list)
    for p in range(op.P):
        by_od[op.path_od[p]].append(p)

    keep = []
    for od, paths in by_od.items():
        paths = sorted(paths, key=lambda p: -op.share[p])     # by descending share
        if top_k is not None:
            paths = paths[:top_k]
        if share_min is not None:
            paths = [p for p in paths if op.share[p] >= share_min]
        if cum_flow is not None:
            kept, c = [], 0.0
            for p in paths:
                kept.append(p); c += op.share[p]
                if c >= cum_flow:
                    break
            paths = kept
        keep.extend(paths if paths else by_od[od][:1])         # always keep >=1 path/OD

    keep = np.array(sorted(keep))
    sub = op.path_link[keep]
    od_sub = op.path_od[keep]
    sh = op.share[keep].copy()
    # renormalize shares within each OD so they sum to 1 again
    denom = np.bincount(od_sub, weights=sh, minlength=op.n_od)
    sh = np.where(denom[od_sub] > 1e-9, sh / np.maximum(denom[od_sub], 1e-9), sh)
    return AssignmentOperator(sub, od_sub, sh, op.od_keys, op.link_ids, op.length, op.fftt, op.d0)
