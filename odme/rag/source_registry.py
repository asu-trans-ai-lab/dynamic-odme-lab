"""Registry of departure/time-of-day profile sources with provenance labels."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ProfileSource:
    key: str
    gives: str
    provenance: str          # measured-trip-start | measured-passage-time | model-prior | derived | count-anchor
    use: str
    needs_tt_shift: bool = False


SOURCE_REGISTRY = {
    "survey": ProfileSource("survey", "trip-start by purpose (HBW/HBO/NHB/truck)",
                            "measured-trip-start", "behavioral departure prior"),
    "nhts": ProfileSource("nhts", "national trips by start time/purpose",
                          "measured-trip-start", "reasonableness benchmark"),
    "pems": ProfileSource("pems", "detector flow/occupancy/speed by time-of-day",
                          "measured-passage-time", "operational profile (after TT shift)", needs_tt_shift=True),
    "abm": ProfileSource("abm", "tour/trip departure-time choice", "model-prior", "modeling-practice prior"),
    "speed_fd": ProfileSource("speed_fd", "speed-derived flow shape", "derived", "local temporal shape only"),
    "counts": ProfileSource("counts", "AADT/AAWDT / screenline counts", "count-anchor", "magnitude anchor"),
}
