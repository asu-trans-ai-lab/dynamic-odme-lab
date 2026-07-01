# Case 09 — ARC Atlanta (CONDENSED)

This case is the **Atlanta Regional Commission (ARC) MPO** network, used to demonstrate the
matrix-free assignment operator and regularized ODME **at agency scale** (146k links, ~322k OD pairs,
~1.06M paths). It is the largest case in the project.

## Why this folder is condensed

The full raw ARC inputs are **~3.7 GB** (route assignment 2.0 GB, link shapefiles ~1.1 GB, OD/link
performance ~0.5 GB) — too large for GitHub. So this folder ships the **result artifacts** *plus* the
**network + demand needed to reproduce the assignment**, gzipped under `network/` (~21 MB, see below).

### Shipped (result + target artifacts)
| file | what |
|---|---|
| `before_after_calibration_summary.csv` | before/after ODME: count %RMSE, ratio, VMT/VHT, OD distortion |
| `lambda_sweep_summary.csv`, `lambda_sweep_result.md` | OD-prior λ sweep + selected operating point |
| `compression_lambda_comparison.csv` | exact vs top-1 vs cum-95% path-pruning, judged by the gates |
| `selected_operating_point.md`, `calibration_summary.csv` | chosen λ and headline metrics |
| `gate_report.md`, `odme_gate_report.md`, `readiness_report.md` | calibration gates + Stage-0 readiness |
| `arc_observed_counts.csv`, `measurement.csv` | the 11k observed sensor-link targets |
| `COUNTS_PREPARED.md`, `settings.csv` | how the counts were prepared + run settings |

### Network + demand — SHIPPED (gzipped, for end-to-end reproduction)
The full ARC assignment inputs are now provided under **`network/`** (gzipped, ~21 MB total; largest file
`link.csv.gz` = 14 MiB — well under GitHub limits, no LFS): `link.csv` (50 MB), `node.csv` (2.4 MB),
`demand_sov/hov2/hov3.csv` (13.7 / 3.8 / 2.5 MB), `mode_type.csv`, `settings.csv`, and
`arc_am_ref_volume.csv` (AM reference for validation). **See [REPRODUCE.md](REPRODUCE.md)** for the
decompress → DTALite assignment → validation steps (reproduces correlation **0.993**, ratio **1.00** vs ARC's
AM assignment).

The only piece not shipped is the raw 2.0 GB TAPLite super-zone `route_assignment.csv` (used for the exact
matrix-free operator); the DTALite assignment above does not need it.

```bash
# quick start (details in REPRODUCE.md)
cd network && gunzip -k *.gz && cp /path/to/DTALite.exe . && ./DTALite.exe && cd ..
cp network/arc_am_ref_volume.csv . && python arc_calibration_report.py network
```

See `../../docs/OPERATOR_COMPRESSION.md` for the matrix-free operator (A = M Δ R, never dense) and the
agency-scale numbers.
