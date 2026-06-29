"""Time-dependent (T>1) ingestion for the QVDF_turnkey stage2_odme format.

Reads time-stamped columns (t_min + link_sequence) and a time-dependent linkflow file
(t_min, link_id, observed, assigned_odme) into a CaseData with T bins, so the SAME
build_A + gradient_deviation pipeline runs as a real dynamic ODME.
"""
from __future__ import annotations

import csv

from ..model import CaseData, Column, Link, Measurement, Node, TimeGrid
from ..readiness.loaders import load_links, load_nodes, _split_ids
from ..readiness.field_reader import IssueLog


def _read(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _bins(t_mins):
    uniq = sorted(set(t_mins))
    step = min((b - a for a, b in zip(uniq, uniq[1:])), default=15) or 15
    return uniq[0], step, {t: (t - uniq[0]) // step for t in uniq}, len(uniq)


def load_dynamic_case(network_dir, columns_csv, linkflow_csv):
    """Returns (case, ref) where ref[(link_id,t)] = assigned_odme for cross-checking."""
    log = IssueLog()
    nodes = load_nodes(network_dir, log)
    links = load_links(network_dir, log)

    col_rows = _read(columns_csv)
    lf_rows = _read(linkflow_csv)
    t_all = [int(float(r["t_min"])) for r in col_rows] + [int(float(r["t_min"])) for r in lf_rows]
    t0, step, tbin, T = _bins(t_all)

    columns = []
    for gid, r in enumerate(col_rows):
        seq = r.get("link_sequence") or ""
        if not seq.strip():
            continue
        columns.append(Column(
            o_zone_id=int(float(r["o_zone_id"])), d_zone_id=int(float(r["d_zone_id"])),
            period="all", volume=float(r["volume"]), link_ids=_split_ids(seq),
            tau=tbin[int(float(r["t_min"]))], group_id=gid))

    # measurements = observed link flow at (link, t); keep assigned_odme as reference
    measurements, ref = [], {}
    for r in lf_rows:
        lid = int(float(r["link_id"])); t = tbin[int(float(r["t_min"]))]
        obs = float(r["observed"])
        measurements.append(Measurement(obs_volume=obs, link_id=lid, t_bin=t,
                                        measurement_type=r.get("role", "link"), source_path="TD"))
        ref[(lid, t)] = float(r["assigned_odme"])

    start_h = t0 / 60.0
    tg = TimeGrid(start_hour=start_h, end_hour=start_h + T * step / 60.0, interval_minutes=float(step))
    case = CaseData(name="dynamic_case", nodes=nodes, links=links, columns=columns,
                    measurements=measurements, time_grid=tg)
    case.build_indexes()
    return case, ref, log
