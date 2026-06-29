# ARC super-zone — ODME before/after gate report (matrix-free, observed-count target)

Operator: `A = M Δ R` matrix-free (322,522 OD · 1,056,688 paths · 158,033 links · **1.86 GB**, never the
408 GB dense). Target: **observed counts** (11,108 DIRAADT links × AM-factor). Regularized ODME
`min ‖MΔR d − y_obs‖² + λ‖d − d0‖²`, λ=0.1, projected gradient, 33 s.

## Before / after
| metric | before (FW base) | after ODME | gate |
|---|---|---|---|
| count %RMSE | **82.8%** | **40.5%** | improved (halved) |
| volume/count ratio | 0.703 | 0.872 | model under-loaded vs observed; ODME scaled up |
| VMT | 32.9 M | 39.3 M (**+19.3%**) | **WARNING** |
| VHT | 834 k | 964 k (**+15.6%**) | **WARNING** |
| OD distortion \|Δd\|/d0 | — | **22.7%** | **WARNING** |

## Gate verdict (the calibration tension, exactly as Section-7 warns)
- **count gate — improving**: %RMSE 83% → 41% on the observed counts.
- **VMT/VHT gate — WARNING**: count fit halved, but VMT +19% and VHT +16%. The model was under-loaded
  (ratio 0.70), so *some* increase is legitimate, but +19% VMT must be checked against the regional GDOT VMT
  target (Section-7 Table 7-4) before acceptance.
- **OD-distortion gate — WARNING**: 22.7% mean demand change; needs evidence or a stronger anchor.

**Recommended action:** raise λ (anchor) and/or add explicit `L_VMT`/`L_VHT` regularizers so ODME fits counts
without inflating VMT/VHT — reasonableness-constrained calibration, not free count-fitting.

## Compression-level comparison (the key result)
ODME run under each operator, judged by gates (not matrix error):
| operator | paths kept | before %RMSE | after %RMSE | dVHT% | OD distortion |
|---|---|---|---|---|---|
| exact | 100% | 82.8% | 42.3% | +14.5% | 19.5% |
| **top-1 path/OD** | **31%** | 82.9% | 43.8% | +13.6% | 18.4% |
| cum-95% flow | 83% | 82.6% | 42.6% | +14.3% | 19.2% |

**Compression is calibration-transparent:** ODME on a 3.2× compressed operator (top-1, 31% of paths) gives
essentially the same calibration outcome (after %RMSE 44% vs 42%, same gate verdicts) as the exact operator.
This is the compressed-optimization thesis proven on a real 146k-link MPO network.

Files: `before_after_calibration_summary.csv`, this report. Operator from `gmns_superzone/route_assignment.csv`.
