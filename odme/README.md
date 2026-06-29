# odme — unified static/dynamic ODME

One matrix **A**; **T (number of time intervals) is the only static/dynamic switch** (`T=1` ⇒ static).
See `../ODME_ARCHITECTURE_PLAN.md` for the full design.

## Run

```bash
cd dynamic-odme   # repo root

# Stage 0 only — data readiness check + filler (the user entrance)
python -m odme check cases/01_four_node

# Stage 0 + build A + solve at T (static when T=1)
python -m odme run   cases/01_four_node
python -m odme run   cases/01_four_node --approx --iterations 60
```

`--approx` synthesizes forced-through columns for measured links that no column covers
(the "approximate / inherit" A source), so the gradient solver can fit them.

## Pipeline (matches the plan)

```
readiness/  Stage 0  load + fill (TAPLite-style defaults) -> checks -> readiness_report.md + VERDICT
matrix/     Stage 1  build_A (source adapters: columns | approximate | ...) + build_R (identity)
solve/      Stage 1  gradient_deviation (port of DTALite ODME.h), operates on (link,t) cells
report/              validate -> odme_link_volume_validation.csv ; solver -> odme_log.csv
```

## Status (v0.1)

| Piece | State |
|---|---|
| Stage 0 readiness + filler + report | working |
| `from_columns` source (TAPLite/Path4GMNS schema) | working |
| `approximate` source (Dijkstra forced-through) | working (Case 01) |
| `from_external` source (geometry paths → columns, auto-orient) | working (Case 02, `io/external_paths.py`) |
| measurement Path A / B / C | working (Cases 01 / 03 / 02) |
| gradient-deviation solver at `T=1` | working across the static ladder (below) |
| `build_R` aggregation | identity only (screenline/corridor TODO) |
| `from_trajectory` / `from_link_perf` adapters, φ reader, `T>1` | in progress (Stages 2–3) |

### Static ladder — all three measurement paths proven

| Case | Network | path | counts | fit | note |
|---|---|---|---|---|---|
| 01 | Four-Node (4 links) | A | 1 | MAPE 23%→1.0% | needs `--approx` (uncovered link) |
| 02 | Sioux Falls (76 links) | C | 71 | **R²=0.9996, MAPE 5.7%** | **cross-engine vs TCGlite R²=0.9998** |
| 03 | West Jordan (378 links) | B | 20 | **R²=0.974, MAPE 4.6%** | real `measurement.csv` |

### Dynamic (`T>1`) — round-trip AND real data

- `python -m odme.examples.dynamic_roundtrip` — the *unmodified* `build_A`+solver run at T=3 on Case 02's
  real columns recover a known φ-split truth from a perturbed seed (**R² 0.78 → 0.992**); **T=1 guard = R²=0.9996**.
- `python -m odme.examples.phi_benchmark cases/07_i405_pm` — **rigorous, realistically-regularized** φ(t) recovery.
  Seeds from FLAT / PIECEWISE departure profiles (not the truth), enforces **OD-total conservation**, and reports
  link MAPE + φ R². Honest result: ODME ~halves link MAPE vs flat (e.g. I405 138%→51%) and lifts
  φ R² (0.88→0.98), but stays observability-limited — *not* a misleading R²=0.999. See `../docs/REVIEW_corridors.md`.

### Dynamic ODME-ready corridor cases (GMNS + time-dependent)

`cases/06_i10_pm` (6 OD), `07_i405_pm` (186 OD) — each with
`network/{node,link,measurement}.csv` + `columns_timedependent.csv` + `linkflow_timedependent.csv` +
`od_timedependent.csv`. Single path per OD ⇒ clean φ(t) problem. Target OD = upstream assignment *estimate*
(no independent truth).

## Outputs (written into the case dir)

`readiness_report.md`, `matrix_A.csv`, `odme_log.csv` (per-iteration MOEs),
`odme_link_volume_validation.csv` (obs vs est, deviation, covered flag, source path).
