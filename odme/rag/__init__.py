"""Departure-profile knowledge layer (RAG): retrieve & label empirical profile sources.

Every profile is tagged by provenance: measured-trip-start (survey), measured-passage-time (detector),
model-prior (ABM), derived (speed->FD), or count-anchored (VDOT). PeMS is detector PASSAGE time, not
trip departure -- a travel-time shift is required to use it as a departure prior.
"""
from .source_registry import SOURCE_REGISTRY, ProfileSource
from .survey_profile_builder import load_survey_profiles
from .pems_profile_builder import detector_profile

__all__ = ["SOURCE_REGISTRY", "ProfileSource", "load_survey_profiles", "detector_profile"]
