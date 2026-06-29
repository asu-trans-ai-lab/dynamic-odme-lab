"""Stage 0 — data readiness check & filler (the user entrance)."""
from .loaders import load_case
from .checks import run_checks
from .report import build_report, write_report

__all__ = ["load_case", "run_checks", "build_report", "write_report"]
