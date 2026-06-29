"""Per-cell validation output: estimated vs observed, deviation, and R2/RMSE/MAPE."""
from __future__ import annotations

import csv
import math
import os


def validate(case, A, out_dir: str) -> tuple[str, dict]:
    vols = A.link_volume(case.columns)
    rows, ys, yhats = [], [], []
    for (lid, t), m in sorted(A.measured_cells.items()):
        est = vols.get((lid, t), 0.0)
        covered = (lid, t) in A.incidence
        rows.append(dict(link_id=lid, t=t, obs=m.obs_volume, est=round(est, 3),
                         dev=round(est - m.obs_volume, 3), covered=int(covered),
                         source_path=m.source_path))
        if covered:
            ys.append(m.obs_volume)
            yhats.append(est)

    path = os.path.join(out_dir, "odme_link_volume_validation.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["link_id", "t", "obs", "est", "dev", "covered", "source_path"])
        w.writeheader()
        w.writerows(rows)

    metrics = _metrics(ys, yhats)
    return path, metrics


def _metrics(ys, yhats) -> dict:
    n = len(ys)
    if n == 0:
        return dict(n=0, r2=float("nan"), rmse=float("nan"), mape_pct=float("nan"))
    mean_y = sum(ys) / n
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    ss_res = sum((y - yh) ** 2 for y, yh in zip(ys, yhats))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-9 else float("nan")
    rmse = math.sqrt(ss_res / n)
    mape = 100.0 / n * sum(abs(y - yh) / y for y, yh in zip(ys, yhats) if y > 1e-9)
    return dict(n=n, r2=round(r2, 4), rmse=round(rmse, 3), mape_pct=round(mape, 2))
