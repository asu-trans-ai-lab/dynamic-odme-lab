"""Assemble a labeled departure-profile library + empirical envelope from registered sources."""
from __future__ import annotations
import numpy as np
from .source_registry import SOURCE_REGISTRY
from ..dynamic.profile_library import normalize, envelope, in_envelope


def build_library(profiles: dict) -> dict:
    """profiles: {source_key: array}. Returns normalized library + per-bin empirical envelope."""
    lib = {k: normalize(p) for k, p in profiles.items()}
    lo, hi = envelope(list(lib.values()))
    return dict(library=lib, env_lo=lo, env_hi=hi,
                provenance={k: SOURCE_REGISTRY[k].provenance for k in lib if k in SOURCE_REGISTRY})


def check(profile, env_lo, env_hi) -> dict:
    """Reasonableness check of a recovered profile against the empirical envelope."""
    return dict(pct_in_envelope=in_envelope(profile, env_lo, env_hi))
