"""Constraint audit: what is enforced vs missing for a physics-informed ODME.

Returns the audit table (status per constraint) so reports can state honestly what is and is not modeled.
"""
from __future__ import annotations

AUDIT = [
    ("phi >= 0",                       "enforced (projection)",          "pass"),
    ("sum_tau phi = 1",                "enforced (projection)",          "pass"),
    ("q_hat >= 0",                     "implied by nonneg H, q, phi",    "pass"),
    ("lambda_{a,t} >= 0 (inflow)",     "modeled only in physics layer",  "diagnostic"),
    ("s_{a,t} <= mu (discharge cap)",  "modeled only in physics layer",  "diagnostic"),
    ("Q_{a,t} >= 0 (queue)",           "modeled only in physics layer",  "diagnostic"),
    ("queue conservation",             "modeled only in physics layer",  "diagnostic"),
    ("P_model ~ P_obs",                "congestion-duration gate",       "gate"),
]


def constraint_audit() -> list[tuple[str, str, str]]:
    return list(AUDIT)


def print_audit():
    print(f"{'constraint':34} {'status':32} verdict")
    for c, s, v in AUDIT:
        print(f"{c:34} {s:32} {v}")
