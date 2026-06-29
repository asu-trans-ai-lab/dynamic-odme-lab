# Profile RAG guide

Retrieve and **label by provenance** multiple departure/time-of-day profile sources, build an empirical
envelope, and use it as a seed / target / reasonableness check.

- Registry: `odme.rag.source_registry.SOURCE_REGISTRY` — survey (trip-start), NHTS (benchmark), PeMS
  (detector **passage-time**, needs travel-time shift), ABM (model prior), speed→FD (derived), counts
  (anchor).
- Builders: `odme.rag.survey_profile_builder.load_survey_profiles(csv)`,
  `odme.rag.pems_profile_builder.detector_profile(csv)` — generic public schemas; point them at local files.
- Envelope + check: `odme.rag.departure_profile_rag.build_library(...)`, `check(...)`.
- **PeMS caveat:** detector passage-time ≠ trip departure; shift by travel time and prefer entry-screenline
  detectors before using as a departure prior.
