# Case 09 — ARC Atlanta (CONDENSED)

This case is the **Atlanta Regional Commission (ARC) MPO** network, used to demonstrate the
matrix-free assignment operator and regularized ODME **at agency scale** (146k links, ~322k OD pairs,
~1.06M paths). It is the largest case in the project.

## Why this folder is condensed

The full ARC inputs are **~3.7 GB** (raw `100_arc_atlanta/`: route assignment 2.0 GB, link shapefiles
~1.1 GB, OD/link performance ~0.5 GB). That exceeds what is reasonable to host on GitHub without LFS, so
**the network and seed demand are not distributed here.** What remains are the *result artifacts* — the
calibration story is fully reproduced in the reports below.

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

### NOT shipped (regenerate locally)
`link.csv` (50 MB), `node.csv` (2.4 MB), `demand.csv` (13.7 MB), and the raw `100_arc_atlanta/`
TAPLite super-zone columns. To reproduce end-to-end, place a local copy of the ARC data and point the
scripts at it:

```bash
export ARC_DATA=/path/to/100_arc_atlanta      # raw network + gmns_superzone/route_assignment.csv
python -m odme.examples.arc_odme_report        # exact-operator before/after ODME
python -m odme.examples.arc_odme_lambda_sweep  # OD-prior λ sweep + compression comparison
```

See `../../docs/OPERATOR_COMPRESSION.md` for the matrix-free operator (A = M Δ R, never dense) and the
agency-scale numbers.
