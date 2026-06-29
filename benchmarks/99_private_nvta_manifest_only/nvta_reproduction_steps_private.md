# NVTA reproduction steps (local, authorized users only — no data committed)

Prerequisite: authorized data placed under `data_private/nvta/` per `expected_private_paths.yaml`.

1. **Crosswalk** corridor link → TMC → GMNS link (direction-aware `N≡-`, `P≡+`); keep SB/NB carriageways
   separate.
2. **Departure-profile recovery** (`odme.dynamic.recover_phi`): seed from a survey base, fit the
   time-dependent OD to the **INRIX/CBI 15-min** link flows on fixed routes (OD totals fixed).
3. **Magnitude / network ODME** against **actual VDOT screenline counts** (the count foundation).
4. **Queue diagnostics** (`odme.physics`): `μ(D/C)` discharge rate, forward queue, congestion-duration gate
   — diagnostic only.
5. **Validate**: INRIX-vs-Model speed profiles + observed-vs-ODME volume in the agency house style.
6. **Before committing anything**: `python scripts/validate_no_private_data.py` must print CLEAN; outputs
   with private link IDs stay under `data_private/nvta/outputs` (git-ignored).
