"""Reproduce the ARC Section-7 traffic-assignment calibration tables for a kernel run.

Compares assigned auto volume (link_performance.csv `volume`) against the ARC AM reference
(`arc_am_ref_volume.csv` `ref_auto_vol`) and builds ARC-format validation statistics:
  Table 7-5  by volume group   (+ ARC acceptable/preferred %RMSE thresholds)
  Table 7-6  by facility type   (Interstate/Freeway, Principal/Minor Arterial, Collector, Ramps)
  Table 7-7  by area type       (ATYPE 1-7)
  correlation coefficient, region-wide %RMSE, volume/count ratio
Prints the ARC report's own numbers alongside for direct comparison, and writes a markdown report.

Usage:  python arc_calibration_report.py [run_dir=gmns_calibrated]
"""
from __future__ import annotations
import csv, math, os, sys
from collections import defaultdict
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "gmns_calibrated")

# factype -> ARC Table 7-6 facility group
FAC = {1: "Interstate/Freeway", 2: "Interstate/Freeway", 3: "Interstate/Freeway",
       4: "Interstate/Freeway", 5: "Interstate/Freeway", 6: "Interstate/Freeway",
       7: "Ramps", 8: "Ramps", 9: "Ramps",
       10: "Principal Arterial", 11: "Minor Arterial", 12: "Minor Arterial", 13: "Minor Arterial",
       14: "Collector"}
FAC_ORDER = ["Interstate/Freeway", "Principal Arterial", "Minor Arterial", "Collector", "Ramps"]
ATYPE_NAME = {1: "1- CBD", 2: "2- High density urban", 3: "3- Medium density urban",
              4: "4- Low density urban", 5: "5- Suburban", 6: "6- Exurban", 7: "7- Rural"}
# volume groups: (lo, hi, acceptable%RMSE, preferred%RMSE)
VGROUPS = [(0, 2500, 100, 100), (2500, 5000, 100, 100), (5000, 10000, 45, 35),
           (10000, 25000, 30, 25), (25000, 50000, 25, 15), (50000, 75000, 19, 10),
           (75000, 100000, 19, 10), (100000, 1e12, 19, 10)]
VLABEL = ["< 2,500", "2,500-4,999", "5,000-9,999", "10,000-24,999", "25,000-49,999",
          "50,000-74,999", "75,000-99,999", ">= 100,000"]
# ARC report's own numbers (for side-by-side)
ARC = dict(overall_pctrmse=38, overall_vc=0.91, corr=0.95,
           fac={"Interstate/Freeway": (18, 0.93), "Principal Arterial": (29, 0.93),
                "Minor Arterial": (41, 0.93), "Collector": (74, 0.79), "Ramps": (41, 0.89)})


def stats(ref, asg):
    ref = np.asarray(ref, float); asg = np.asarray(asg, float)
    n = len(ref); mean = ref.mean() if n else 0
    rmse = math.sqrt(np.mean((asg - ref) ** 2)) if n else 0
    return n, ref.sum(), asg.sum(), rmse, (100 * rmse / mean if mean else 0), (asg.sum() / ref.sum() if ref.sum() else 0)


