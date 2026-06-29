"""OD-basis compression (Option 3) — interpretable d = U z, not blind SVD.

Reduce the ODME unknowns from |OD| (millions) to a few thousand INTERPRETABLE latent variables:
district/county pairs, distance bands, etc. U maps the latent z to the full OD vector using a
prior within-block split, so the ODME kernel solves on z (block-level corrections), which is
well-posed and far cheaper, while the full link network response is preserved.

Composes with the matrix-free operator: x = A (U z) = (Δ R) U z, gradient = Uᵀ (Δ R)ᵀ r.
"""
from __future__ import annotations

import csv

import numpy as np
import scipy.sparse as sp


def spatial_districts(op, node_csv, K=30):
    """Cluster zones by coordinate into ~K districts (grid bins); return zone->district array."""
    coord = {}
    for r in csv.DictReader(open(node_csv, encoding="utf-8-sig")):
        z = int(float(r.get("zone_id") or 0))
        if z >= 1:
            coord[z] = (float(r["x_coord"]), float(r["y_coord"]))
    if not coord:
        return {}
    xs = np.array([c[0] for c in coord.values()]); ys = np.array([c[1] for c in coord.values()])
    nb = max(1, int(round(K ** 0.5)))
    xb = np.linspace(xs.min(), xs.max(), nb + 1); yb = np.linspace(ys.min(), ys.max(), nb + 1)
    z2d = {}
    for z, (x, y) in coord.items():
        i = min(nb - 1, np.searchsorted(xb, x) - 1); j = min(nb - 1, np.searchsorted(yb, y) - 1)
        z2d[z] = i * nb + j
    return z2d


def build_basis(op, z2d):
    """U (|OD| x |blocks|): block = (district_o, district_d); U[od,block] = prior share d0/blocktot."""
    block_of = np.full(op.n_od, -1)
    for oi, od in enumerate(op.od_keys):
        try:
            o = int(float(od[0])); d = int(float(od[1]))
        except (TypeError, ValueError):
            continue
        do = z2d.get(o); dd = z2d.get(d)
        if do is None or dd is None:
            continue
        block_of[oi] = do * 100000 + dd
    # map block ids to contiguous indices
    uniq = {b: i for i, b in enumerate(sorted(set(block_of[block_of >= 0])))}
    cols = np.array([uniq.get(b, -1) for b in block_of])
    valid = cols >= 0
    blk_tot = np.bincount(cols[valid], weights=op.d0[valid], minlength=len(uniq))
    share = np.where(blk_tot[cols[valid]] > 1e-9, op.d0[valid] / blk_tot[cols[valid]], 0.0)
    U = sp.csr_matrix((share, (np.where(valid)[0], cols[valid])), shape=(op.n_od, len(uniq)))
    return U


def reduced_matvec(op, U):
    """Return (matvec_z, rmatvec_z) for the basis-reduced operator A U."""
    def mv(z):
        return op.matvec(np.asarray(U @ z).ravel())
    def rmv(r):
        return np.asarray(U.T @ op.rmatvec(r)).ravel()
    return mv, rmv
