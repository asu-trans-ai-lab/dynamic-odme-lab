"""Chicago Sketch: QVDF base case + ODME demand-recovery sensitivity (numpy/scipy.sparse).

1. Load network + 118k columns; build sparse path-link incidence Delta.
2. Base case: true link volume x = Delta h; QVDF-style speed v(VOC); a phi(t) departure profile
   gives time-dependent volume & speed profiles + congestion duration.
3. ODME sensitivity: observe a fraction p of links as counts, seed demand perturbed by +/-10%,
   recover path/OD flow by regularized least squares (Delta_S h ~ y, anchored to the seed), nonneg.
   Report fit on OBSERVED links, HELD-OUT links (generalization), OD recovery, VMT/VHT.

Run:  python -m odme.examples.chicago_qvdf_sensitivity
"""
from __future__ import annotations

import csv
import os

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import lsqr

# Chicago Sketch GMNS data is NOT bundled. Set CHICAGO_DATA to a local copy
# (e.g. a directory holding the Chicago Sketch link.csv / demand / columns).
SRC = os.environ.get("CHICAGO_DATA", "data/10_Chicago_Sketch")
T_BINS = 8
# a smooth single-peak departure profile over the analysis window (sums to 1)
PHI = np.array([0.06, 0.10, 0.15, 0.20, 0.19, 0.14, 0.10, 0.06])


