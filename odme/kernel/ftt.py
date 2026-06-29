"""Flow-Through-Tensor (FTT) / HFN solver with EXPLICIT A and B matrices + adjoint backprop.

Follows flow_through_tensor.tex exactly:
  matrices   A = A_{P,L} (path->link incidence, |P|x|L|, fixed topology)
             B = B_{OD,P} (OD->path proportion, |OD|x|P|, route choice)
  forward    f_P = B^T f_OD ;  f_L = A^T f_P ;  t_L = phi(f_L) ;  t_P = A t_L ;  t_OD = B t_P
  backward   d f_L / d f_OD = A^T B^T   (adjoint pass; chain rule lines 652-663 of the tex)

Multi-source ODME (HFN, Wu et al. 2018): minimize
  L = l3 * ||M f_L - y_count||^2      (sensor / link layer  F3)
    + l2 * ||C_od f_OD - y_od||^2     (mobile / OD layer     F2)
    + l1 * ||C_o  f_OD - y_gen||^2    (survey / origin layer F1)
with decision variable f_OD (or path flow f_P), solved by gradient projection (Bertsekas).
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp

from .matrices import build_kernel


class FTT:
    """Explicit A/B Flow-Through-Tensor model built from a tiny-panel-style case."""

    def __init__(self, case_dir):
        K = build_kernel(case_dir)            # gives R(PxK)=B^T, Delta(AxP)=A^T, M(SxA)
        self.od_ids = K.od_ids
        self.link_ids = K.link_ids
        self.B = sp.csr_matrix(K.R.T)         # B_{OD,P}  (|OD| x |P|)
        self.A = sp.csr_matrix(K.Delta.T)     # A_{P,L}   (|P|  x |L|)
        self.M = sp.csr_matrix(K.M)           # sensor->link (S x L)
        self.d_seed = K.d_seed                # f_OD prior

    # ---- forward pass (states) ----
    def forward(self, f_OD, bpr=None):
        f_P = self.B.T @ f_OD                 # f_P = B^T f_OD
        f_L = self.A.T @ f_P                  # f_L = A^T f_P
        out = dict(f_P=f_P, f_L=f_L)
        if bpr is not None:
            voc = np.where(bpr["cap"] > 0, f_L / bpr["cap"], 0.0)
            t_L = bpr["t0"] * (1 + bpr["alpha"] * voc ** bpr["beta"])
            t_P = self.A @ t_L                # t_P = A t_L
            t_OD = self.B @ t_P               # t_OD = B t_P
            out.update(t_L=t_L, t_P=t_P, t_OD=t_OD)
        return out

    # ---- backward pass (adjoint) for the count term d/df_OD ||M f_L - y||^2 ----
    def grad_count(self, f_OD, y_count):
        f_L = self.A.T @ (self.B.T @ f_OD)
        resid = self.M @ f_L - y_count                       # (S,)
        # adjoint: A^T B^T mapped back: dL/df_OD = B A M^T resid
        return self.B @ (self.A @ (self.M.T @ resid))        # (|OD|,)

    def jacobian_link_od(self):
        """The FTT operator d f_L / d f_OD = A^T B^T  (the assignment-visible map G)."""
        return (self.A.T @ self.B.T)

    # ---- multi-source ODME by gradient projection (Bertsekas) ----
    def solve(self, y_count, y_od=None, C_od=None, y_gen=None, C_o=None,
              l3=1.0, l2=0.0, l1=0.0, iters=300, lr=None):
        d = self.d_seed.astype(float).copy()
        MG = self.M @ self.jacobian_link_od()                # S x |OD|
        if lr is None:
            # Lipschitz of the full quadratic: L = l3||MG||^2 + l2||C_od||^2 + l1||C_o||^2
            Lip = l3 * np.linalg.norm(MG.toarray(), 2) ** 2
            if l2 and C_od is not None:
                Lip += l2 * np.linalg.norm(C_od, 2) ** 2
            if l1 and C_o is not None:
                Lip += l1 * np.linalg.norm(C_o, 2) ** 2
            lr = 1.0 / (Lip + 1e-9)
        hist = []
        for k in range(iters):
            g = l3 * self.grad_count(d, y_count)
            if l2 and y_od is not None:
                g = g + l2 * (C_od.T @ (C_od @ d - y_od))
            if l1 and y_gen is not None:
                g = g + l1 * (C_o.T @ (C_o @ d - y_gen))
            d = np.maximum(0.0, d - lr * g)                  # projected gradient step (d>=0)
            f_L = self.A.T @ (self.B.T @ d)
            hist.append(float(np.mean((self.M @ f_L - y_count) ** 2)))
        return d, hist
