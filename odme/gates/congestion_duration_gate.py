"""Congestion-duration gate (re-export of the physics duration gate at the gates layer)."""
from __future__ import annotations
from ..physics.congestion_duration import observed_duration, duration_gate

__all__ = ["observed_duration", "duration_gate"]
