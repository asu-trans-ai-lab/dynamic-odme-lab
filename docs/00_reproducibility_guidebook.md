# Reproducibility guidebook

1. **Repository setup** — clone, then `pip install -e .` (numpy, scipy, matplotlib, PyYAML).
2. **Environment** — Python ≥ 3.9; or `conda env create -f environment.yml`.
3. **Tiny case** — `python examples/run_tiny_panel.py` (constraint audit + four-node ODME).
4. **Matrix-free operator** — `python examples/run_matrix_free_operator.py` (Sioux Falls, `A = M·Δ·R`).
5. **Departure-profile recovery** — `python examples/run_phi_recovery.py` (φ(t) from link-time obs).
6. **Profile-basis mixture** — `python examples/run_profile_mixture.py` (purpose mix + envelope).
7. **One-link queue diagnosis** — `python examples/run_queue_one_link.py` (λ, μ(D/C), s, Q, P; diagnostic).
8. **Solver tests** — `pytest tests/` (queue, duration gate, φ-recovery, profiles, constraints, operator).
9. **Reproducibility check** — `python examples/run_full_reproducibility_check.py` (runs all + privacy guard).
10. **Private-data policy** — see `docs/09_private_data_policy.md`; run `scripts/validate_no_private_data.py`.
11. **Expected outputs** — each example prints its metrics; the public benchmarks ship expected gate reports.

**Honest status reminder:** the queue layer is *diagnostic*; the congestion-duration gate currently does not
pass on a pure forward queue (it requires the joint demand/μ calibration). Do not label any run
"physics-on" until that gate passes.
