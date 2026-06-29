"""Run every public example end-to-end and confirm the repo is reproducible (no private data).

Run:  python examples/run_full_reproducibility_check.py
"""
from __future__ import annotations
import os, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

EXAMPLES = ["run_queue_one_link.py", "run_phi_recovery.py", "run_profile_mixture.py",
            "run_matrix_free_operator.py", "run_tiny_panel.py"]
ok = True
for ex in EXAMPLES:
    r = subprocess.run([sys.executable, os.path.join(HERE, ex)], cwd=ROOT, capture_output=True, text=True)
    status = "OK" if r.returncode == 0 else "FAIL"
    ok = ok and r.returncode == 0
    print(f"[{status}] {ex}")
    if r.returncode != 0:
        print(r.stderr[-800:])
# privacy guard
r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "validate_no_private_data.py")],
                   cwd=ROOT, capture_output=True, text=True)
print(r.stdout.strip())
ok = ok and r.returncode == 0
print("\nREPRODUCIBILITY:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
