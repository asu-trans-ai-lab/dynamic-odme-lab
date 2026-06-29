"""HFN multi-source ODME — does adding OD-layer data (F2) break the count-only OD floor?

From Wu/Guo/Xian/Zhou 2018 (TR-C), the Hierarchical Flow Network:
  alpha --g--> q --rho--> f --delta--> v ,   loss = l1*F1(alpha) + l2*F2(gamma) + l3*F3(v)
Each data source enters at its layer; the others regularize. Counts (F3, link layer) cannot
see per-OD error; mobile/OD-split data (F2, OD layer) can.

Experiment (on Chicago Sketch, the random-per-OD +/-10% case from CHICAGO_QVDF_FINDINGS):
  observe 50% of links (F3) AND a fraction q% of OD pairs' true volume (F2, the new source);
  sweep q% and watch OD MAPE fall below the count-only ~5% floor.

Run:  python -m odme.examples.hfn_multisource
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp

from .chicago_qvdf_sensitivity import load_chicago, base_case, vmt_vht, _metrics


def _agg(P, h):
    return np.asarray(P @ h).ravel()


def odme_hfn(net, sensors, y_obs, h0, P, PT, d_prior, d_true, obs_od_mask,
             w_count=1.0, w_od=0.0, iters=80, bound=0.15):
    Ds = net["Delta"][sensors, :].tocsr(); DsT = Ds.T.tocsr()
    expo = np.asarray(Ds.sum(axis=0)).ravel()
    # F2 target = TRUE od volume on observed OD pairs (the mobile-data source), prior elsewhere
    d_target = np.where(obs_od_mask, d_true, d_prior)
    x0 = net["Delta"] @ h0
    s_count = max(1.0, np.mean((x0[sensors] - y_obs) ** 2))
    s_od = max(1.0, np.mean((_agg(P, h0) - d_target) ** 2))
    h = h0.copy()
    for k in range(iters):
        # F3 link-count gradient
        g = w_count * (DsT @ ((Ds @ h - y_obs) / np.maximum(y_obs, 1.0))) / s_count
        if w_od > 0:
            d = _agg(P, h)
            # F2 only on observed OD pairs
            err = np.where(obs_od_mask, d - d_target, 0.0)
            g = g + w_od * (PT @ err) / s_od
        upd = 0.5 * g / np.maximum(expo, 1.0) * np.maximum(h, 1.0)
        upd = np.clip(upd, -bound * np.maximum(h, 1.0), bound * np.maximum(h, 1.0))
        h = np.maximum(0.0, h - upd)
    return h


def main():
    print("loading Chicago Sketch ...")
    net = load_chicago()
    base = base_case(net)
    real = base["real"]; x_true = base["x"]
    od_of = net["od_of"]; od_keys = list(set(od_of)); kix = {k: i for i, k in enumerate(od_keys)}
    rows = [kix[od] for od in od_of]
    P = sp.csr_matrix((np.ones(len(rows)), (rows, range(len(od_of)))), shape=(len(od_keys), len(od_of)))
    PT = P.T.tocsr()
    d_true = _agg(P, net["h_true"])
    vmt_true, _ = vmt_vht(x_true, net["length"], net["vf"], net["alpha"], net["beta"], net["cap"])

    rng = np.random.default_rng(7)
    cand = np.where(real & (x_true > 50))[0]
    sensors = rng.choice(cand, size=int(0.50 * len(cand)), replace=False)
    held = np.setdiff1d(cand, sensors)
    y_obs = x_true[sensors]
    fac = 1 + rng.uniform(-0.10, 0.10, size=len(od_keys))   # link-invisible per-OD error
    d_prior = d_true * fac
    h0 = net["h_true"] * np.array([fac[kix[od]] for od in od_of])

    print(f"setup: 50% link sensors (F3), random per-OD +/-10% seed.  seed OD MAPE = "
          f"{_metrics(d_true, d_prior)[1]:.1f}% (the count-only floor)\n")
    print(f"{'OD-data %':>9} {'held MAPE':>9} {'OD R2':>7} {'OD MAPE':>8} {'dVMT%':>7}")
    for od_frac in (0.0, 0.10, 0.25, 0.50, 1.0):
        n_od = int(od_frac * len(od_keys))
        obs_idx = rng.choice(len(od_keys), size=n_od, replace=False) if n_od else np.array([], dtype=int)
        mask = np.zeros(len(od_keys), dtype=bool); mask[obs_idx] = True
        w_od = 0.0 if od_frac == 0.0 else 0.8
        h = odme_hfn(net, sensors, y_obs, h0, P, PT, d_prior, d_true, mask, w_count=1.0, w_od=w_od)
        x = net["Delta"] @ h; d = _agg(P, h)
        _, mape_h = _metrics(x_true[held], x[held])
        r2_od, mape_od = _metrics(d_true, d)
        vmt, _ = vmt_vht(x, net["length"], net["vf"], net["alpha"], net["beta"], net["cap"])
        tag = "count-only" if od_frac == 0 else f"+{int(od_frac*100)}% OD"
        print(f"{tag:>9} {mape_h:>8.1f}% {r2_od:>7.3f} {mape_od:>7.1f}% {100*(vmt-vmt_true)/vmt_true:>+6.1f}")
    print("\n-> adding OD-layer (F2) observations breaks the count-only floor:")
    print("   link counts (F3) leave per-OD error ~5%; observing OD splits directly drives OD MAPE down.")


if __name__ == "__main__":
    main()
