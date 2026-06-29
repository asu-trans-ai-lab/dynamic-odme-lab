"""Versioned feature switch. The queue layer is NEVER 'on' -- at most 'diagnostic' until the
congestion-duration gate passes. Honest naming is enforced here.

  ODME_VERSION = v1_baseline | v2_profile_enhanced | v3_physics_diagnostic   (default v2_profile_enhanced)
"""
from __future__ import annotations
import os

VERSIONS = {
    "v1_baseline": dict(
        seed="flat", profile_regularization=False, target_prior=None,
        queue_layer="off", congestion_duration_gate=False,
        label="v1 baseline: flat seed, link-time mapping, no regularization, no queue"),
    "v2_profile_enhanced": dict(
        seed="survey_or_mixture", profile_regularization=True, target_prior="purpose_mix",
        queue_layer="off", congestion_duration_gate=False,
        label="v2 profile-enhanced: survey/mixture base + regularization (queue OFF)"),
    "v3_physics_diagnostic": dict(
        seed="survey_or_mixture", profile_regularization=True, target_prior="purpose_mix",
        queue_layer="diagnostic", congestion_duration_gate=True,
        label="v3 physics-DIAGNOSTIC: v2 + queue diagnostic + duration gate (NOT production)"),
}
_QUEUE = {"on": "diagnostic", "diagnostic": "diagnostic", "off": "off"}


def get_config(version: str | None = None) -> dict:
    v = version or os.environ.get("ODME_VERSION", "v2_profile_enhanced")
    if v not in VERSIONS:
        raise ValueError(f"unknown ODME_VERSION {v!r}; choose {list(VERSIONS)}")
    cfg = dict(VERSIONS[v]); cfg["version"] = v
    if "ODME_PHYSICS" in os.environ:                       # never resolves to 'on'
        cfg["queue_layer"] = _QUEUE.get(os.environ["ODME_PHYSICS"].lower(), "off")
        cfg["congestion_duration_gate"] = cfg["queue_layer"] == "diagnostic"
    return cfg
