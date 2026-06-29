"""Matrix-free sparse assignment operator A = M Δ R — never materialize dense A.

Built from a column file (route_assignment.csv / columns.csv) + link.csv. Stores only the
sparse path-link incidence Δ (CSR), the path→OD index, and the path share R. Provides:

    matvec(d)  -> x   link flow      x = Δᵀ (share ⊙ d[path_od])      ( = Δ R d )
    rmatvec(r) -> g   OD gradient    g = Σ_p share_p (Δ_p · r)         ( = (Δ R)ᵀ r )
    aggregate(x)      VMT, VHT, counts, screenline/corridor totals     ( = M x )

Exposed as a scipy.sparse.linalg.LinearOperator so any large-scale solver can use it without
ever forming the |L|×|OD| matrix.  For ARC: |L|×|OD| ≈ 146k×1.4M ≈ 1.6 TB dense — never built.
"""
from __future__ import annotations

import csv
import time

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import LinearOperator


def _ids(s):
    return [int(float(x)) for x in str(s).replace(",", ";").split(";") if str(x).strip()]


class AssignmentOperator:
    def __init__(self, path_link, path_od, share, od_keys, link_ids, length, fftt, d0):
        self.path_link = path_link.tocsr()      # P x L  (Δ)
        self.path_link_T = self.path_link.T.tocsr()
        self.path_od = path_od                   # P -> od index
        self.share = share                       # P route shares
        self.od_keys = od_keys                   # od index -> (o,d)
        self.link_ids = link_ids
        self.length = length                     # L
        self.fftt = fftt                         # L (free-flow time, hours)
        self.d0 = d0                             # base OD demand (|OD|)
        self.P, self.L = self.path_link.shape
        self.n_od = len(od_keys)

    # ---- forward: d -> link flow ----
    def matvec(self, d):
        path_flow = self.share * d[self.path_od]
        return self.path_link_T @ path_flow

    # ---- adjoint: link residual -> OD gradient ----
    def rmatvec(self, r):
        path_resid = self.path_link @ r
        return np.bincount(self.path_od, weights=self.share * path_resid, minlength=self.n_od)

    def as_linear_operator(self):
        return LinearOperator((self.L, self.n_od), matvec=self.matvec, rmatvec=self.rmatvec)

    # ---- calibration-visible aggregation M x ----
    def aggregate(self, x):
        return dict(VMT=float(x @ self.length), VHT=float(x @ self.fftt), total=float(x.sum()))

    def grouped(self, x, M):
        """y = M x for any link->group aggregation M (counts / screenline / corridor)."""
        return M @ x

    @property
    def nnz(self):
        return self.path_link.nnz

    def memory_mb(self):
        m = self.path_link
        return (m.data.nbytes + m.indices.nbytes + m.indptr.nbytes
                + self.path_od.nbytes + self.share.nbytes) / 1e6


def build_operator(columns_csv, link_csv):
    """Build the exact sparse operator from a column file + link.csv."""
    # links
    link_ids, length, fftt, lix = [], [], [], {}
    with open(link_csv, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            lid = int(float(r["link_id"])); lix[lid] = len(link_ids); link_ids.append(lid)
            ln = float(r.get("vdf_length_mi") or r.get("length") or 0) or 1.0
            if ln > 1000:
                ln /= 1609.344
            vf = float(r.get("vdf_free_speed_mph") or r.get("free_speed") or 30) or 30
            length.append(ln); fftt.append(ln / max(vf, 1.0))
    length = np.array(length); fftt = np.array(fftt); L = len(link_ids)

    # paths
    rows, cols, od_of, vol = [], [], [], []
    odx = {}
    with open(columns_csv, newline="", encoding="utf-8-sig") as f:
        for p, r in enumerate(csv.DictReader(f)):
            seq = r.get("link_id_sequence") or r.get("link_sequence") or r.get("link_ids") or ""
            if not str(seq).strip():
                continue
            od = (r.get("o_zone_id"), r.get("d_zone_id"))
            oi = odx.setdefault(od, len(odx))
            od_of.append(oi); vol.append(float(r.get("volume") or 0))
            for a in _ids(seq):
                if a in lix:
                    rows.append(len(od_of) - 1); cols.append(lix[a])
    P = len(od_of)
    path_link = sp.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(P, L))
    od_of = np.array(od_of); vol = np.array(vol)
    od_keys = [None] * len(odx)
    for od, i in odx.items():
        od_keys[i] = od
    # OD totals + path shares
    d0 = np.bincount(od_of, weights=vol, minlength=len(odx))
    share = np.where(d0[od_of] > 1e-9, vol / np.maximum(d0[od_of], 1e-9), 0.0)
    return AssignmentOperator(path_link, od_of, share, od_keys, link_ids, length, fftt, d0)
