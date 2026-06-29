import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from odme.physics import observed_duration, duration_gate


def test_observed_duration():
    speed = np.array([60, 60, 30, 25, 28, 60, 60.0])   # congested bins 2..4
    d = observed_duration(speed, cutoff=45.0, dt=0.25)
    assert d["t0"] == 2 and d["t3"] == 4 and abs(d["P"] - 0.75) < 1e-9


def test_gate_fail_when_no_queue():
    g = duration_gate(P_model=[0.0, 0.0], P_obs=[3.0, 2.5])
    assert g["verdict"] == "FAIL" and not g["queue_forms"]


def test_gate_pass_when_close():
    g = duration_gate(P_model=[3.0, 2.4], P_obs=[3.0, 2.5])
    assert g["verdict"] == "PASS" and g["RMSE_P"] < 0.5


if __name__ == "__main__":
    test_observed_duration(); test_gate_fail_when_no_queue(); test_gate_pass_when_close()
    print("test_congestion_duration: OK")
