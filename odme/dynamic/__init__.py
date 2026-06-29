"""Dynamic (time-dependent) ODME: departure-profile recovery, profile library, and mixture.

The corridor experiments here are DEPARTURE-PROFILE recovery with fixed OD totals -- not full
metro-wide OD-magnitude ODME. See docs/04_dynamic_phi_recovery_guide.md.
"""
from .profile_library import normalize, envelope, profile_diagnostics
from .profile_mixture import fit_mixture
from .phi_recovery import recover_phi, grid_columns

__all__ = ["normalize", "envelope", "profile_diagnostics", "fit_mixture",
           "recover_phi", "grid_columns"]
