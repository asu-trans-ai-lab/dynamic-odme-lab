"""Section-7 layered calibration report on real ARC Atlanta data (modeled vs OBSERVED counts).

Validates the ARC model's AM volume (V_TOTAM) against the OBSERVED field counts (DIRAADT15 x AM-factor)
extracted from the shapefile — the validation the ARC benchmark omits — stratified exactly like
Section 7 Tables 7-5..7-8, with gate verdicts. Writes calibration_summary.csv + gate_report.md.

Run:  python -m odme.examples.arc_calibration_report
"""
from __future__ import annotations

import csv

from ..gates import calibration_layers as CL

CASE = "cases/09_arc_atlanta"


def load_rows():
    rows = []
    with open(CASE + "/arc_observed_counts.csv", newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            obs = float(r["am_observed_est"]); asg = float(r["v_totam_modeled"])
            if obs <= 0 or asg <= 0:
                continue
            rows.append(dict(assigned=asg, observed=obs,
                             facility=CL.FACILITY.get(int(float(r["factype"])), "other"),
                             area=f"atype{r['atype']}", screenline=int(float(r["screenline"])),
                             length=1.0, truck_obs=obs * float(r["trkpct"]) / 100.0,
                             truck_mod=float(r["v_trkam_modeled"])))
    return rows


def main():
    rows = load_rows()
    print(f"ARC Section-7 validation: MODEL (V_TOTAM) vs OBSERVED (DIRAADT15 x 0.259)  on {len(rows)} count links\n")

    print("Table 7-5  validation by VOLUME GROUP")
    vol = CL.by_volume_group(rows)
    print(f"  {'group':>8} {'n':>5} {'%RMSE':>7} {'thresh':>7} {'ratio':>6}  verdict")
    for s in vol:
        print(f"  {s['group']:>8} {s['n']:>5} {s['pct_rmse']:>6.0f}% {s['threshold']:>6}% {s['ratio']:>6.2f}  {s['status']}")

    print("\nTable 7-6  by FACILITY TYPE")
    for s in CL.by_category(rows, "facility"):
        print(f"  {s['label']:>10} n={s['n']:>5} %RMSE={s['pct_rmse']:>5.0f}% ratio={s['ratio']:.2f}")

    print("\nTable 7-7  by AREA TYPE")
    for s in CL.by_category(rows, "area"):
        print(f"  {s['label']:>10} n={s['n']:>5} %RMSE={s['pct_rmse']:>5.0f}% ratio={s['ratio']:.2f}")

    print("\nTable 7-8  by SCREENLINE (top 8 by |%diff|)")
    sl = sorted(CL.screenline_validation(rows), key=lambda r: -abs(r["pct_diff"]))
    print(f"  {'screenline':>10} {'observed':>10} {'estimated':>10} {'%diff':>7}")
    for r in sl[:8]:
        print(f"  {r['screenline']:>10} {r['observed']:>10.0f} {r['estimated']:>10.0f} {r['pct_diff']:>+6.0f}%")

    print("\nGates:")
    g_vmt = CL.vmt_gate(rows); g_reg = CL.overall_gate(vol)
    truck_obs = sum(r["truck_obs"] for r in rows); truck_mod = sum(r["truck_mod"] for r in rows)
    print(" ", g_reg.line())
    print(" ", g_vmt.line())
    print(f"  [{'PASS' if abs(truck_mod/max(truck_obs,1)-1)<0.25 else 'WARNING':7}] truck ratio "
          f"model/observed = {truck_mod/max(truck_obs,1):.2f}")

    # outputs
    with open(CASE + "/calibration_summary.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["stratum", "group", "n", "pct_rmse", "ratio", "status"])
        for s in vol:
            w.writerow(["volume_group", s["group"], s["n"], round(s["pct_rmse"], 1), round(s["ratio"], 3), s["status"]])
        for s in CL.by_category(rows, "facility"):
            w.writerow(["facility", s["label"], s["n"], round(s["pct_rmse"], 1), round(s["ratio"], 3), ""])
    with open(CASE + "/gate_report.md", "w", encoding="utf-8") as f:
        f.write("# ARC calibration gate report (model vs observed counts)\n\n")
        f.write(f"- {g_reg.finding}\n- {g_vmt.finding}\n")
        f.write(f"- truck model/observed ratio = {truck_mod/max(truck_obs,1):.2f}\n\n")
        f.write("Volume-group verdicts:\n")
        for s in vol:
            f.write(f"  - {s['group']}: %RMSE {s['pct_rmse']:.0f}% vs threshold {s['threshold']}% -> {s['status']}\n")
    print(f"\n-> {CASE}/calibration_summary.csv\n-> {CASE}/gate_report.md")


if __name__ == "__main__":
    main()
