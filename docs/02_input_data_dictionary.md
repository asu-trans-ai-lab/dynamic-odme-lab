# Input data dictionary (public, agency-agnostic schemas)

## Network layer
`link_id, from_node_id, to_node_id, length, lanes, facility_type, area_type, capacity, free_flow_speed, tmc, direction`

## OD / path layer
`o_zone_id, d_zone_id, mode_type, demand, departure_time_bin, path_id, path_link_sequence, path_share`

## Observation layer
`link_id, tmc, time_bin, observed_count, observed_speed, derived_flow, count_source, speed_source`
- **`observed_count` / `count_source`** = actual measured counts (e.g. VDOT) — the magnitude foundation.
- **`observed_speed` / `speed_source`** = measured speed (e.g. INRIX) — the time-of-day foundation.
- **`derived_flow`** = speed→FD reconstruction — temporal *shape* only, anchored to counts.

## Profile layer
`profile_id, source, purpose, time_bin, profile_share, is_measured, is_derived, is_modeled`

## Queue layer (diagnostic)
`lambda_inflow, mu_discharge, outflow_s, queue_Q, queue_growth, T0, T2, T3, P`

## Gate layer
`gate_name, metric, threshold, value, status, diagnosis`

> Provenance discipline: every volume/flow is tagged measured (count), measured (speed), derived
> (speed→FD), model, or count-anchored — see `odme/rag/source_registry.py`.
