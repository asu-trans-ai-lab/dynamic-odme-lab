"""Build the matrix-free assignment operator A = M Delta R on a bundled public case and run ODME.

Uses the Sioux Falls benchmark (public). Demonstrates the operator + a static ODME fit.

Run:  python examples/run_matrix_free_operator.py
"""
from __future__ import annotations
import os, sys, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# The bundled odme package runs the full readiness -> build_A -> solve pipeline on a case directory.
case = os.path.join("benchmarks", "02_sioux_falls")
print(f"Running static ODME on the public benchmark: {case}")
r = subprocess.run([sys.executable, "-m", "odme", "run", case, "--iterations", "80"],
                   cwd=ROOT, capture_output=True, text=True)
print(r.stdout[-1500:] if r.stdout else "")
if r.returncode != 0:
    print("STDERR:", r.stderr[-1500:])
print("\n(Operator internals: odme.operator.assignment_operator builds A = M.Delta.R matrix-free;\n"
      " see docs/03_matrix_free_operator_guide.md.)")
