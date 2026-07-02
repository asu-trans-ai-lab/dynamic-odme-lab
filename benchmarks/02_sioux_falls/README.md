# Sioux Falls — benchmark network

The classic **Sioux Falls** 24-node traffic-assignment test network (LeBlanc et al., 1975), in GMNS /
DTALite-TAPLite format. Small enough to inspect by hand; used here for the matrix-free operator + static ODME.

| file | what |
|---|---|
| `link.csv`, `node.csv` | network (GMNS) |
| `demand.csv` | OD demand (`o_zone_id, d_zone_id, volume`) |
| `columns.csv`, `matrix_A.csv` | route pool / assignment matrix |
| `odme_link_volume_validation.csv`, `output_link_count.csv` | ODME validation artifacts |
| `settings.yml`, `readiness_report.md` | run config + Stage-0 readiness |

**Source & attribution:** Transportation Networks for Research Core Team —
https://github.com/bstabler/TransportationNetworks. Citation: LeBlanc, Morlok & Pierskalla (1975). See
[`../../DATA_SOURCES.md`](../../DATA_SOURCES.md). Provided as-is for research/teaching.
