# ARC benchmark — end-to-end reproduction

Full network + demand are provided (gzipped) under `network/` so the ARC equilibrium assignment and its
Section-7-style validation can be reproduced from scratch.

## Files (`network/`)
| file | raw size | what |
|---|---:|---|
| `link.csv.gz` | 50 MB | GMNS links (145,971) with facility/area type, VDF, capacity, free-flow speed |
| `node.csv.gz` | 2.4 MB | nodes (66,546) incl. zone centroids |
| `demand_sov.csv.gz` | 13.7 MB | SOV OD demand |
| `demand_hov2.csv.gz`, `demand_hov3.csv.gz` | 3.8 / 2.5 MB | HOV2 / HOV3 OD demand |
| `mode_type.csv`, `settings.csv` | — | DTALite run config (AM 6–10, 30 iters, gap 0.5%, 3 consecutive) |
| `arc_am_ref_volume.csv.gz` | 3.9 MB | ARC AM reference assigned volume (+ factype/atype) for validation |

## Steps
```bash
# 1. decompress the network + demand + reference
cd benchmarks/04_arc_superzone/network
gunzip -k *.gz                 # keeps the .gz; produces link.csv, node.csv, demand_*.csv, arc_am_ref_volume.csv

# 2. run the equilibrium assignment (bi-conjugate Frank-Wolfe) with DTALite/TAPLite
#    build the kernel once (see the DTALite/TAPLite source; -O2 static build):
#    g++ -std=c++17 -O2 -fopenmp -fpermissive -static-libgcc -static-libstdc++ TAPLite.cpp -o taplite.exe
cp /path/to/DTALite.exe .      # or taplite.exe
./DTALite.exe                  # reads link/node/demand/settings -> writes link_performance.csv (~6 min)

# 3. validate against the ARC reference (reproduces Tables 7-5 / 7-6 / 7-7 + correlation)
cd ..
cp network/arc_am_ref_volume.csv .        # the validation script reads it from its own dir
python arc_calibration_report.py network  # -> arc_calibration_reproduction.md
```

## Expected result (AM, auto)
Reproducing ARC's own AM assignment (`ref_auto_vol`) with this kernel:

| metric | value |
|---|---:|
| correlation | **0.993** |
| region-wide %RMSE | 22% |
| volume ratio (Est/Ref) | **1.00** |
| matched links | 118,687 |

By facility type the fit follows ARC's pattern (Interstate/Freeway best, Collector worst). See the repo's
condensed calibration artifacts (`arc_observed_counts.csv`, `*gate_report.md`, `calibration_summary.csv`) for
the count-based validation. Note: `settings.csv` runs the AM period; ARC's published report is a full 5-period
daily model — the single-period run reproduces ARC's **assignment**, and inherits its count calibration.
