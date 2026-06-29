# QVDF queue physics guide (experimental / diagnostic)

> **The queue layer is diagnostic, not production.** A model that improves φ(t) and link-flow WMAPE is
> **not** physics-informed until it reproduces congestion **duration** and queue evolution.

## Discharge rate is NOT the ultimate capacity
During congestion the bottleneck discharges at the **queue discharge rate** (capacity drop), well below the
free-flow capacity `C`. Using `μ = C` makes the queue **never form** (throughput ≤ C by definition). The
calibrated QVDF discharge rate is a function of the demand/capacity ratio:
$$\mu(D/C) = \frac{C}{f_d}\,(D/C)^{1-n} \;<\; C \quad(\text{decreasing in } D/C),$$
from `P = f_d (D/C)^n` and the consistency `D = P·μ`. (`odme.physics.qvdf.mu_of_dc`.)

## Forward queue and the hard gate
`odme.physics.point_queue(λ, μ, dt)` runs `s=min(μ, λ+Q/dt)`, `Q⁺=[Q+dt(λ−s)]₊`; duration `P = #{Q>0}·dt`.
`odme.gates.congestion_duration_gate.duration_gate(P_model, P_obs)` returns `RMSE_P` and a **PASS/FAIL**
verdict — PASS only if a queue forms **and** `RMSE_P < 0.5 h`.

## What passes / what does not (current)
- `μ = capacity`, throughput-as-λ → **no queue, FAIL**.
- `μ = μ(D/C)` + peaked arrival demand → queue forms; duration approaches observed but exact match needs
  the **joint demand/μ calibration** against `P_obs` (open item).
- Speed consistency under a static VDF is still poor (open item); use the QVDF congested branch.

## μ(D/C) for future-year scenarios
`μ` is fixed from the base-year QVDF calibration; for future years it is **re-evaluated via `μ(D/C)`** as
demand grows — the discharge rate is a calibrated function, not a constant.

See `examples/run_queue_one_link.py` and `tests/test_fluid_queue.py` / `tests/test_congestion_duration.py`.
