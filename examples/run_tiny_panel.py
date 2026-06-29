"""Tiny smoke case: verify OD-path-link mapping, nonnegativity, and the constraint audit (public).

Run:  python examples/run_tiny_panel.py
"""
from __future__ import annotations
import os, sys, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from odme.gates.constraint_audit import print_audit

print("=== constraint audit (what is enforced vs diagnostic) ===")
print_audit()
print("\n=== four-node readiness + ODME (public benchmark) ===")
case = os.path.join("benchmarks", "01_four_node")
r = subprocess.run([sys.executable, "-m", "odme", "run", case, "--approx", "--iterations", "60"],
                   cwd=ROOT, capture_output=True, text=True)
print(r.stdout[-1200:] if r.stdout else r.stderr[-1200:])
