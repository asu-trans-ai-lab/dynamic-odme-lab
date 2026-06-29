"""FTT/HFN demo on the tiny panel — explicit A, B, forward-backward, multi-source.

Shows: the A (path-link) and B (OD-path) matrices; the forward chain f_OD->f_P->f_L;
the adjoint gradient; and that count-only ODME is rank-deficient (cannot recover OD 2,
which no sensor sees) while adding ONE OD-layer observation (F2) recovers it exactly.

Run:  python -m odme.examples.ftt_demo
"""
from __future__ import annotations

import numpy as np

from ..kernel.ftt import FTT

CASE = "cases/00_tiny_panel"
D_TRUE = np.array([160.0, 120.0, 100.0])    # od_demand_true.csv totals (OD1, OD2, OD3)


def main():
    m = FTT(CASE)
    print("A = A_{P,L} (path x link), rows=paths cols=links:")
    print(m.A.toarray().astype(int))
    print("B = B_{OD,P} (OD x path), rows=OD cols=paths:")
    print(m.B.toarray())

    # synthesize consistent counts from the TRUE OD
    f_true = m.forward(D_TRUE)
    y_count = m.M @ f_true["f_L"]
    print(f"\nforward (true OD={D_TRUE.tolist()}):  f_L={f_true['f_L'].astype(int).tolist()}  "
          f"sensors M f_L = {y_count.tolist()}  (links {[m.link_ids[i] for i in m.M.indices]})")

    print(f"seed OD = {m.d_seed.tolist()}")
    g0 = m.grad_count(m.d_seed, y_count)
    print(f"adjoint grad_count at seed  dL/df_OD = B A M^T (M f_L - y) = {g0.round(2).tolist()}")
    print("  (note: OD 2's component is 0 -> no sensor sees it -> rank-deficient, see G7)")

    # rank of the assignment-visible operator M G = M A^T B^T
    MG = (m.M @ m.jacobian_link_od()).toarray()
    print(f"rank(M A^T B^T) = {np.linalg.matrix_rank(MG)}  vs  #OD = {len(m.od_ids)}  -> underdetermined\n")

    # --- count-only ODME ---
    d1, _ = m.solve(y_count, l3=1.0, iters=400)
    print(f"count-only ODME:        OD_hat = {d1.round(1).tolist()}   (true {D_TRUE.tolist()})")
    print(f"                        OD2 error = {abs(d1[1]-D_TRUE[1]):.1f}  <- unrecovered (no sensor)")

    # --- multi-source: add ONE OD-layer observation on OD 2 (mobile/F2) ---
    C_od = np.zeros((1, 3)); C_od[0, 1] = 1.0          # observe OD pair 2
    y_od = np.array([D_TRUE[1]])                        # its true volume
    d2, _ = m.solve(y_count, y_od=y_od, C_od=C_od, l3=1.0, l2=5.0, iters=400)
    print(f"\ncount + OD2 obs (F2):   OD_hat = {d2.round(1).tolist()}   (true {D_TRUE.tolist()})")
    print(f"                        OD2 error = {abs(d2[1]-D_TRUE[1]):.1f}  <- recovered by the OD-layer source")
    print("\n=> explicit A,B + adjoint backprop; multi-source (F2) breaks the count-only rank deficiency.")


if __name__ == "__main__":
    main()
