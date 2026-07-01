"""Bounded low-rank ODME -- ODME as a small, interpretable refinement, NOT demand reconstruction.

The OD adjustment is a MULTIPLICATIVE correction surface:

    Q_new(i,j) = theta_ij * Q_base(i,j),   log theta_ij = mu + O_i + D_j (+ small rank-R interaction)

with a HARD per-pair bound  (1 - bound) <= theta_ij <= (1 + bound)  (default +-10%), so origin production
P_i = sum_j Q_ij and destination attraction A_j = sum_i Q_ij also stay within +-bound. Fitting counts is
constrained to a low-rank origin/destination structure, which keeps the adjustment interpretable and avoids
cell-by-cell overfitting.

Matrix-free: pass an assignment operator's `matvec` (OD->link) and `rmatvec` (link->OD). A count-incidence
matrix `S` (n_counts x L, e.g. screenline membership) maps link volumes to observed count groups.

Design rule: ODME should be a small, bounded, low-rank correction to an *already reasonable* base OD/loading.
If the counts cannot be matched within +-bound, that is a DIAGNOSTIC signal to fix the base demand, period
factors, count matching, or assignment loading upstream -- not to widen the bound.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np


@dataclass
class ODMEResult:
    d: np.ndarray                 # adjusted OD vector
    theta: np.ndarray             # per-OD adjustment ratio d / d0
    fit: dict                     # count fit after adjustment (R2, WMAPE, ratio)
    diagnostics: dict = field(default_factory=dict)


def _fit(model, y):
    m = y > 0; mo = model[m]; oo = y[m]
    if mo.size == 0 or oo.sum() == 0:
        return dict(R2=float("nan"), WMAPE=float("nan"), ratio=float("nan"))
    return dict(R2=float(1 - ((mo - oo) ** 2).sum() / (((oo - oo.mean()) ** 2).sum() + 1e-12)),
                WMAPE=float(np.abs(mo - oo).sum() / oo.sum()), ratio=float(mo.sum() / oo.sum()))


def _explained_by_od(theta, w, oi, di, n_o, n_d, iters=25):
    """weighted variance of log(theta) explained by an additive origin+destination model (low-rank check)."""
    L = np.log(np.clip(theta, 1e-3, 1e3)); mu = np.average(L, weights=w)
    O = np.zeros(n_o); D = np.zeros(n_d)
    swo = np.bincount(oi, w, n_o) + 1e-9; swd = np.bincount(di, w, n_d) + 1e-9
    for _ in range(iters):
        O = np.bincount(oi, w * (L - mu - D[di]), n_o) / swo
        D = np.bincount(di, w * (L - mu - O[oi]), n_d) / swd
        mu = np.average(L - O[oi] - D[di], weights=w)
    sstot = np.sum(w * (L - np.average(L, weights=w)) ** 2) + 1e-12
    return float(1 - np.sum(w * (L - (mu + O[oi] + D[di])) ** 2) / sstot)


def _totals_range(d0, d, idx, n, bound):
    b = np.bincount(idx, d0, n); a = np.bincount(idx, d, n); m = b > 0
    r = a[m] / b[m]
    out = float(100 * np.mean((r < 1 - bound - 1e-6) | (r > 1 + bound + 1e-6)))
    return float(r.min()), float(r.max()), out


def bounded_lowrank_odme(matvec, rmatvec, d0, od_origin, od_dest, S, y, *, bound=0.10, rank=2,
                         rho=8.0, rho_uv=40.0, calibrate=None, maxiter=300, observable=None):
    """Bounded low-rank ODME.

    matvec(d)->link volumes (L,);  rmatvec(r)->OD (n_od,);  d0: base OD (n_od,);
    od_origin/od_dest: integer origin/destination-zone index per OD (n_od,);
    S: (n_counts, L) sparse count-incidence;  y: (n_counts,) observed count totals;
    bound: hard +-fraction on theta (0.10 = +-10%);  rank: low-rank interaction terms;
    calibrate: optional per-link factor c (L,) so calibrated loading c*matvec(d0) matches the base counts.

    Returns ODMEResult (V2, bounded). Use `three_version_comparison` for V0/V1/V2.
    """
    from scipy.optimize import minimize
    d0 = np.asarray(d0, float); n_od = d0.size
    oi = np.asarray(od_origin); di = np.asarray(od_dest)
    n_o = int(oi.max()) + 1; n_d = int(di.max()) + 1
    c = np.ones(S.shape[1]) if calibrate is None else np.asarray(calibrate, float)

    def A(d):  return c * matvec(d)
    def At(r): return rmatvec(c * r)

    sU = 1 + n_o + n_d; sV = sU + n_o * rank

    def unpack(p):
        return (p[0], p[1:1 + n_o], p[1 + n_o:1 + n_o + n_d],
                p[sU:sV].reshape(n_o, rank), p[sV:].reshape(n_d, rank))

    def expo(mu, O, D, U, V):
        e = mu + O[oi] + D[di]
        return e + np.einsum("ar,ar->a", U[oi], V[di]) if rank else e

    def objgrad(p):
        mu, O, D, U, V = unpack(p)
        e = np.clip(expo(mu, O, D, U, V), -4, 4); d = d0 * np.exp(e)
        r = S @ A(d) - y
        loss = 0.5 * float(r @ r) + 0.5 * rho * (O @ O + D @ D)
        if rank:
            loss += 0.5 * rho_uv * (U.ravel() @ U.ravel() + V.ravel() @ V.ravel())
        ge = At(S.T @ r) * d
        grad = np.concatenate([[ge.sum()], np.bincount(oi, ge, n_o) + rho * O,
                               np.bincount(di, ge, n_d) + rho * D])
        if rank:
            gU = np.zeros((n_o, rank)); gV = np.zeros((n_d, rank))
            for k in range(rank):
                np.add.at(gU[:, k], oi, ge * V[di, k]); np.add.at(gV[:, k], di, ge * U[oi, k])
            grad = np.concatenate([grad, (gU + rho_uv * U).ravel(), (gV + rho_uv * V).ravel()])
        return loss, grad

    res = minimize(objgrad, np.zeros(sV + n_d * rank), jac=True, method="L-BFGS-B",
                   options=dict(maxiter=maxiter, maxfun=maxiter + 100, ftol=1e-11))
    mu, O, D, U, V = unpack(res.x)
    theta = np.exp(np.clip(expo(mu, O, D, U, V), -4, 4))
    clipped = 0
    if bound is not None:
        tc = np.clip(theta, 1 - bound, 1 + bound); clipped = int(np.sum(np.abs(theta - tc) > 1e-9)); theta = tc
    # OBSERVABILITY GATE: OD pairs that cross no sensor (observable[k]==False) are NOT adjusted -> theta=1.
    if observable is not None:
        theta = np.where(np.asarray(observable, bool), theta, 1.0)
    d = d0 * theta
    fit = _fit(S @ A(d), y)
    pos = d0 > 0
    o_lo, o_hi, o_out = _totals_range(d0, d, oi, n_o, bound if bound else 1e9)
    d_lo, d_hi, d_out = _totals_range(d0, d, di, n_d, bound if bound else 1e9)
    diag = dict(median_theta=float(np.median(theta[pos])),
                p5=float(np.percentile(theta[pos], 5)), p95=float(np.percentile(theta[pos], 95)),
                max_theta=float(theta[pos].max()), min_theta=float(theta[pos].min()),
                pct_outside=float(100 * np.mean((theta[pos] < 1 - (bound or 1) - 1e-6) |
                                                (theta[pos] > 1 + (bound or 1) + 1e-6))),
                origin_ratio_range=(o_lo, o_hi), origin_pct_outside=o_out,
                dest_ratio_range=(d_lo, d_hi), dest_pct_outside=d_out,
                od_explained_pct=100 * _explained_by_od(theta[pos], d0[pos], oi[pos], di[pos], n_o, n_d),
                total_change_pct=float(100 * (d.sum() / d0.sum() - 1)), clipped_pairs=clipped)
    return ODMEResult(d=d, theta=theta, fit=fit, diagnostics=diag)


def three_version_comparison(matvec, rmatvec, d0, od_origin, od_dest, S, y, *, bound=0.10, rank=2,
                             calibrate=None):
    """V0 (no ODME), V1 (unconstrained low-rank), V2 (bounded +-bound). Returns list of dicts."""
    d0 = np.asarray(d0, float)
    c = np.ones(S.shape[1]) if calibrate is None else np.asarray(calibrate, float)
    v0_fit = _fit(S @ (c * matvec(d0)), y)
    rows = [dict(version="V0_no_ODME", **v0_fit, median_theta=1.0, pct_outside=0.0,
                 origin_pct_outside=0.0, dest_pct_outside=0.0, total_change_pct=0.0)]
    v1 = bounded_lowrank_odme(matvec, rmatvec, d0, od_origin, od_dest, S, y, bound=None, rank=rank,
                              rho=2.0, calibrate=calibrate)
    rows.append(dict(version="V1_unconstrained", **v1.fit, median_theta=v1.diagnostics["median_theta"],
                     pct_outside=_pct_out(v1.theta, d0, bound),
                     origin_pct_outside=v1.diagnostics["origin_pct_outside"],
                     dest_pct_outside=v1.diagnostics["dest_pct_outside"],
                     total_change_pct=v1.diagnostics["total_change_pct"]))
    v2 = bounded_lowrank_odme(matvec, rmatvec, d0, od_origin, od_dest, S, y, bound=bound, rank=rank,
                              rho=8.0, calibrate=calibrate)
    rows.append(dict(version="V2_bounded", **v2.fit, median_theta=v2.diagnostics["median_theta"],
                     pct_outside=v2.diagnostics["pct_outside"],
                     origin_pct_outside=v2.diagnostics["origin_pct_outside"],
                     dest_pct_outside=v2.diagnostics["dest_pct_outside"],
                     total_change_pct=v2.diagnostics["total_change_pct"],
                     od_explained_pct=v2.diagnostics["od_explained_pct"]))
    return rows, v2


def _pct_out(theta, d0, bound):
    pos = d0 > 0; t = theta[pos]
    return float(100 * np.mean((t < 1 - bound - 1e-6) | (t > 1 + bound + 1e-6)))


def observability_mask(path_link, path_od, sensor_link_cols, n_od):
    """Per-OD sensor coverage for the observability gate (twin of the DTALite/TAPLite gate).

    path_link: sparse (n_path x L) path-link incidence; path_od: (n_path,) path->OD index;
    sensor_link_cols: iterable of link column indices that carry an observed count (sensors);
    returns (num_sensor_points_passed (n_od,), adjustable (n_od,) bool).

    RULE: an OD pair whose paths cross NO sensor point is unobservable -- it must NOT be adjusted
    (pass the returned `adjustable` mask as `observable=` to bounded_lowrank_odme to freeze theta=1).
    """
    import scipy.sparse as sp
    cols = list(sensor_link_cols)
    sub = path_link[:, cols]
    P = path_link.shape[0]
    od_sel = sp.csr_matrix((np.ones(P), (np.asarray(path_od), np.arange(P))), shape=(n_od, P))
    od_sensor = (od_sel @ sub).tocsr()
    od_sensor.data[:] = 1.0                                   # binarize -> distinct sensor links
    num = np.asarray(od_sensor.sum(axis=1)).ravel().astype(int)
    return num, num > 0
