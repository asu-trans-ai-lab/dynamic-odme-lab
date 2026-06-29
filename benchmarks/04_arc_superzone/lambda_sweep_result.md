# ARC super-zone — reasonableness-constrained ODME λ-sweep result

Matrix-free operator (322k OD · 1.06M paths · 158k links · 1.86 GB). Target = observed DIRAADT counts.
Objective `min ‖MΔR d−y‖²/s_count + λ_OD‖(d−d0)/(d0+ε)‖² + λ_VMT(...)² + λ_VHT(...)²`, projected gradient,
50 iters fixed. Base: count %RMSE 82.8%, volume/count ratio 0.703 (model **under-loaded** vs observed).

## Stage 1 — the count vs OD-distortion / VMT frontier (the Pareto curve)
| λ_OD | count %RMSE | ratio | dVMT% | dVHT% | OD distortion | gate (count/VMT/OD) |
|---|---|---|---|---|---|---|
| 0 (free) | **41.3%** | 0.87 | +18.9 | +15.1 | 21.2% | PASS / **WARN** / **WARN** |
| 1e-5 | 65.4% | 0.76 | +6.5 | +4.8 | 4.8% | WARN / **PASS** / **PASS** |
| 3e-5 | 73.7% | 0.74 | +3.5 | +2.6 | 2.2% | WARN / PASS / PASS |
| 1e-4 | 79.2% | 0.72 | +1.4 | +1.0 | 0.8% | WARN / PASS / PASS |
| 1e-3 | 82.4% | 0.70 | +0.2 | +0.1 | 0.1% | WARN / PASS / PASS |
| 1e-2 | 82.7% | 0.70 | +0.0 | +0.0 | 0.0% | = base (fully anchored) |

The curve is the calibration tradeoff: free ODME fits counts best (41%) but inflates VMT +19% and distorts OD
21% (gates warn); raising λ_OD trades count fit for reasonableness, monotonically.

## Selected gate-balanced operating point
**λ_OD = 1e-5, λ_VMT = λ_VHT = 0** — reduces count %RMSE **82.8% → 65%** while keeping **VMT Δ +6.5% (PASS)**,
VHT Δ +4.8%, **OD distortion 4.8% (PASS)**. (Count gate still WARN at 65% < the 60% target — see the VMT-target
note: you cannot push count below ~65% on this network without VMT/OD warnings, because the model is genuinely
under-loaded.)

## Key finding 1 — VMT inflation is DRIVEN by OD distortion (they co-move)
The OD-prior anchor (λ_OD) alone controls VMT/VHT here: as OD distortion falls 21%→0, VMT Δ falls +19%→0 in
lockstep. So an explicit `λ_VMT` penalty is largely **redundant** on this case (Stage 2: λ_VMT≥1e4 only removes
the last ~1% of VMT that λ_OD already controlled). The free ODME scales demand up → both VMT and OD distortion
rise together.

## Key finding 2 — the VMT target choice decides whether the gate is right (you warned about this)
With **VMT* = base** (anti-inflation), the +19% VMT at λ_OD=0 reads as a WARNING. But the model is under-loaded
(ratio 0.70), so the **under-load-corrected regional proxy is VMT* ≈ 46.8 M = base/0.70**. Against that target,
the free solution's VMT (39.3 M) is **16% BELOW** the regional target — i.e. the demand increase is *legitimate*,
not over-loading. **Conclusion: with a real regional GDOT VMT target, the operating point shifts toward lower
λ_OD (more count fit allowed)**; the anti-inflation target is too conservative for an under-loaded base model.

## Compression is calibration-transparent at the operating point
| operator | paths kept | count %RMSE | dVMT% | OD distortion |
|---|---|---|---|---|
| exact | 100% | 65.4% | +6.5 | 4.8% |
| **top-1 path/OD** | **31%** | 66.2% | +5.6 | 4.8% |
| cum-95% | 83% | 65.6% | +6.3 | 4.8% |

Running ODME on a 3.2× compressed operator gives the **same operating point and the same gate verdicts**.

## One-line recommendation
> Operating point λ_OD = 1e-5 (λ_VMT = λ_VHT = 0): reduces count %RMSE 82.8% → 65% with VMT Δ +6.5% and OD
> distortion 4.8% (both gates pass). With a real regional VMT target (~46.8 M), a lower λ_OD (toward the free
> 41% solution) becomes acceptable, since the base model is under-loaded and the demand increase is legitimate.

Outputs: `lambda_sweep_summary.csv`, `selected_operating_point.md`, `compression_lambda_comparison.csv`.
(Minor: the "BAD" contrast row auto-picked λ_OD=0.01, the fully-anchored case; the true free/bad case is
λ_OD=0 — the 41%/+19%/21% top row.)
