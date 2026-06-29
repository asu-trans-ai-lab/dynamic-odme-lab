"""Measurement aggregation R: (link,t) cells -> measurement groups.

v0 ships identity (R=I, raw link counts). Screenline/corridor grouping plugs in here later
without touching the solver; the model stays y = R A x for all R.
"""
from __future__ import annotations


class IdentityR:
    """R = I — each measured cell is its own group."""

    def groups(self, measured_cells):
        # group_key -> list of cells
        return {cell: [cell] for cell in measured_cells}


def build_R(case, kind: str = "identity"):
    return IdentityR()
