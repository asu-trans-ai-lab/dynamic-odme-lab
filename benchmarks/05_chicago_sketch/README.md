# Chicago Sketch — benchmark network

Classic **Chicago Sketch** planning network (~933 zones), a standard traffic-assignment testbed, in GMNS /
DTALite-TAPLite format.

| file | what |
|---|---|
| `link.csv` | links (GMNS: id, from/to node, lanes, capacity, free_speed, VDF) |
| `node.csv` | nodes incl. zone centroids |
| `demand.csv` | OD demand (`o_zone_id, d_zone_id, volume`) |
| `mode_type.csv`, `settings.csv` | run config |

Run the assignment/ODME with the DTALite/TAPLite kernel (see the repo's operator + `odme` package). All files
are small and shipped raw — no decompression needed.

**Source & attribution:** Transportation Networks for Research Core Team —
https://github.com/bstabler/TransportationNetworks. See [`../../DATA_SOURCES.md`](../../DATA_SOURCES.md) for
citation, terms, and disclaimer. Provided as-is for research/teaching.
