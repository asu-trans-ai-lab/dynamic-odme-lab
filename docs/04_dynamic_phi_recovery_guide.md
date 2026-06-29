# Dynamic φ(t) recovery guide

Recover the departure-time profile `φ_{r,τ}` so the time-expanded operator reproduces observed link-time
flows, with **OD totals fixed** (this is *departure-profile* ODME, not full OD-magnitude ODME).

- API: `odme.dynamic.recover_phi(G, y, groups, X, T, seed=, lam_smooth=, lam_curv=, lam_target=, target=)`.
- Seed from a **survey/behavioral base** (not flat); add smoothness/curvature/target penalties to keep the
  recovered shape behaviorally reasonable (`odme.dynamic.profile_library`, `profile_mixture`).
- Constraints `φ≥0`, `Σ_τ φ=1` are enforced by projection (machine-precision conservation).
- Example: `examples/run_phi_recovery.py`. Workflow: seed OD + base profile → build `G` → adjust
  time-dependent OD vs **link-level volumes** on fixed routes → recovered `φ(t)`.
