# Formulation teaching guide

## Static assignment operator (matrix-free)
$$h = R\,d, \qquad x = \Delta h = \Delta R\,d, \qquad y = M x = M\,\Delta\,R\,d$$
- `d` OD demand · `R` route choice / path shares · `Δ` path→link incidence · `M` link→observation.
- `A = M·Δ·R` is kept **matrix-free** (sparse `Δ` + shares), never densified.

## Dynamic (time-dependent) form
$$\hat y_{a,t} = \sum_r \sum_\tau H_{a,t,r,\tau}\, q_r\, \phi_{r,\tau}$$
- `q_r` OD total · `φ_{r,τ}` departure-time profile · `H` time-dependent propagation (departure bin τ +
  travel-time offset).

## Departure-profile constraints
$$\phi_{r,\tau} \ge 0, \qquad \sum_\tau \phi_{r,\tau} = 1$$
Recovered by a **projected first-order** solver (conservation + non-negativity projection); optional
smoothness / curvature / target-profile penalties. **This baseline is NOT BFGS** — L-BFGS-B is reserved for
bounded physical parameters.

## Queue (physics, diagnostic)
$$Q_{t+\Delta t} = \max\!\big(0,\, Q_t + \Delta t(\lambda_t - s_t)\big), \qquad
  s_t = \min\!\big(\mu,\, \lambda_t + Q_t/\Delta t\big)$$
QVDF discharge rate (capacity drop): $\mu(D/C) = (C/f_d)\,(D/C)^{1-n} < C$; duration $P = T_3 - T_0$.

## The ladder (what each stage is — and is not)
| Stage | Meaning |
|---|---|
| link-time mapping | OD→link-time proportions, no internal queue |
| departure-profile recovery | re-estimate `φ(t)` with OD totals **fixed** |
| matrix-free ODME | the above with `A = M·Δ·R` never densified |
| profile-basis compression | `φ_r = Σ_k α_{r,k} p_k + δ_r`, K ≪ T |
| fluid-queue diagnosis | per-link λ, μ, s, Q, P from speed/demand (diagnostic) |
| **full physics-informed ODME** | **not yet** — requires the congestion-duration gate to pass |
