"""Fit a purpose-mixture departure profile to a target shape, and check the empirical envelope (public).

Run:  python examples/run_profile_mixture.py
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from odme.dynamic import fit_mixture, normalize, envelope
from odme.dynamic.profile_library import in_envelope

T = 20
tt = np.arange(T)
# synthetic public profile bases (stand-ins for survey HBW/HBO/NHB + a detector profile)
p_hbw = normalize(np.exp(-0.5 * ((tt - 12) / 2.2) ** 2))            # sharp AM/PM commute peak
p_hbo = normalize(np.exp(-0.5 * ((tt - 10) / 4.0) ** 2))           # broader
p_nhb = normalize(0.4 + 0.6 * (tt / (T - 1)))                      # rising
basis = [p_hbw, p_hbo, p_nhb]
lo, hi = envelope(basis)

# a target flow shape (e.g. an observed corridor profile)
target = normalize(0.5 * p_hbw + 0.3 * p_hbo + 0.2 * p_nhb + 0.02 * np.abs(np.sin(tt)))
res = fit_mixture(target, basis)
print("fitted mixture weights (HBW, HBO, NHB):", np.round(res["weights"], 3))
print("residual L1 share:", round(res["delta_l1"], 3))
print("mixture in-envelope:", round(in_envelope(res["mixture"], lo, hi) * 100, 0), "%")
print("target  in-envelope:", round(in_envelope(target, lo, hi) * 100, 0), "%")
