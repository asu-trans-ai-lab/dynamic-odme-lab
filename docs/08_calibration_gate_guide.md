# Calibration gate guide

Gates score a calibration honestly and gate "physics-on" claims.

- **Constraint audit** (`odme.gates.constraint_audit`): which constraints are enforced (φ≥0, Σφ=1, q≥0) vs
  diagnostic (λ, s≤μ, Q≥0, queue conservation) vs gated (P_model≈P_obs).
- **Calibration gates** (`odme.gates.calibration_layers`): counts / VMT / VHT / OD-distortion vs thresholds.
- **Profile reasonableness** (`odme.gates.reasonableness`): recovered φ within the empirical envelope; flag
  unsupported early-AM shoulders.
- **Congestion-duration gate** (`odme.gates.congestion_duration_gate`): PASS only if a queue forms **and**
  `RMSE_P < 0.5 h`. **Currently FAILS** on a pure forward queue — so the queue layer stays *diagnostic*.

A version may not be called "physics-on" until: `P_model ≈ P_obs`, the queue forms, λ and μ are physically
interpretable, and speed consistency improves.
