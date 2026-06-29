"""Reasonableness gates — codified expert calibration judgment.

ODME is reasonableness-controlled calibration, not count curve-fitting. A solution can match
counts and still be wrong (VMT/VHT off, OD distorted, departure profile unphysical, residuals
corridor-concentrated). These gates encode that judgment as PASS/WARNING/FAIL.

Functions take plain numbers/arrays so they compose with any solver.
"""
from __future__ import annotations

import math

from .verification import GateResult


def _r2(y, yh):
    n = len(y)
    if n == 0:
        return float("nan")
    m = sum(y) / n
    sst = sum((a - m) ** 2 for a in y)
    ssr = sum((a - b) ** 2 for a, b in zip(y, yh))
    return 1 - ssr / sst if sst > 1e-9 else float("nan")


def _mape(y, yh):
    pairs = [(a, b) for a, b in zip(y, yh) if a > 1e-9]
    return 100.0 / len(pairs) * sum(abs(a - b) / a for a, b in pairs) if pairs else float("nan")


def gate_count_quality(y_obs, y_model):
    """The headline gate: high count-R2 can hide a bad fit; report MAPE alongside."""
    r2, mape = _r2(y_obs, y_model), _mape(y_obs, y_model)
    if r2 > 0.9 and mape > 25:
        return GateResult("count quality", "WARNING",
                          f"R2={r2:.3f} looks great but MAPE={mape:.0f}% is high",
                          "count R2 is dominated by large links; the fit is NOT actually good")
    if mape > 40:
        return GateResult("count quality", "FAIL", f"MAPE={mape:.0f}% (R2={r2:.3f})")
    return GateResult("count quality", "PASS", f"R2={r2:.3f}, MAPE={mape:.0f}%")


def gate_vmt_vht(link_vol_a, link_vol_b, links, dt_h, label_a="ref", label_b="solved"):
    """VMT = sum x*L ; VHT = sum x*T(BPR). Flag if VHT moves much more than VMT (overloading)."""
    def vmt_vht(vol):
        vmt = vht = 0.0
        for (lid, t), x in vol.items():
            lk = links.get(lid)
            if not lk:
                continue
            fftt_h = lk.length / max(lk.free_speed, 1.0)
            cap = lk.link_capacity * dt_h
            voc = x / cap if cap > 0 else 0.0
            tt_h = fftt_h * (1 + lk.alpha * voc ** lk.beta)
            vmt += x * lk.length
            vht += x * tt_h
        return vmt, vht
    va, ha = vmt_vht(link_vol_a)
    vb, hb = vmt_vht(link_vol_b)
    dvmt = 100 * (vb - va) / va if va else 0.0
    dvht = 100 * (hb - ha) / ha if ha else 0.0
    detail = f"VMT {va:.0f}->{vb:.0f} ({dvmt:+.1f}%)  VHT {ha:.0f}->{hb:.0f} ({dvht:+.1f}%)"
    if abs(dvht) > 25 and abs(dvht) > 3 * max(abs(dvmt), 1):
        return GateResult("VMT/VHT consistency", "WARNING",
                          f"VHT moved {dvht:+.0f}% with VMT only {dvmt:+.0f}% (possible overloading)", detail)
    return GateResult("VMT/VHT consistency", "PASS", "macro totals consistent", detail)


def gate_od_distortion(d_new, d_seed, names=None):
    """Flag aggressive OD changes vs the seed prior."""
    rels = []
    for k in d_new:
        s = d_seed.get(k, 0.0)
        if s > 1e-6:
            rels.append((k, (d_new[k] - s) / s))
    if not rels:
        return GateResult("OD distortion", "PASS", "no seed to compare")
    k_worst, worst = max(rels, key=lambda kv: abs(kv[1]))
    mean_abs = 100 * sum(abs(r) for _, r in rels) / len(rels)
    detail = f"mean |dOD|={mean_abs:.0f}%, worst OD {k_worst} = {100*worst:+.0f}%"
    if abs(worst) > 2.0:
        return GateResult("OD distortion", "WARNING",
                          f"OD {k_worst} changed {100*worst:+.0f}% vs seed without evidence", detail)
    return GateResult("OD distortion", "PASS", "OD changes within plausible range", detail)


def gate_departure_profile(phi, ref_phi=None):
    """Realism of the aggregate departure-time profile: smoothness + single-peak shape."""
    T = len(phi)
    if T < 3:
        return GateResult("departure profile", "PASS", "too few bins to assess")
    rough = sum(abs(phi[t + 1] - 2 * phi[t] + phi[t - 1]) for t in range(1, T - 1))
    peaks = sum(1 for t in range(1, T - 1) if phi[t] > phi[t - 1] and phi[t] > phi[t + 1])
    detail = f"roughness(2nd-diff)={rough:.3f}, local_peaks={peaks}"
    if peaks > 2 or rough > 0.5:
        return GateResult("departure profile", "WARNING",
                          f"profile is spiky/multi-peak ({peaks} peaks) — likely unphysical", detail)
    return GateResult("departure profile", "PASS", "smooth single-peak profile", detail)


def gate_corridor_residual(residual_by_link):
    """Flag spatially concentrated residual (one facility carrying the error)."""
    if not residual_by_link:
        return GateResult("corridor residual", "PASS", "no residuals")
    tot = sum(abs(v) for v in residual_by_link.values())
    if tot < 1e-9:
        return GateResult("corridor residual", "PASS", "residuals ~0")
    lid, mx = max(residual_by_link.items(), key=lambda kv: abs(kv[1]))
    share = 100 * abs(mx) / tot
    detail = f"link {lid} holds {share:.0f}% of total abs residual"
    if share > 30:
        return GateResult("corridor residual", "WARNING",
                          f"residual concentrated: link {lid} = {share:.0f}% of total error", detail)
    return GateResult("corridor residual", "PASS", "residual spatially diffuse", detail)
