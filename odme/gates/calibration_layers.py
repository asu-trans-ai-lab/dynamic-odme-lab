"""Section-7-style layered calibration validation (ARC Atlanta template).

Implements the stratified validation the agency report uses (Tables 7-5..7-13):
count fit by volume group / facility / area / screenline / corridor, plus VMT and truck gates.
Each stratum gets RMSE, %RMSE, volume/count ratio, and a PASS/FAIL vs the ARC %RMSE thresholds.
This is the assignment-validation layer that sits ON TOP of ODME (Layers 3-10 of the framework).
"""
from __future__ import annotations

import math
from .verification import GateResult

# ARC acceptable %RMSE thresholds by volume group (Table 7-5 / ARC_BENCHMARK)
VOL_GROUPS = [(0, 2500, 100), (2500, 5000, 55), (5000, 10000, 45),
              (10000, 25000, 30), (25000, 50000, 25), (50000, 1e12, 19)]

FACILITY = {1: "freeway", 4: "freeway", 5: "freeway", 6: "freeway", 2: "expressway",
            3: "parkway", 7: "ramp", 8: "ramp", 9: "ramp",
            10: "arterial", 11: "arterial", 12: "arterial", 13: "collector", 14: "collector"}


def _stats(assigned, observed):
    n = len(observed)
    if n == 0:
        return None
    rmse = math.sqrt(sum((a - o) ** 2 for a, o in zip(assigned, observed)) / n)
    mean_obs = sum(observed) / n
    pct = 100 * rmse / mean_obs if mean_obs > 0 else float("nan")
    ratio = sum(assigned) / sum(observed) if sum(observed) > 0 else float("nan")
    return dict(n=n, rmse=rmse, pct_rmse=pct, ratio=ratio, mean_obs=mean_obs)


def by_volume_group(rows):
    """Table 7-5: validation by volume group, with PASS/FAIL vs ARC threshold."""
    out = []
    for lo, hi, thr in VOL_GROUPS:
        grp = [(r["assigned"], r["observed"]) for r in rows if lo <= r["observed"] < hi]
        s = _stats([a for a, _ in grp], [o for _, o in grp])
        if not s:
            continue
        s.update(group=f"{int(lo/1000)}-{int(hi/1000) if hi<1e11 else '+'}k", threshold=thr,
                 status="PASS" if s["pct_rmse"] <= thr else "FAIL")
        out.append(s)
    return out


def by_category(rows, key):
    out = {}
    for r in rows:
        out.setdefault(r[key], []).append((r["assigned"], r["observed"]))
    res = []
    for k, grp in sorted(out.items()):
        s = _stats([a for a, _ in grp], [o for _, o in grp])
        if s:
            s["label"] = k; res.append(s)
    return res


def screenline_validation(rows):
    """Table 7-8: aggregate to screenline totals (y = S x), report % difference."""
    agg = {}
    for r in rows:
        sl = r.get("screenline", 0)
        if not sl:
            continue
        a, o = agg.setdefault(sl, [0.0, 0.0])
        agg[sl][0] += r["assigned"]; agg[sl][1] += r["observed"]
    out = []
    for sl, (a, o) in sorted(agg.items()):
        out.append(dict(screenline=sl, estimated=a, observed=o,
                        pct_diff=100 * (a - o) / o if o > 0 else float("nan")))
    return out


def vmt_gate(rows, length_key="length"):
    """Layer 4: VMT consistency (assigned vs observed-derived)."""
    vmt_a = sum(r["assigned"] * r.get(length_key, 1.0) for r in rows)
    vmt_o = sum(r["observed"] * r.get(length_key, 1.0) for r in rows)
    d = 100 * (vmt_a - vmt_o) / vmt_o if vmt_o > 0 else float("nan")
    status = "PASS" if abs(d) <= 10 else "WARNING"
    return GateResult("VMT consistency", status, f"assigned/observed VMT ratio {vmt_a/max(vmt_o,1):.3f} ({d:+.1f}%)")


def overall_gate(vol_rows):
    """Region-wide verdict: how many volume groups pass."""
    npass = sum(1 for r in vol_rows if r["status"] == "PASS")
    region_pct = sum(r["rmse"] ** 2 * r["n"] for r in vol_rows)
    region_n = sum(r["n"] for r in vol_rows)
    mean_obs = sum(r["mean_obs"] * r["n"] for r in vol_rows) / max(region_n, 1)
    region_rmse = math.sqrt(region_pct / max(region_n, 1))
    region_pct_rmse = 100 * region_rmse / max(mean_obs, 1)
    status = "PASS" if npass >= len(vol_rows) - 1 else "FAIL"
    return GateResult("region-wide count fit", status,
                      f"{npass}/{len(vol_rows)} volume groups pass; region %RMSE={region_pct_rmse:.0f}% (ARC target ~38%)")
