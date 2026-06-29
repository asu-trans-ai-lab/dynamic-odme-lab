"""Experimental physics / queue diagnostics for dynamic ODME.

NOTE: this layer is DIAGNOSTIC / EXPERIMENTAL. It is *not* a validated physics-informed ODME until the
congestion-duration gate passes (P_model approx P_obs with a queue that forms). See
docs/06_qvdf_queue_physics_guide.md and odme.gates.congestion_duration_gate.
"""
from .fluid_queue import point_queue
from .qvdf import mu_of_dc, duration_from_dc, s3_speed, s3_invert_flow, bpr_speed
from .fd_models import FD_S3, FD_BPR
from .congestion_duration import observed_duration, duration_gate

__all__ = ["point_queue", "mu_of_dc", "duration_from_dc", "s3_speed", "s3_invert_flow",
           "bpr_speed", "FD_S3", "FD_BPR", "observed_duration", "duration_gate"]
