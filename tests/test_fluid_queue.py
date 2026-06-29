import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from odme.physics import point_queue, mu_of_dc


def test_no_queue_below_capacity():
    lam = np.full(10, 1000.0)            # below mu
    q = point_queue(lam, 2000.0, 0.25)
    assert q["P"] == 0.0 and not q["queue_forms"]


def test_queue_forms_above_discharge():
    lam = np.array([500, 1500, 3000, 3000, 1500, 500.0])
    q = point_queue(lam, 1400.0, 0.25)
    assert q["queue_forms"] and q["P"] > 0 and q["Q"].max() > 0


def test_mu_of_dc_below_capacity_and_decreasing():
    C, f_d, n = 2200.0, 1.05, 1.06
    mu_low = mu_of_dc(C, f_d, n, 2.0)
    mu_high = mu_of_dc(C, f_d, n, 5.0)
    assert mu_low < C and mu_high < mu_low      # decreasing in D/C (capacity drop)


if __name__ == "__main__":
    test_no_queue_below_capacity(); test_queue_forms_above_discharge(); test_mu_of_dc_below_capacity_and_decreasing()
    print("test_fluid_queue: OK")
