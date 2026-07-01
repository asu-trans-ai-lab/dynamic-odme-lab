# Dynamic ODME Lab

A **reproducible research kernel** for dynamic Origin–Destination Matrix Estimation (ODME): matrix-free
assignment operators, time-dependent **departure-profile recovery**, profile-basis / survey-informed
regularization, calibration & reasonableness **gates**, and **experimental** queue/QVDF diagnostics.

> **Honest scope.** This is *departure-profile recovery embedded in a corridor*, plus **diagnostic** queue
> analysis — **not** validated full-network dynamic ODME, and **not** production "physics-informed" ODME.
> The queue layer is **never "on"**: it stays *diagnostic/experimental* until the congestion-duration gate
> passes (model queue forms and `P_model ≈ P_obs`). First release: **`v0.1.0-reproducible-kernel`**.

## What this repo does
- Builds **matrix-free** assignment operators (`A = M·Δ·R`, never densified).
- Recovers **time-dependent departure profiles** `φ(t)` (OD totals fixed; projected first-order solver).
- Tests **profile-basis** and **survey/PeMS-informed** regularization and **purpose mixtures**.
- Runs **bounded low-rank OD adjustment** (`odme.bounded`): ODME as a small ±10%, interpretable
  origin/destination correction surface — not cell-by-cell demand reconstruction.
- Provides **calibration** and **reasonableness** gates + a **constraint audit**.
- Supports **one-link fluid-queue** diagnostics and a **congestion-duration gate**.
- **Separates public benchmarks from private agency data** (NVTA is a private, local-only pack).

## What this repo does *not* claim (yet)
- It does **not** provide validated full-network dynamic ODME.
- It does **not** claim production physics-informed ODME until the congestion-duration gate passes.
- It does **not** include any private NVTA / VDOT / INRIX / RITIS / CBI data.

## Install
```bash
pip install -e .          # numpy, scipy, matplotlib, PyYAML
```

## Quick start (all public / synthetic)
```bash
python examples/run_tiny_panel.py            # OD-path-link mapping + constraint audit
python examples/run_matrix_free_operator.py  # A = M·Δ·R on the public Sioux Falls benchmark
python examples/run_phi_recovery.py          # recover φ(t) from link-time observations
python examples/run_profile_mixture.py       # purpose-mixture + empirical envelope
python examples/run_queue_one_link.py        # λ, μ(D/C), s, Q, P for one congested link (diagnostic)
python examples/run_bounded_odme.py          # bounded ±10% low-rank OD adjustment (V0/V1/V2)
python examples/run_observability_gate.py    # sensor-coverage gate: unobserved OD frozen at θ=1
python examples/run_full_reproducibility_check.py
pytest tests/
```

## Version presets (honest feature switch)
| version | seed + reg | queue | duration gate |
|---|---|---|---|
| `v1_baseline` | flat, none | off | off |
| `v2_profile_enhanced` | survey/mixture + reg | **off** | off |
| `v3_physics_diagnostic` | survey/mixture + reg | **diagnostic** | on |

```bash
python -m odme.cli.main v3_physics_diagnostic   # prints the resolved config (queue = diagnostic, never "on")
```

## Benchmarks (public → private)
| Stage | Case | Purpose |
|---|---|---|
| 0 | `benchmarks/00_tiny_panel` | matrix dims, OD-path-link mapping, conservation |
| 1 | `benchmarks/01_four_node` | TAPLite/DTALite columns + route assignment |
| 2 | `benchmarks/02_sioux_falls` | reproducible operator + static ODME |
| 3 | `benchmarks/03_west_jordan_utah` | larger public network |
| 4 | `benchmarks/04_arc_superzone` | agency-scale operator (condensed result artifacts) |
| 5 | `benchmarks/99_private_nvta_manifest_only` | **manifest only** — private NVTA pack runs locally |

## Private data policy
NVTA / VDOT / INRIX / RITIS / CBI data are **never committed**. The public repo contains the reproducible
kernel, teaching/public benchmarks, documentation, and expected artifact schemas; private results are
regenerated **locally** when authorized data are present under `data_private/`. See
[docs/09_private_data_policy.md](docs/09_private_data_policy.md) and run
`python scripts/validate_no_private_data.py` before any commit.

## Docs
[reproducibility guidebook](docs/00_reproducibility_guidebook.md) ·
[formulation guide](docs/01_formulation_teaching_guide.md) ·
[data dictionary](docs/02_input_data_dictionary.md) ·
[matrix-free operator](docs/03_matrix_free_operator_guide.md) ·
[QVDF queue physics](docs/06_qvdf_queue_physics_guide.md) ·
[bounded low-rank ODME](docs/10_bounded_lowrank_odme.md) ·
[private data policy](docs/09_private_data_policy.md)

## License
MIT — see [LICENSE](LICENSE).
