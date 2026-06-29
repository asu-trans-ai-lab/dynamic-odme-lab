import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from odme.dynamic import normalize, envelope, fit_mixture
from odme.dynamic.profile_library import in_envelope, profile_diagnostics


def test_normalize_sums_to_one():
    p = normalize([1, 2, 3, 4.0]); assert abs(p.sum() - 1.0) < 1e-12 and (p >= 0).all()


def test_envelope_and_membership():
    a = normalize([1, 2, 3, 2.0]); b = normalize([2, 2, 2, 2.0])
    lo, hi = envelope([a, b])
    assert in_envelope(a, lo, hi) == 1.0


def test_mixture_weights_simplex():
    T = 12; tt = np.arange(T)
    b = [normalize(np.exp(-0.5*((tt-6)/2)**2)), normalize(0.5+0.5*tt/(T-1))]
    res = fit_mixture(normalize(0.7*b[0]+0.3*b[1]), b)
    assert abs(res["weights"].sum() - 1.0) < 1e-9 and (res["weights"] >= 0).all()


if __name__ == "__main__":
    test_normalize_sums_to_one(); test_envelope_and_membership(); test_mixture_weights_simplex()
    print("test_profile_library: OK")
