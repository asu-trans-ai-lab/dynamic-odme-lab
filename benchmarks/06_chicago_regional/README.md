# Chicago Regional — benchmark network

**Chicago Regional** network (~1,790 zones, ~39k links) — a large agency-scale traffic-assignment testbed, in
GMNS / DTALite-TAPLite format. Large files are gzipped.

| file | raw | what |
|---|---:|---|
| `link.csv.gz` | 6.8 MB | links (GMNS) |
| `node.csv` | 0.4 MB | nodes incl. zone centroids |
| `demand.csv.gz` | 31 MB | OD demand (`o_zone_id, d_zone_id, volume`) |
| `mode_type.csv`, `settings.csv` | — | run config |

```bash
cd benchmarks/06_chicago_regional && gunzip -k *.gz     # -> link.csv, demand.csv
# then run the DTALite/TAPLite assignment (see repo operator + odme package)
```

**Source & attribution:** Transportation Networks for Research Core Team —
https://github.com/bstabler/TransportationNetworks. See [`../../DATA_SOURCES.md`](../../DATA_SOURCES.md) for
citation, terms, and disclaimer. Provided as-is for research/teaching.
