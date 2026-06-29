# ARC Atlanta — observed counts found in the long shapefile, prepared for ODME

Source shapefile: `100_arc_atlanta/arc-Shape_long/arc-Shape/AMLink2020.dbf`
(150,255 records, 143 fields). Calibration spec: `Section 7_traffic_assignment_calibration.docx`
+ `ARC_BENCHMARK.md`.

## Are the counts in the shapefile? YES.
The long `.dbf` carries **observed field counts**, separate from the modeled volumes:

| field(s) | meaning | coverage |
|---|---|---|
| `CNTSTATION` | count-station ID | 11,387 links |
| **`DIRAADT00/05/10/15`** | directional AADT (observed daily), by year | **11,108 links (DIRAADT15>0)** |
| `HR1`–`HR24` | **hourly** count profile | 176 links (ATR stations) → dynamic ODME |
| `ATR`, `ATR_DIR` | automatic traffic recorder | 176 links |
| `SCREENLINE` | screenline ID | 553 links |
| `TRKPCT/MTKPCT/HTKPCT` | truck % | with counts |
| `V_TOTAM, V_SOVAM, …` | **modeled** AM volumes (the model output) | 144,054 links |

So the **observed counts (DIRAADT, ATR, HR1–24)** are a real, untapped data source distinct from
`arc_am_ref_volume.csv` — which `ARC_BENCHMARK.md` §4 confirms is the **modeled** assigned volume
(`ref_total_vol = V_TOTAM`), used as the current "ground truth".

## The finding that matters
The ARC benchmark (`ARC_BENCHMARK.md` §6) validates **assigned vs modeled-ref** → 23% region-wide RMSE, "passes".
But validating **modeled vs the OBSERVED counts** (the field truth) tells a different story:

> **MODEL (V_TOTAM) vs OBSERVED (DIRAADT15 × AM-factor 0.259), 11,005 count links: R² = 0.864, MAPE = 70.3%.**

The model matches its *own* assigned volumes but is ~70% off per link against real counts — which is exactly the
case for running ODME against the **observed** counts rather than the modeled ref. (AM factor 0.259 = median
V_TOTAM/DIRAADT15, i.e. the AM 4-h period ≈ 26% of daily.)

## What was prepared (this folder)
- **`arc_observed_counts.csv`** — 11,108 observed counts mapped 1:1 to GMNS `link_id`:
  `link_id, A, B, station, dir_aadt15, am_observed_est, v_totam_modeled, atr, screenline, hr_am`.
- **`measurement.csv`** — ODME Path-B target (`from_node_id, to_node_id, count=AM observed est, note=station`).
- GMNS network copied (`node.csv` 66,546 nodes / `link.csv` 145,971 links / `demand.csv` / `settings.csv`).

`odme check` → **READY** (network + 11,108 observed counts ingest and resolve to links).

## To actually run ODME here (next step)
`columns = 0` — ARC has **no pre-generated route columns**, so the assignment matrix A is empty and ODME
cannot move yet. Needs an assignment pass (DTALite/TAPLite on the calibrated GMNS) to emit `route_assignment.csv`;
then ODME fits the **observed** `measurement.csv` (not the modeled ref_volume). Note: the readiness run mixed
Path A (modeled `ref_volume` in link.csv) + Path B (observed `measurement.csv`) = 154,919 measurements — for an
observed-count ODME, use **Path B only** (drop `ref_volume` from link.csv, or treat it as the prior, not a target).
The 176 ATR links with `HR1–24` give an hourly profile for a **dynamic** (T>1) ODME.
