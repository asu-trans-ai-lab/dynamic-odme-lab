"""CGODME-style multi-objective ODME on Chicago Sketch — adopting the Tucson CGODME formulation.

Learned from `05_Tucson_planning_network/CGODME with Tucson case`:
  loss = count + VMT + OD-prior + zonal, each normalized by its initial error (scaled_mse),
  decision = path flow with OD-total conservation, positivity.

This compares COUNT-ONLY vs CGODME-STYLE (count + VMT-anchor + OD-prior-anchor + conservation)
on the hard random-per-OD ±10% case, to see whether the extra reasonableness terms help or just
keep the solution physical.

Run:  python -m odme.examples.cgodme_style
"""
from __future__ import annotations

import numpy as np

from .chicago_qvdf_sensitivity import load_chicago, base_case, vmt_vht, _metrics


def _od_aggregate(h, od_of, od_keys, kix):
    d = np.zeros(len(od_keys))
    for j, od in enumerate(od_of):
        d[kix[od]] += h[j]
    return d


def run_variant(net, base, sensors, y_obs, h0, od_of, od_keys, kix, d_prior,
                vmt_target, mode, iters=80):
    """mode in {'count', 'cgodme'}. Bounded gradient with scaled multi-objective terms."""
    import scipy.sparse as sp
    Ds = net["Delta"][sensors, :].tocsr(); DsT = Ds.T.tocsr()
    expo = np.asarray(Ds.sum(axis=0)).ravel()
    L = net["length"]
    # OD aggregation operator P (od x path) as sparse for the OD-prior gradient
    rows = [kix[od] for od in od_of]; colsi = list(range(len(od_of)))
    P = sp.csr_matrix((np.ones(len(rows)), (rows, colsi)), shape=(len(od_keys), len(od_of)))
    PT = P.T.tocsr()

    # initial-error scales (scaled_mse): normalize each term by its seed error
    x0 = net["Delta"] @ h0
    s_count = max(1.0, np.mean((x0[sensors] - y_obs) ** 2))
    d0 = _od_aggregate(h0, od_of, od_keys, kix)
    s_od = max(1.0, np.mean((d0 - d_prior) ** 2))
    vmt0, _ = vmt_vht(x0, L, net["vf"], net["alpha"], net["beta"], net["cap"])
    s_vmt = max(1.0, (vmt0 - vmt_target) ** 2)

    w_count, w_od, w_vmt = (1.0, 0.0, 0.0) if mode == "count" else (1.0, 0.6, 0.4)
    h = h0.copy(); bound = 0.15
    for k in range(iters):
        x = net["Delta"] @ h
        # count gradient (relative, scaled)
        rc = (Ds @ h - y_obs)
        g_count = DsT @ (rc / np.maximum(y_obs, 1.0)) / s_count
        g = w_count * g_count
        if mode == "cgodme":
            d = P @ h
            g_od = PT @ ((d - d_prior)) / s_od
            vmt = float((x * L).sum())
            g_vmt = (net["Delta"].T @ L) * (2 * (vmt - vmt_target)) / s_vmt
            g = g + w_od * g_od + w_vmt * g_vmt
        upd = 0.5 * g / np.maximum(expo, 1.0) * np.maximum(h, 1.0)
        upd = np.clip(upd, -bound * np.maximum(h, 1.0), bound * np.maximum(h, 1.0))
        h = np.maximum(0.0, h - upd)
        if mode == "cgodme":
            # OD-total conservation: renormalize each OD's paths to the prior total
            d = P @ h
            scale = np.where(d > 1e-9, d_prior / np.maximum(d, 1e-9), 1.0)
            h = h * np.asarray(PT @ scale).ravel()
    return h


def main():
    print("loading Chicago Sketch ...")
    net = load_chicago()
    base = base_case(net)
    real = base["real"]; x_true = base["x"]
    od_of = net["od_of"]; od_keys = list(set(od_of)); kix = {k: i for i, k in enumerate(od_keys)}
    d_true = _od_aggregate(net["h_true"], od_of, od_keys, kix)
    vmt_true, vht_true = vmt_vht(x_true, net["length"], net["vf"], net["alpha"], net["beta"], net["cap"])

    rng = np.random.default_rng(7)
    cand = np.where(real & (x_true > 50))[0]
    sensors = rng.choice(cand, size=int(0.50 * len(cand)), replace=False)
    held = np.setdiff1d(cand, sensors)
    y_obs = x_true[sensors]

    # random per-OD +/-10% seed (the hard, link-invisible case)
    fac = 1 + rng.uniform(-0.10, 0.10, size=len(od_keys))
    d_prior = d_true * fac
    h0 = net["h_true"] * np.array([fac[kix[od]] for od in od_of])

    print(f"setup: 50% sensors ({len(sensors)}), random per-OD +/-10% seed (link-invisible).")
    print(f"{'variant':12} {'held MAPE':>9} {'OD R2':>7} {'OD MAPE':>8} {'dVMT%':>7} {'dVHT%':>7}")
    for mode in ("count", "cgodme"):
        h = run_variant(net, base, sensors, y_obs, h0, od_of, od_keys, kix, d_prior, vmt_true, mode)
        x = net["Delta"] @ h
        d = _od_aggregate(h, od_of, od_keys, kix)
        _, mape_h = _metrics(x_true[held], x[held])
        r2_od, mape_od = _metrics(d_true, d)
        vmt, vht = vmt_vht(x, net["length"], net["vf"], net["alpha"], net["beta"], net["cap"])
        print(f"{mode:12} {mape_h:>8.1f}% {r2_od:>7.3f} {mape_od:>7.1f}% "
              f"{100*(vmt-vmt_true)/vmt_true:>+6.1f} {100*(vht-vht_true)/vht_true:>+6.1f}")
    print("\nseed OD MAPE (the unrecoverable target):", f"{_metrics(d_true, d_prior)[1]:.1f}%")


if __name__ == "__main__":
    main()
