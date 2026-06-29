# Matrix-free sparse assignment operator + compression (ARC-scale)

Per the directive: **never materialize dense A**. Build A as a composition of sparse operators
`A = M Δ R`, expose `matvec`/`rmatvec`, and judge compression by **assignment-visible calibration
metrics**, not matrix reconstruction error. Code: `odme/operator/`. Run: `python -m odme.operator.benchmark`.

## The operator (`assignment_operator.py`)
From a column file + link.csv, store only: sparse path-link incidence **Δ** (CSR), path→OD index,
path share **R**. Then matrix-free:
- `matvec(d) = Δᵀ(R ⊙ d[path_od])` → link flow `x` ( = Δ R d )
- `rmatvec(r) = Σ_p share_p (Δ_p·r)` → OD gradient ( = (ΔR)ᵀ r ) — the ODME gradient
- `aggregate(x)` → VMT, VHT; `grouped(x, M)` → counts/screenline/corridor (M = link→group)
- exposed as `scipy.sparse.linalg.LinearOperator` so any large solver uses it without forming |L|×|OD|.

## Experiment 1 — exact sparse baseline (Chicago Sketch)
| OD pairs | paths | links | nnz(Δ) | **operator memory** | dense |L|×|OD| | matvec | rmatvec |
|---|---|---|---|---|---|---|---|
| 93,135 | 118,445 | 2,950 | 1.54 M | **20.4 MB** | 2 GB (never built) | 2.2 ms | 3.6 ms |

For ARC the dense `146k × 1.4M` would be ≈ **1.6 TB** — the sparse operator stays in tens of MB.

## Experiment 2 — active path pruning judged by calibration metrics
| scheme | paths kept | E_link | E_VMT | E_VHT | E_count |
|---|---|---|---|---|---|
| top-1 path/OD | 79% | 2.84% | **0.01%** | 0.08% | 2.56% |
| top-2 | 93% | 0.50% | 0.00% | 0.01% | 0.46% |
| top-3 | 98% | 0.13% | 0.00% | 0.00% | 0.12% |
| cum-95% flow | 96% | 0.13% | 0.01% | 0.01% | 0.13% |

**Reading:** even one path per OD keeps VMT/VHT error at ~0.01% — acceptable under the gates while
discarding 21% of paths. Compression is accepted because `E_count/E_VMT/E_VHT` stay inside the
calibration thresholds, **not** because the matrix is reconstructed.

## Compression options (the menu)
| option | status |
|---|---|
| 1. exact sparse (Δ CSR + share + od_index) | ✅ baseline (`build_operator`) |
| 2. active path pruning (top-K / share≥ε / cum-flow) | ✅ (`prune_paths`) |
| 3. OD basis `d = U z` (county/district/distance-band/tensor) | ⬜ next (interpretable, not blind SVD) |
| 4. link/corridor aggregation `ȳ = C x` (counts/screenline/segments/VMT) | ✅ via `grouped(x, M)` |
| 5. random projection / sketching `S A` | ⬜ |
| 6. CUR / column sampling (high-demand / high-residual OD) | ⬜ |
| 7. route-signature / shared-segment dictionary | ⬜ (good for ARC freeway corridors) |
| 8. hierarchical spatial (zone→district→county; refine only where residual) | ⬜ (agentic) |

## ARC at agency scale — DONE
**Super-zone TAPLite FW** (1,431 super-zones from 6,031, full 158k-link network) ran in **4 min at 8.9 GB**
(vs 38 GB for the full run) and emitted **1,056,688 columns (2.0 GB)**. The matrix-free operator built on it:

### Experiment 1 — ARC exact sparse operator
| OD pairs | paths | links | nnz(Δ) | **operator memory** | dense |L|×|OD| | matvec | rmatvec |
|---|---|---|---|---|---|---|---|
| 322,522 | 1,056,688 | 158,033 | 153 M | **1,858 MB** | **408 GB** (never built) | 226 ms | 256 ms |

The full regional operator is **1.86 GB sparse** vs **408 GB dense** — and `matvec`/`rmatvec` (the ODME
forward/gradient) run in ~0.25 s on the whole metro.

### Experiment 2 — ARC path pruning vs calibration error (3.3 paths/OD ⇒ real compression)
| scheme | paths kept | E_link | E_VMT | E_VHT | E_count |
|---|---|---|---|---|---|
| top-1 path/OD | **31%** | 6.47% | **0.18%** | 0.14% | 6.56% |
| top-2 | 54% | 3.13% | 0.10% | 0.14% | 3.14% |
| cum-95% flow | 83% | 1.07% | **0.01%** | 0.08% | 1.08% |
| cum-99% | 98% | 0.06% | 0.00% | 0.00% | 0.06% |

Keeping the top path per OD (a **3.2× path reduction**) holds VMT/VHT error at ~0.15% — inside any gate —
while count error is 6.6% (acceptable for sketch use). This is the compressed-optimization claim, on a real
146k-link MPO network.

## OD-basis compression (Option 3) — unknowns reduction proven, resolution trade-off is real
`od_basis.py`: cluster zones → districts → district-pair latent `z`, `d = U z` (prior within-block split).
Chicago unknowns: **93,135 OD → 188 / 1,637 / 5,603** district-pairs (495× / 57× / 17× fewer). The honest
finding: an OD basis cannot represent *within-block* per-OD variation, so on the random-per-OD test it fits the
aggregate but leaves within-block error — it is the right tool for **structural/aggregate** corrections and
regularization (few, interpretable unknowns), **not** for recovering individual OD detail (that needs the full
operator or an OD-layer data source, per `HFN_MULTISOURCE.md`). [demo seed-scaling to be tightened.]

## Closing the loop
TAPLite FW columns → sparse `A = M Δ R` (1.86 GB, never 408 GB dense) → path-pruning / OD-basis compression →
**calibration-gated** error (`gates/calibration_layers.py`). The ARC operator is ready for the Section-7 gates
and ODME against the observed counts.

## Message
> We compress the OD→path→link→observation operator while preserving calibration-relevant outputs
> (VMT, VHT, V/C, counts, screenlines, corridors). Error is evaluated by assignment-visible metrics under
> transportation calibration gates — not by matrix reconstruction loss. That is the bridge from the TAPLite
> kernel to compressed optimization and the flow tensor.