def main():
    ref = {}
    for r in csv.DictReader(open(os.path.join(HERE, "arc_am_ref_volume.csv"), encoding="utf-8-sig")):
        ref[(r["from_node_id"], r["to_node_id"])] = (float(r["ref_auto_vol"]),
                                                     int(float(r["factype"])), int(float(r["atype"])))
    lp = os.path.join(RUN, "link_performance.csv")
    asg = {}
    for r in csv.DictReader(open(lp, encoding="utf-8-sig")):
        try:
            asg[(r["from_node_id"], r["to_node_id"])] = float(r["volume"])
        except (KeyError, ValueError):
            pass
    keys = [k for k in ref if k in asg and ref[k][1] != 0]     # drop centroid connectors (factype 0)
    R = np.array([ref[k][0] for k in keys]); A = np.array([asg[k] for k in keys])
    fac = [FAC.get(ref[k][1]) for k in keys]; at = [ref[k][2] for k in keys]
    out = ["# ARC traffic-assignment calibration -- reproduction (AM period, auto)\n",
           f"Run: `{os.path.relpath(RUN, HERE)}`  |  matched links (non-connector): **{len(keys):,}**  |  "
           "reference = ARC AM assigned auto volume (`ref_auto_vol`).\n",
           "> The ARC report validates **daily** volumes vs GDOT counts (Tables 7-5..7-7). Here we reproduce "
           "the same table structure comparing our kernel's **AM** assignment against ARC's **AM** reference "
           "assignment; %RMSE / correlation / volume ratio are the directly comparable statistics.\n"]

    # ---- Table 7-5 volume group ----
    out.append("## Table 7-5 equivalent -- by volume group\n")
    out.append("| Volume Group | n | Ref (auto) | Est | RMSE | %RMSE | Accept | Prefer | Est/Ref |")
    out.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for (lo, hi, acc, pref), lab in zip(VGROUPS, VLABEL):
        idx = [i for i in range(len(keys)) if lo <= R[i] < hi]
        if not idx:
            continue
        n, rs, as_, rmse, pr, vc = stats(R[idx], A[idx])
        out.append(f"| {lab} | {n:,} | {rs:,.0f} | {as_:,.0f} | {rmse:,.0f} | {pr:.0f}% | {acc}% | {pref}% | {vc:.2f} |")
    n, rs, as_, rmse, pr, vc = stats(R, A)
    out.append(f"| **Total** | **{n:,}** | **{rs:,.0f}** | **{as_:,.0f}** | **{rmse:,.0f}** | "
               f"**{pr:.0f}%** | 45% | 38% | **{vc:.2f}** |")
    out.append(f"\n*ARC report (daily vs counts): overall %RMSE **38%**, volume/count **0.91**.*\n")

    # ---- Table 7-6 facility type ----
    out.append("## Table 7-6 equivalent -- by facility type\n")
    out.append("| Facility Type | n | Ref | Est | RMSE | %RMSE | Est/Ref | ARC %RMSE | ARC ratio |")
    out.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for f in FAC_ORDER:
        idx = [i for i in range(len(keys)) if fac[i] == f]
        if not idx:
            continue
        n, rs, as_, rmse, pr, vc = stats(R[idx], A[idx])
        ap, ar = ARC["fac"][f]
        out.append(f"| {f} | {n:,} | {rs:,.0f} | {as_:,.0f} | {rmse:,.0f} | {pr:.0f}% | {vc:.2f} | {ap}% | {ar} |")
    n, rs, as_, rmse, pr, vc = stats(R, A)
    out.append(f"| **Total** | **{n:,}** | **{rs:,.0f}** | **{as_:,.0f}** | **{rmse:,.0f}** | **{pr:.0f}%** | "
               f"**{vc:.2f}** | 38% | 0.91 |")

    # ---- Table 7-7 area type ----
    out.append("\n## Table 7-7 equivalent -- by area type\n")
    out.append("| Area Type | n | Ref | Est | RMSE | %RMSE | Est/Ref |")
    out.append("|---|---:|---:|---:|---:|---:|---:|")
    for a in range(1, 8):
        idx = [i for i in range(len(keys)) if at[i] == a]
        if not idx:
            continue
        n, rs, as_, rmse, pr, vc = stats(R[idx], A[idx])
        out.append(f"| {ATYPE_NAME[a]} | {n:,} | {rs:,.0f} | {as_:,.0f} | {rmse:,.0f} | {pr:.0f}% | {vc:.2f} |")

    # ---- correlation + headline ----
    corr = float(np.corrcoef(R, A)[0, 1])
    n, rs, as_, rmse, pr, vc = stats(R, A)
    out.append("\n## Headline vs ARC report\n")
    out.append("| metric | this kernel | ARC report |")
    out.append("|---|---:|---:|")
    out.append(f"| correlation coefficient | **{corr:.3f}** | 0.95 |")
    out.append(f"| region-wide %RMSE | **{pr:.0f}%** | 38% |")
    out.append(f"| volume ratio (Est/Ref) | **{vc:.2f}** | 0.91 |")
    out.append(f"| matched links | {len(keys):,} | 11,017 counts |")

    rep = os.path.join(HERE, "arc_calibration_reproduction.md")
    open(rep, "w", encoding="utf-8").write("\n".join(out))
    print(f"correlation={corr:.3f}  region %RMSE={pr:.0f}%  Est/Ref={vc:.2f}  links={len(keys):,}")
    print("wrote", os.path.relpath(rep, HERE))


if __name__ == "__main__":
    main()
