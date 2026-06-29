"""Verification gates (Gate 1-7) — the reproducible matrix-level checks.

Each gate returns a GateResult(status PASS/WARNING/FAIL, finding, detail). These are the
"is the computation graph correctly constructed and is the inverse problem well-posed?" checks
a student/agent must pass before trusting an ODME result.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np

from ..kernel import build_kernel, load_observations

REQUIRED_FILES = ["node.csv", "link.csv", "od.csv", "path.csv", "sensor.csv", "measurement.csv"]


@dataclass
class GateResult:
    gate: str
    status: str          # PASS | WARNING | FAIL
    finding: str
    detail: str = ""

    def line(self):
        return f"[{self.status:7}] {self.gate:28} {self.finding}" + (f"\n           {self.detail}" if self.detail else "")


def gate1_files(case_dir):
    missing = [f for f in REQUIRED_FILES if not os.path.exists(os.path.join(case_dir, f))]
    if missing:
        return GateResult("G1 file completeness", "FAIL", f"missing {missing}")
    return GateResult("G1 file completeness", "PASS", f"all {len(REQUIRED_FILES)} required files present")


def gate2_dims(K):
    P, Kk = K.R.shape; A, Pd = K.Delta.shape; S, Ad = K.M.shape
    ok = (Pd == P and Ad == A and len(K.d_seed) == Kk)
    msg = f"R[{P}x{Kk}] Delta[{A}x{Pd}] M[{S}x{Ad}] d[{len(K.d_seed)}] G[{K.G.shape[0]}x{K.G.shape[1]}]"
    return GateResult("G2 dimensions", "PASS" if ok else "FAIL",
                      "matrix shapes consistent" if ok else "shape mismatch", msg)


def gate3_conservation(case_dir, K):
    # OD-to-path shares sum to 1 per OD
    bad = []
    col_sum = K.R.sum(axis=0)
    for j, kid in enumerate(K.od_ids):
        if abs(col_sum[j] - 1.0) > 1e-6:
            bad.append((kid, round(float(col_sum[j]), 4)))
    if bad:
        return GateResult("G3 conservation (R cols=1)", "FAIL",
                          f"{len(bad)} OD pair(s) have path shares not summing to 1", str(bad))
    return GateResult("G3 conservation (R cols=1)", "PASS", "all OD path-shares sum to 1")


def gate4_nonneg(K):
    bad = [K.od_ids[i] for i, v in enumerate(K.d_seed) if v < 0]
    return GateResult("G4 nonnegativity", "PASS" if not bad else "FAIL",
                      "seed demand >= 0" if not bad else f"negative seed demand: {bad}")


def gate5_linkflow(K):
    # x = Delta R d_seed must be finite and nonnegative
    x = K.Delta @ K.R @ K.d_seed
    if np.any(x < -1e-9):
        return GateResult("G5 link-flow reconstruct", "FAIL", "x = Delta R d has negative entries")
    return GateResult("G5 link-flow reconstruct", "PASS",
                      f"x = Delta R d ok (total link flow {x.sum():.0f})")


def gate6_observation(case_dir, K):
    obs, periods = load_observations(case_dir)
    # aggregate observed over time for a static check
    y = np.array([sum(obs.get(s, {}).values()) for s in K.sensor_ids])
    yhat = K.assign(K.d_seed)
    res = y - yhat
    rel = np.abs(res) / np.maximum(y, 1.0)
    worst = K.sensor_ids[int(np.argmax(rel))] if len(rel) else "-"
    status = "PASS" if np.max(rel) < 0.15 else "WARNING"
    return GateResult("G6 observation residual", status,
                      f"seed reproduces counts within {100*np.max(rel):.0f}% (worst sensor {worst})",
                      f"y={y.round(1).tolist()} yhat_seed={yhat.round(1).tolist()}")


def gate7_rank(K):
    Kdim = K.G.shape[1]
    r = K.rank_G
    if r < Kdim:
        return GateResult("G7 underdetermination", "WARNING",
                          f"rank(G)={r} < #OD={Kdim}: OD recovery is UNDERDETERMINED",
                          "=> compression / prior / regularization required (justifies the engine)")
    return GateResult("G7 underdetermination", "PASS", f"rank(G)={r} = #OD={Kdim}: identifiable")


def run_verification(case_dir):
    results = [gate1_files(case_dir)]
    if results[0].status == "FAIL":
        return results
    K = build_kernel(case_dir)
    results += [gate2_dims(K), gate3_conservation(case_dir, K), gate4_nonneg(K),
                gate5_linkflow(K), gate6_observation(case_dir, K), gate7_rank(K)]
    return results
