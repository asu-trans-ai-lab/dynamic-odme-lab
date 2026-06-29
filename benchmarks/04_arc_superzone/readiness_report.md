# ODME readiness report

```
[READINESS] case=09_arc_atlanta
 nodes=66546  zones=6031  links=145971  columns=0  OD_pairs(cols)=0
 time grid: 6.0-10.0h interval=240.0min -> static (T=1)
 measurements: 154919 (path A+B) | resolved 154919/145971 links (106.1%) | usable(with column coverage)=0
 UNCOVERED measured links (no column through them): [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20] … (+143877 more)
 filled-by-default: d_zone_id(11108), o_zone_id(11108), obs_volume(157079), upper_bound_flag(11108)
 warn: time grid 6.0-10.0h, interval=240.0min -> T=1 (static)
 warn: no route_assignment.csv/columns.csv; A must come from another source adapter
 warn: 143897 measured link(s) carried by NO column -> ODME cannot fit them: links [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20] …(+143877). Need columns (run assignment) or the approximate adapter.
 warn: all measurements are on links with no column coverage -> ODME will not move the fit until A gains paths through those links (Stage-1 approximate adapter)
 VERDICT: READY  (static (T=1))
```
