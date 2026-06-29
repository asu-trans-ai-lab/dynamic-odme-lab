# DO NOT COMMIT NVTA / VDOT / INRIX / RITIS / CBI DATA

This folder is a **manifest only**. It contains paths, steps, and schema templates — **never data**.

Do **not** place any of the following here or anywhere in the repo tree:
- CBI data, INRIX/RITIS speed files, VDOT matched-link files, VDOT counts (if restricted)
- NVTA GMNS private `link.csv`, `TMC_Identification*` files, P4P link IDs
- generated CSVs carrying private link IDs

Private data live **outside** the repo or under the git-ignored `data_private/` folder. Run
`python scripts/validate_no_private_data.py` before every commit — it fails if any private data leak in.
