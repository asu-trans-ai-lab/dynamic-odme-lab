# Stage 5 — NVTA private benchmark (manifest only)

The NVTA corridor-embedded dynamic ODME (I-395) is a **private** benchmark. **No NVTA / VDOT / INRIX /
RITIS / CBI data are committed here.** This folder documents how to reproduce the private results **locally**
when authorized data are present.

## What lives here
- `expected_private_paths.yaml` — where the private inputs must be on a local machine.
- `private_file_manifest_template.csv` — the file list (names + roles) an authorized user fills in.
- `nvta_reproduction_steps_private.md` — the local run steps (no data).
- `DO_NOT_COMMIT_NVTA_DATA.md` — the hard rule.

## To reproduce locally (authorized users only)
1. Place authorized data under `data_private/nvta/` (git-ignored) per `expected_private_paths.yaml`.
2. Follow `nvta_reproduction_steps_private.md`.
3. Run `python scripts/validate_no_private_data.py` before any commit — it must print CLEAN.

The public repo demonstrates the **same methodology** on public/synthetic benchmarks (stages 0–4).
