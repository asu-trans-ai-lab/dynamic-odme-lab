# Data sources, attribution & disclaimer

The benchmark networks bundled in `benchmarks/` are third-party or agency datasets, re-distributed here in
**GMNS / DTALite-TAPLite format for research reproducibility**. Original rights remain with the sources
below. Formats have been **converted/derived** (GMNS `link.csv` / `node.csv` / `demand.csv`); numbers may
differ from the originals due to that conversion. **Verify the original source and its terms before any
redistribution or production use.** Everything here is provided **as-is, without warranty**, for research and
teaching.

| benchmark | network | source | external link | notes |
|---|---|---|---|---|
| `02_sioux_falls` | Sioux Falls | Transportation Networks for Research Core Team | https://github.com/bstabler/TransportationNetworks | classic 24-node test net; public |
| `03_west_jordan_utah` | West Jordan, UT | GMNS / DTALite example network | https://github.com/asu-trans-ai-lab/DTALite · https://github.com/zephyr-data-specs/GMNS | small real-network example |
| `04_arc_superzone` | Atlanta (ARC) | **Atlanta Regional Commission** travel model | https://atlantaregional.org/ · https://github.com/asu-trans-ai-lab | **converted/derived GMNS**; see disclaimer below |
| `05_chicago_sketch` | Chicago Sketch | Transportation Networks for Research Core Team | https://github.com/bstabler/TransportationNetworks | ~933 zones; public |
| `06_chicago_regional` | Chicago Regional | Transportation Networks for Research Core Team | https://github.com/bstabler/TransportationNetworks | ~1,790 zones; large (gzipped) |

## Citations
- **Sioux Falls** — LeBlanc, L.J., Morlok, E.K., Pierskalla, W.P. (1975). *An efficient approach to solving
  the road network equilibrium traffic assignment problem.* Transportation Research 9(5), 309–318.
- **Chicago Sketch / Regional** — Eash, R., Chon, K.S., Lee, Y.J., Boyce, D.E. (1983) and the Chicago Area
  Transportation Study; distributed via the Transportation Networks for Research repository.
- **Transportation Networks repository** — Transportation Networks for Research Core Team.
  *Transportation Networks for Research.* https://github.com/bstabler/TransportationNetworks (accessed 2026).

## ARC disclaimer (important)
The `04_arc_superzone` network and demand are a **GMNS conversion derived from the Atlanta Regional
Commission (ARC) regional travel model**. This repository redistributes a **converted, research-oriented
copy** for reproducibility of the assignment/ODME experiments; it is **not** an official ARC product and may
differ from ARC's released model. **ARC retains all rights to the original data.** For the authoritative model
and data, contact the Atlanta Regional Commission (https://atlantaregional.org/) — do not treat the copy here
as official, and confirm ARC's terms before redistribution or any non-research use.

## Not included
Any private agency data (see `docs/09_private_data_policy.md`) is **never** committed here; it stays local
under `data_private/`.
