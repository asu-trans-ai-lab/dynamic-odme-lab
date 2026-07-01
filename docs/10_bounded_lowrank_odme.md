# Bounded low-rank ODME

ODME should be a **small, bounded, low-rank correction** to an *already reasonable* OD matrix — not a tool to
reconstruct demand or to compensate for inconsistent counts, wrong period factors, missing demand, or
assignment-loading errors.

## Formulation
Treat the OD adjustment as a **multiplicative correction surface**:

```
Q_new(i,j) = theta_ij * Q_base(i,j)
log theta_ij = mu + O_i + D_j (+ sum_r U_i[r] V_j[r])       # low-rank: systemwide + origin + destination + small interaction
subject to   (1 - b) <= theta_ij <= (1 + b)                # hard per-pair bound, default b = 0.10
```

Because every OD pair is bounded within ±b, the **origin production** `P_i = sum_j Q_ij` and **destination
attraction** `A_j = sum_i Q_ij` automatically stay within ±b as well (we still report them explicitly — they
are easier for planners to read).

The objective minimizes the count-fitting error (link/screenline) plus ridge penalties on the origin,
destination, and interaction effects, so the surface stays low-rank and interpretable.

## API
```python
from odme.bounded import bounded_lowrank_odme, three_version_comparison

res = bounded_lowrank_odme(matvec, rmatvec, d0, od_origin, od_dest, S, y, bound=0.10, rank=2,
                           calibrate=c)     # c: optional per-link factor so c*matvec(d0) matches the base counts
res.theta          # per-OD adjustment ratio, guaranteed within [1-bound, 1+bound]
res.fit            # {R2, WMAPE, ratio} of counts after adjustment
res.diagnostics    # median/p5/p95 theta, origin/dest ranges, od_explained_pct, total_change_pct, ...

rows, v2 = three_version_comparison(matvec, rmatvec, d0, od_origin, od_dest, S, y, bound=0.10)
# rows = V0 (no ODME), V1 (unconstrained), V2 (bounded)  -> the recommended reporting table
```
`matvec(d)` maps OD → link volumes; `rmatvec(r)` maps link residuals → OD; `S` (n_counts × L) is the
count-incidence (e.g. screenline membership); `y` are the observed count totals.

## Recommended three-version comparison
| Version | Description | Purpose |
|---|---|---|
| **V0** | no ODME | baseline assignment/loading fit |
| **V1** | unconstrained low-rank ODME | maximum count fit — usually overfits (large theta, distorted totals) |
| **V2** | **bounded ±b low-rank ODME** | **preferred production method** |

## Acceptance criteria for V2
| check | rule |
|---|---|
| screenline/count fit | R² not worse than V0 (usually slightly better) |
| % OD pairs outside ±b | **0%** (hard bound) |
| origin production change | within ±b |
| destination attraction change | within ±b |
| O+D explained variance of `log theta` | high (adjustment is low-rank / interpretable) |
| sector-to-sector map & log(theta) heatmap | no isolated unreasonable jumps |

## Diagnostic rule
> If the counts **cannot** be matched within ±b, do **not** widen the bound. That is a signal to fix the
> **base demand, period factors, count matching (duplicate/forecast counts), external/truck demand, or
> assignment loading** upstream. A near-boundary median theta (many pairs clipped to the same side) usually
> means a **systemwide level** issue (period factor or base a few % off), not an OD-structure problem.

A good ODME result is not just a good R² against counts — it is a good count fit **plus** a reasonable,
low-rank OD adjustment surface.
