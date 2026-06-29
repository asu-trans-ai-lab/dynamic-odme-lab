import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from odme.gates.constraint_audit import constraint_audit
from odme.cli import get_config


def test_constraint_audit_marks_queue_diagnostic():
    audit = dict((c, v) for c, _, v in constraint_audit())
    assert audit["phi >= 0"] == "pass"
    assert audit["Q_{a,t} >= 0 (queue)"] == "diagnostic"   # queue is diagnostic, not enforced


def test_queue_never_on():
    for ver in ("v1_baseline", "v2_profile_enhanced", "v3_physics_diagnostic"):
        cfg = get_config(ver)
        assert cfg["queue_layer"] in ("off", "diagnostic")  # never 'on'


if __name__ == "__main__":
    test_constraint_audit_marks_queue_diagnostic(); test_queue_never_on(); print("test_constraints: OK")