def _read(p):
    with open(p, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_chicago():
    links = _read(SRC + "/link.csv")
    cols = _read(SRC + "/columns.csv")
    link_id = [int(float(r["link_id"])) for r in links]
    lix = {a: i for i, a in enumerate(link_id)}
    A = len(link_id)
    cap = np.array([float(r.get("capacity", 0) or 0) for r in links])
    vf = np.array([float(r.get("vdf_free_speed_mph") or r.get("free_speed") or 30) for r in links])
    length = np.array([float(r.get("vdf_length_mi") or 0) or float(r.get("length") or 0) for r in links])
    alpha = np.array([float(r.get("vdf_alpha", 0.15) or 0.15) for r in links])
    beta = np.array([float(r.get("vdf_beta", 4) or 4) for r in links])

    # sparse path-link incidence Delta (A x P) and per-column OD + true volume
    rows, colsi = [], []
    h_true = np.empty(len(cols))
    od_of = np.empty(len(cols), dtype=object)
    for j, r in enumerate(cols):
        h_true[j] = float(r["volume"])
        od_of[j] = (int(r["o_zone_id"]), int(r["d_zone_id"]))
        for a in str(r["link_sequence"]).split(";"):
            if a.strip() and int(a) in lix:
                rows.append(lix[int(a)]); colsi.append(j)
    Delta = sp.csr_matrix((np.ones(len(rows)), (rows, colsi)), shape=(A, len(cols)))
    return dict(link_id=link_id, A=A, cap=cap, vf=vf, length=length, alpha=alpha, beta=beta,
                Delta=Delta, h_true=h_true, od_of=od_of, n_cols=len(cols))


def qvdf_speed(x, cap, vf, alpha, beta):
    voc = np.where(cap > 1, x / cap, 0.0)
    return vf / (1.0 + alpha * np.power(voc, beta)), voc


def base_case(net):
    x = net["Delta"] @ net["h_true"]
    v, voc = qvdf_speed(x, net["cap"], net["vf"], net["alpha"], net["beta"])
    # time-dependent profiles via global phi(t): x_t = x * phi_t (scaled to per-bin)
    real = (net["length"] > 0.05) & (net["cap"] > 1)
    xt = np.outer(x, PHI)                      # A x T  (per-bin volume share)
    cap_bin = (net["cap"] * (1.0 / T_BINS))[:, None]
    voc_t = np.where(cap_bin > 0, xt / cap_bin, 0.0)
    vt = net["vf"][:, None] / (1.0 + net["alpha"][:, None] * np.power(voc_t, net["beta"][:, None]))
    cong_dur = (voc_t > 1.0).sum(axis=1) * (1.0 / T_BINS)   # hours over threshold, per link
    return dict(x=x, v=v, voc=voc, real=real, xt=xt, vt=vt, cong_dur=cong_dur)


def vmt_vht(x, length, vf, alpha, beta, cap):
    voc = np.where(cap > 1, x / cap, 0.0)
    fftt = np.where(vf > 1, length / vf, 0.0)
    tt = fftt * (1 + alpha * np.power(voc, beta))
    return float((x * length).sum()), float((x * tt).sum())


def _metrics(y, yh):
    y = np.asarray(y); yh = np.asarray(yh)
    m = y.mean()
    sst = ((y - m) ** 2).sum()
    r2 = 1 - ((y - yh) ** 2).sum() / sst if sst > 0 else float("nan")
    mask = y > 1
    mape = 100 * np.mean(np.abs(y[mask] - yh[mask]) / y[mask]) if mask.any() else float("nan")
    return r2, mape


def odme(net, base, sensor_frac, pert, rng, lam=0.05):
    A, P = net["A"], net["n_cols"]
    real = base["real"]
    x_true = base["x"]
    # candidate sensor links = real links carrying meaningful flow
    cand = np.where(real & (x_true > 50))[0]
    n_s = max(1, int(sensor_frac * len(cand)))
    sensors = rng.choice(cand, size=n_s, replace=False)
    held = np.setdiff1d(cand, sensors)
    y_obs = x_true[sensors]

    # seed demand perturbation: scale each OD's columns by (1 +/- pert)
    od_keys = list({od for od in net["od_of"]})
    if pert == "rand":
        fac = {od: 1 + rng.uniform(-0.10, 0.10) for od in od_keys}
    else:
        fac = {od: 1 + pert for od in od_keys}
    h0 = net["h_true"] * np.array([fac[od] for od in net["od_of"]])

    Ds = net["Delta"][sensors, :].tocsr()
    DsT = Ds.T.tocsr()
    expo = np.asarray(Ds.sum(axis=0)).ravel()          # # sensor links each column touches
    # bounded gradient ODME (stays near the seed -> physical; the realistic regularization)
    h_hat = h0.copy()
    bound, iters = 0.15, 60
    for k in range(iters):
        res = Ds @ h_hat - y_obs                        # sensor residual (veh)
        rel = res / np.maximum(y_obs, 1.0)              # relative -> scale-free
        grad = DsT @ rel                                # P-vector
        upd = (0.5) * grad / np.maximum(expo, 1.0) * np.maximum(h_hat, 1.0)
        upd = np.clip(upd, -bound * np.maximum(h_hat, 1.0), bound * np.maximum(h_hat, 1.0))
        h_hat = np.maximum(0.0, h_hat - upd)

    x_hat = net["Delta"] @ h_hat
    # OD recovery
    od_true, od_hat = {}, {}
    for j, od in enumerate(net["od_of"]):
        od_true[od] = od_true.get(od, 0.0) + net["h_true"][j]
        od_hat[od] = od_hat.get(od, 0.0) + h_hat[j]
    odk = list(od_true)
    r2_od, mape_od = _metrics([od_true[k] for k in odk], [od_hat[k] for k in odk])

    r2_obs, mape_obs = _metrics(x_true[sensors], x_hat[sensors])
    r2_held, mape_held = _metrics(x_true[held], x_hat[held]) if len(held) else (float("nan"),) * 2
    vmt_t, vht_t = vmt_vht(x_true, net["length"], net["vf"], net["alpha"], net["beta"], net["cap"])
    vmt_h, vht_h = vmt_vht(x_hat, net["length"], net["vf"], net["alpha"], net["beta"], net["cap"])
    # seed baseline (no ODME) held-out fit
    x_seed = net["Delta"] @ h0
    r2_seed, mape_seed = _metrics(x_true[held], x_seed[held]) if len(held) else (float("nan"),) * 2
    return dict(n_s=n_s, n_held=len(held), r2_obs=r2_obs, mape_obs=mape_obs,
                r2_held=r2_held, mape_held=mape_held, r2_seed=r2_seed, mape_seed=mape_seed,
                r2_od=r2_od, mape_od=mape_od, dvmt=100 * (vmt_h - vmt_t) / vmt_t,
                dvht=100 * (vht_h - vht_t) / vht_t)


def main():
    print("loading Chicago Sketch ...")
    net = load_chicago()
    base = base_case(net)
    real = base["real"]
    print(f"links={net['A']} (real={int(real.sum())})  columns={net['n_cols']}  "
          f"OD_pairs={len(set(net['od_of']))}")
    vmt, vht = vmt_vht(base["x"], net["length"], net["vf"], net["alpha"], net["beta"], net["cap"])
    congested = (base["voc"][real] > 1).sum()
    print(f"base case: VMT={vmt:,.0f} veh-mi  VHT={vht:,.0f} veh-h  "
          f"links VOC>1: {congested}/{int(real.sum())}  mean cong-duration(h)={base['cong_dur'][real].mean():.2f}")
    print(f"phi(t) T={T_BINS} peak share={PHI.max():.2f}")

    # QVDF time-dependent volume & speed profiles for the most congested links
    print("\nQVDF time-dependent profiles (top-3 most congested links):")
    order = np.argsort(-base["voc"] * real)
    for i in order[:3]:
        volp = " ".join(f"{base['xt'][i, t]:5.0f}" for t in range(T_BINS))
        spdp = " ".join(f"{base['vt'][i, t]:5.1f}" for t in range(T_BINS))
        print(f"  link {net['link_id'][i]} (vf={net['vf'][i]:.0f}, peakVOC={base['voc'][i]:.2f}, "
              f"cong={base['cong_dur'][i]:.2f}h):")
        print(f"     vol/bin: {volp}")
        print(f"     spd/bin: {spdp}")
    print()

    rng = np.random.default_rng(42)
    print(f"{'sensors%':>8} {'demand':>7} {'#sens':>6} {'obs MAPE':>9} {'HELD-OUT MAPE':>14} "
          f"{'(seed)':>8} {'OD R2':>7} {'OD MAPE':>8} {'dVMT%':>7} {'dVHT%':>7}")
    for frac in (0.25, 0.50, 0.75, 1.0):
        for pert in (0.10, -0.10, "rand"):
            r = odme(net, base, frac, pert, np.random.default_rng(7))
            pl = f"+10%" if pert == 0.10 else ("-10%" if pert == -0.10 else "rand")
            print(f"{int(frac*100):>7}% {pl:>7} {r['n_s']:>6} {r['mape_obs']:>8.1f}% "
                  f"{r['mape_held']:>13.1f}% {r['mape_seed']:>7.1f}% {r['r2_od']:>7.3f} "
                  f"{r['mape_od']:>7.1f}% {r['dvmt']:>+6.1f} {r['dvht']:>+6.1f}")


if __name__ == "__main__":
    main()
