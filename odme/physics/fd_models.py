"""Fundamental-diagram model wrappers (speed<->flow) for the physics layer."""
from __future__ import annotations
from dataclasses import dataclass
from .qvdf import s3_speed, s3_invert_flow, bpr_speed


@dataclass
class FD_S3:
    """Three-parameter (S3) fundamental diagram."""
    v_f: float = 70.0
    k_c: float = 44.4
    m: float = 4.0

    def speed(self, k):
        return s3_speed(k, self.v_f, self.k_c, self.m)

    def flow_from_speed(self, v, branch="free"):
        return s3_invert_flow(v, self.v_f, self.k_c, self.m, branch)


@dataclass
class FD_BPR:
    """BPR volume-delay function."""
    C: float = 2200.0
    v_f: float = 70.0
    alpha: float = 0.15
    beta: float = 4.0

    def speed(self, q):
        return bpr_speed(q, self.C, self.v_f, self.alpha, self.beta)
