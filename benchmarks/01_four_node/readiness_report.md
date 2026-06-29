# ODME readiness report

```
[READINESS] case=01_four_node
 nodes=4  zones=2  links=4  columns=1  OD_pairs(cols)=1
 time grid: 7.0-8.0h interval=60.0min -> static (T=1)
 measurements: 1 (path A) | resolved 1/4 links (25.0%) | usable(with column coverage)=0
 UNCOVERED measured links (no column through them): [3]
 filled-by-default: VDF_alpha(4), VDF_beta(4), VDF_plf(4), obs_volume(4), ref_volume(3)
 warn: time grid 7.0-8.0h, interval=60.0min -> T=1 (static)
 warn: 1 measured link(s) carried by NO column -> ODME cannot fit them: links [3]. Need columns (run assignment) or the approximate adapter.
 warn: all measurements are on links with no column coverage -> ODME will not move the fit until A gains paths through those links (Stage-1 approximate adapter)
 VERDICT: READY  (static (T=1))
```
