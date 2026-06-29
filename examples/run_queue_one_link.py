"""Diagnose lambda, mu, s, Q, P for ONE congested link (synthetic, public).

Demonstrates the discharge-rate correction: with mu = ultimate capacity the queue cannot form; with the
calibrated QVDF discharge rate mu(D/C) < C and a peaked demand, a queue forms and the duration is recovered.

Run:  python examples/run_queue_one_link.py
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from odme.physics import point_queue, mu_of_dc, observed_duration, duration_gate

# --- synthetic congested link (PM peak, 24 x 15-min bins from 14:00) ---
T, dt, h0, C = 24, 0.25, 14.0, 2200.0       # capacity vphpl
f_d, n, DC = 1.05, 1.06, 2.9                # QVDF params + demand/capacity ratio
t2 = 12                                      # trough bin (~17:00)
tt = np.arange(T)

mu_cap = C                                   # WRONG: ultimate (free-flow) capacity
mu_q = mu_of_dc(C, f_d, n, DC)               # calibrated discharge rate (capacity drop)

# peaked arrival demand whose peak sits BETWEEN the discharge rate and ultimate capacity:
# -> with mu = capacity the queue cannot form; with mu = mu(D/C) it does (the discharge-rate correction).
demand_peak = 1.06 * mu_q
lam = demand_peak * np.exp(-0.5 * ((tt - t2) / 3.0) ** 2)
v_f = 70.0
speed = np.where(lam > mu_q, 24.0, 58.0)     # congested while arrivals exceed the discharge rate

q_cap = point_queue(lam, mu_cap, dt)
q_dis = point_queue(lam, mu_q, dt)
obs = observed_duration(speed, cutoff=49.0, dt=dt)

print(f"demand peak = {demand_peak:.0f} vph | mu_capacity = {mu_cap:.0f} | mu(D/C) = {mu_q:.0f} vphpl")
print(f"observed congestion duration P_obs = {obs['P']:.2f} h "
      f"(t0={h0+obs['t0']*dt:.2f}h .. t3={h0+obs['t3']*dt:.2f}h)")
print(f"  mu = capacity   -> P_model = {q_cap['P']:.2f} h, queue_forms={q_cap['queue_forms']}")
print(f"  mu = qdf*cap     -> P_model = {q_dis['P']:.2f} h, queue_forms={q_dis['queue_forms']}, "
      f"Qmax={q_dis['Q'].max():.0f} veh")
gate = duration_gate([q_dis['P']], [obs['P']])
print(f"duration gate (discharge-rate queue): RMSE_P={gate['RMSE_P']:.2f} h -> {gate['verdict']}")
print("\nThis is a DIAGNOSTIC: the discharge-rate correction makes the queue form; exact validation "
      "still requires the joint demand/mu calibration against observed duration.")
