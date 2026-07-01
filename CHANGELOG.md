# Changelog

All notable changes to `dynamic-odme-lab`.

## [0.2.1] — observability gate
### Added
- **`odme.bounded.observability_mask(path_link, path_od, sensor_link_cols, n_od)`** — per-OD count of
  distinct sensor links crossed + an `adjustable` mask. RULE: an OD pair whose paths cross **no** sensor
  point is unobservable and must not be adjusted.
- `bounded_lowrank_odme(..., observable=mask)` — freezes `theta = 1` for unobserved OD pairs (they stay at
  seed). This is the public twin of the DTALite/TAPLite ODME **sensor-point observability gate**: only OD
  that pass a sensor may enter the adjustment stage; total regional trips stay anchored to the base OD.
- Test coverage for the gate (frozen OD stay at seed).

## [0.2.0] — bounded low-rank OD adjustment
### Added
- **`odme.bounded`** — bounded, low-rank ODME that treats the OD adjustment as an interpretable
  multiplicative *correction surface* rather than cell-by-cell demand reconstruction:
  `Q_new(i,j) = theta_ij · Q_base(i,j)`, `log theta = mu + O_i + D_j (+ small rank-R)`, with a **hard ±bound**
  (default ±10%) on every OD pair, so origin production `P_i` and destination attraction `A_j` also stay in
  band. Matrix-free (`matvec`/`rmatvec`), with optional per-link calibration of the base loading.
  - `bounded_lowrank_odme(...)` → `ODMEResult` (adjusted OD, theta, count fit, structure diagnostics).
  - `three_version_comparison(...)` → **V0** (no ODME) / **V1** (unconstrained) / **V2** (bounded) rows.
- Diagnostics: theta distribution (median, p5/p95, %outside band), origin/destination total ranges,
  origin/destination-explained variance of `log theta` (low-rank check), total demand change.
- `examples/run_bounded_odme.py` (synthetic, self-contained) and `tests/test_bounded_odme.py`.
- `docs/10_bounded_lowrank_odme.md` — formulation, acceptance criteria, and the "if it can't fit within
  ±bound, fix the base upstream" diagnostic rule.

### Rationale
Unconstrained ODME can fit counts by inventing a new OD matrix (large `theta`, distorted origin/destination
totals). Bounded low-rank ODME keeps the adjustment small, interpretable, and stable — a count fit **plus** a
reasonable OD surface.

## [0.1.0] — reproducible kernel
- Matrix-free assignment operators, departure-profile recovery `phi(t)`, profile-basis / survey-informed
  regularization, calibration & reasonableness gates, one-link fluid-queue + congestion-duration diagnostics,
  public/synthetic benchmarks, private-data policy.
