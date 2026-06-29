# Solver testing guide

| Solver | Purpose |
|---|---|
| Projected gradient | φ simplex-constrained departure-profile recovery (the **validated baseline**) |
| L-BFGS-B | bounded physical params (μ, C, α, β) — reserved for the physics layer |
| Alternating | update φ, then queue/QVDF params, then queue posterior; repeat |
| Lambda sweep | profile-fit vs reasonableness trade-off (OD-prior / target weight) |
| Matrix-free CG/LSQR | large ODME normal-equation tests on the matrix-free operator |
| One-link queue calibration | μ sensitivity and P matching |

**Important:** the current **validated baseline is NOT BFGS**. It is **projected first-order** recovery with
OD-conservation projection (`odme.dynamic.phi_recovery.recover_phi`). BFGS / L-BFGS-B should be used only for
the **bounded physical parameters** once the queue layer is being calibrated — within an **alternating**
(projected-gradient for φ ↔ L-BFGS-B for μ/QVDF) scheme, which is more stable than solving everything at
once.

Tests: `tests/test_phi_recovery.py` (conservation, non-negativity, peak recovery),
`tests/test_fluid_queue.py`, `tests/test_congestion_duration.py`.
