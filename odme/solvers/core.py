"""Unified ODME solver interface + four interchangeable solver versions.

All solvers share ONE input/output contract so they are swappable options:

    Problem(G, y, x0, [P, d_prior])   ->   solve(problem, ...) -> Result(x, iters, runtime, loss_hist)

where the linear operator G (m x n, scipy.sparse) maps the decision variable x (n,) to the
observations y (m,).  In the path-flow setting x = path/column flows, G = M A^T (sensors x paths);
in the dynamic setting the time-dependent 3rd-order incidence is FLATTENED (matricized) to a 2D
sparse G whose rows index (link, t) cells and columns index (path, tau) time-columns.

Versions:
  1. projected_gradient   (FTT / Bertsekas): x <- max(0, x - (1/L) G^T(Gx - y)),  L = sigma_max(G)^2
  2. gradient_deviation   (DTALite ODME.h):  bounded multiplicative MSA, step = 1/(k+2), |dx| <= bound*x
  3. multi_objective      (CGODME / HFN):    + OD-prior term + OD-total conservation
  4. low_rank             (compressed):      x = x0 + V_r z,  V_r = top-r right singular vecs of G
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import svds, eigsh


@dataclass
class Problem:
    G: "sp.spmatrix"          # m x n observation operator
    y: np.ndarray             # m observations
    x0: np.ndarray            # n prior/seed
    P: "sp.spmatrix" = None   # k x n  aggregate x -> OD (optional, for multi-objective / metrics)
    d_prior: np.ndarray = None
    name: str = ""


@dataclass
class Result:
    x: np.ndarray
    iters: int
    runtime_s: float
    loss_hist: list = field(default_factory=list)
    solver: str = ""
    extra: dict = field(default_factory=dict)


def _spectral_norm_sq(G):
    """sigma_max(G)^2 = largest eigenvalue of G^T G (the unified Lipschitz constant)."""
    try:
        return float(eigsh(G.T @ G, k=1, return_eigenvectors=False, which="LA")[0])
    except Exception:
        return float(svds(G, k=1, return_singular_vectors=False)[0] ** 2)


def _loss(G, x, y):
    return float(np.mean((G @ x - y) ** 2))


# ---------------------------------------------------------------- 1. projected gradient (Bertsekas)
def projected_gradient(p: Problem, max_iter=300, tol=1e-6):
    t0 = time.time()
    L = _spectral_norm_sq(p.G)
    lr = 1.0 / (L + 1e-12)                 # unified rule: step = 1 / Lipschitz
    x = p.x0.astype(float).copy(); hist = []
    for k in range(max_iter):
        g = p.G.T @ (p.G @ x - p.y)
        x = np.maximum(0.0, x - lr * g)    # projection onto x >= 0
        hist.append(_loss(p.G, x, p.y))
        if k > 1 and abs(hist[-2] - hist[-1]) <= tol * max(1.0, hist[-2]):
            break
    return Result(x, k + 1, time.time() - t0, hist, "projected_gradient")


# ---------------------------------------------------------------- 2. gradient deviation (DTALite)
def gradient_deviation(p: Problem, max_iter=300, tol=1e-6, bound=0.15):
    t0 = time.time()
    GT = p.G.T.tocsr()
    expo = np.asarray(abs(p.G).sum(axis=0)).ravel()
    x = p.x0.astype(float).copy(); hist = []
    for k in range(max_iter):
        rel = (p.G @ x - p.y) / np.maximum(np.abs(p.y), 1.0)   # scale-free relative residual
        step = 1.0 / (k + 2.0)                                 # MSA schedule
        upd = step * (GT @ rel) / np.maximum(expo, 1.0) * np.maximum(x, 1.0)
        upd = np.clip(upd, -bound * np.maximum(x, 1.0), bound * np.maximum(x, 1.0))
        x = np.maximum(0.0, x - upd)
        hist.append(_loss(p.G, x, p.y))
        if k > 5 and abs(hist[-2] - hist[-1]) <= tol * max(1.0, hist[-2]):
            break
    return Result(x, k + 1, time.time() - t0, hist, "gradient_deviation")


# ---------------------------------------------------------------- 3. multi-objective (CGODME / HFN)
def multi_objective(p: Problem, max_iter=300, tol=1e-6, lam_od=0.5, conserve=True):
    t0 = time.time()
    L = _spectral_norm_sq(p.G) + (lam_od if p.P is not None else 0.0)
    lr = 1.0 / (L + 1e-12)
    x = p.x0.astype(float).copy(); hist = []
    d_prior = p.d_prior if p.d_prior is not None else (p.P @ p.x0 if p.P is not None else None)
    for k in range(max_iter):
        g = p.G.T @ (p.G @ x - p.y)
        if p.P is not None and lam_od:
            g = g + lam_od * (p.P.T @ (p.P @ x - d_prior))
        x = np.maximum(0.0, x - lr * g)
        if conserve and p.P is not None:                      # OD-total conservation (spillover-style)
            d = p.P @ x
            scale = np.where(d > 1e-9, d_prior / np.maximum(d, 1e-9), 1.0)
            x = x * np.asarray(p.P.T @ scale).ravel()
        hist.append(_loss(p.G, x, p.y))
        if k > 5 and abs(hist[-2] - hist[-1]) <= tol * max(1.0, hist[-2]):
            break
    return Result(x, k + 1, time.time() - t0, hist, "multi_objective")


# ---------------------------------------------------------------- 4. low-rank (compressed)
def low_rank(p: Problem, rank=80, max_iter=1, tol=1e-6):
    """Restrict the correction to the r observable directions: x = x0 + V_r z.
    Solve the reduced least squares in r dims via the SVD G ~ U_r S_r V_r^T (one shot)."""
    t0 = time.time()
    r = min(rank, min(p.G.shape) - 1)
    U, S, Vt = svds(p.G.asfptype(), k=r)           # ascending singular values
    r0 = p.y - p.G @ p.x0                            # residual to explain
    # z* = V_r (1/S) U_r^T r0  (pseudo-inverse in the rank-r subspace)
    z = Vt.T @ ((U.T @ r0) / np.maximum(S, 1e-9))
    x = np.maximum(0.0, p.x0 + z)
    hist = [_loss(p.G, x, p.y)]
    return Result(x, 1, time.time() - t0, hist, f"low_rank(r={r})",
                  extra={"rank": r, "sigma_min": float(S.min()), "sigma_max": float(S.max())})


SOLVERS = {
    "projected_gradient": projected_gradient,
    "gradient_deviation": gradient_deviation,
    "multi_objective": multi_objective,
    "low_rank": low_rank,
}
