# Private data policy

This repository is **public**. Agency data are **private** and are **never committed**.

## Never commit
- CBI data, INRIX/RITIS speed files, VDOT matched-link files, VDOT counts (if restricted)
- NVTA GMNS private `link.csv`, TMC identification files, P4P link IDs
- Any generated CSVs that carry private link IDs

## How privacy is enforced
1. **`.gitignore`** ignores `data_private/`, `**/*NVTA*`, `**/*VDOT*`, `**/*INRIX*`, `**/*RITIS*`,
   `**/*CBI*`, `**/*P4P*`, `TMC_Identification*`, `*.parquet`, `*.sqlite`, `*.zip` (laid down *before* any
   data was copied).
2. **`scripts/validate_no_private_data.py`** scans every committed text file for private terms / file names
   and **fails** if any are found. Run it before every commit/release:
   ```bash
   python scripts/validate_no_private_data.py
   ```
3. The only place private *names* may appear is `benchmarks/99_private_nvta_manifest_only/` (a **manifest
   only** — paths and steps, no data) and this policy doc.

## Local private pack convention
Place authorized agency data **outside** the repo tree or under the git-ignored folder:
```
C:\source_codes\0_source_code_new\dynamic_ODME\data_private\nvta\
```
The code and docs run against the private data **when it is present locally**; the private data are not
part of the public repository. Private NVTA results can therefore be regenerated locally by an authorized
user, while the public repo demonstrates the full methodology on public/synthetic benchmarks.
