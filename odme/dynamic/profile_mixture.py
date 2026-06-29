"""Purpose-mixture departure profile: phi = sum_k alpha_k p_k + delta, alpha>=0, sum alpha = 1.

Fit the convex mixture weights to a target shape by non-negative least squares (simplex-renormalized),
so a behaviorally-bounded blend can explain an observed flow shape without free over-fitting.
"""
from __future__ import annotations
import numpy as np
from scipy.optimize import nnls
from .profile_library import normalize


def fit_mixture(target, basis_profiles) -> dict:
    """min ||B a - target||  s.t. a>=0 ; renormalize a to the simplex. Returns weights, mix, residual."""
    target = normalize(target)
    B = np.vstack([normalize(p) for p in basis_profiles]).T   # T x K
    a, _ = nnls(B, target)
    a = a / a.sum() if a.sum() > 0 else np.ones(B.shape[1]) / B.shape[1]
    mix = normalize(B @ a)
    delta = target - mix
    return dict(weights=a, mixture=mix, delta_l1=float(np.abs(delta).sum()),
                delta_l2=float(np.linalg.norm(delta)))
