"""Pluggable A-source adapters. Each emits (link_id, t, col_idx, proportion)."""
from . import from_columns

ADAPTERS = {"columns": from_columns}

__all__ = ["from_columns", "ADAPTERS"]
