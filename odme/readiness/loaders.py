"""Tolerant loaders + filler for a case directory.

Reads node/link/demand/columns/measurement/settings, applies TAPLite-style defaults,
coerces units, and assembles a CaseData. Records every defaulted field / warning in IssueLog.
"""
from __future__ import annotations

import csv
import os

import yaml

from ..model import CaseData, Column, Link, Measurement, Node, TimeGrid
from .field_reader import IssueLog, get_value


def _read_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [{(k.strip() if k else k): v for k, v in row.items()}
                for row in csv.DictReader(f)]


def load_settings(case_dir: str, log: IssueLog) -> dict:
    yml = os.path.join(case_dir, "settings.yml")
    csvp = os.path.join(case_dir, "settings.csv")
    s: dict = {}
    if os.path.exists(yml):
        with open(yml, encoding="utf-8") as f:
            s = yaml.safe_load(f) or {}
    elif os.path.exists(csvp):
        for row in _read_csv(csvp):  # key,value style or single-row style
            if "key" in row and "value" in row:
                s[row["key"].strip()] = row["value"]
            else:
                s.update(row)
    else:
        log.warn("no settings.yml/settings.csv found; using time-grid defaults (T=1, static)")
    return s


def time_grid_from_settings(s: dict, log: IssueLog) -> TimeGrid:
    a = s.get("assignment", {}) if isinstance(s.get("assignment"), dict) else s
    start = float(a.get("time_start_hour", s.get("demand_period_starting_hours", 7.0)))
    end = float(a.get("time_end_hour", s.get("demand_period_ending_hours", 8.0)))
    # default interval = whole window  => T = 1 (static)
    interval = a.get("time_interval_minutes", s.get("time_interval_minutes", (end - start) * 60.0))
    tg = TimeGrid(start_hour=start, end_hour=end, interval_minutes=float(interval))
    if tg.is_static:
        log.warn(f"time grid {start}-{end}h, interval={interval}min -> T=1 (static)")
    else:
        log.warn(f"time grid {start}-{end}h, interval={interval}min -> T={tg.T} (dynamic)")
    return tg


def load_nodes(case_dir: str, log: IssueLog) -> dict[int, Node]:
    path = os.path.join(case_dir, "node.csv")
    if not os.path.exists(path):
        log.fatal("node.csv not found")
        return {}
    nodes: dict[int, Node] = {}
    for row in _read_csv(path):
        nid = get_value(row, "node_id", 0, required=True, log=log, row_tag="node.csv")
        if nid == 0:
            continue
        nodes[nid] = Node(
            node_id=nid,
            zone_id=get_value(row, "zone_id", 0, log=log),
            x=get_value(row, "x_coord", 0.0, log=log),
            y=get_value(row, "y_coord", 0.0, log=log),
        )
    if not nodes:
        log.fatal("node.csv produced 0 usable nodes")
    return nodes


def load_links(case_dir: str, log: IssueLog, length_unit: str = "mile") -> dict[int, Link]:
    path = os.path.join(case_dir, "link.csv")
    if not os.path.exists(path):
        log.fatal("link.csv not found")
        return {}
    links: dict[int, Link] = {}
    for row in _read_csv(path):
        lid = get_value(row, "link_id", 0, required=True, log=log, row_tag="link.csv")
        fn = get_value(row, "from_node_id", 0, required=True, log=log, row_tag=f"link {lid}")
        tn = get_value(row, "to_node_id", 0, required=True, log=log, row_tag=f"link {lid}")
        if lid == 0 or fn == 0 or tn == 0:
            log.error(f"link row dropped (missing id/nodes): link_id={lid}")
            continue
        # prefer an explicit unit'd column when present, else coerce raw length
        if str(row.get("length_in_miles", "")).strip() != "":
            length = get_value(row, "length_in_miles", 1.0, log=None)
        else:
            length = get_value(row, "length", 1.0, log=log)
            if length > 1000:  # heuristic: raw meters
                length = length / 1609.344 if length_unit == "mile" else length / 1000.0
        cap = get_value(row, "capacity", 0.0, log=log)
        if cap <= 0:
            log.warn(f"link {lid}: capacity missing/0 (needed for z=v/C); left as 0 -> flag")
        links[lid] = Link(
            link_id=lid, from_node_id=fn, to_node_id=tn,
            lanes=get_value(row, "lanes", 1, log=log),
            capacity=cap,
            free_speed=get_value(row, "free_speed", 10.0, log=log),
            length=length,
            link_type=get_value(row, "link_type", 1, log=log),
            alpha=_first(row, ("VDF_alpha", "vdf_alpha", "BPR_alpha1"), 0.15, log),
            beta=_first(row, ("VDF_beta", "vdf_beta", "BPR_beta1"), 4.0, log),
            plf=_first(row, ("VDF_plf", "vdf_plf", "BPR_plf1"), 1.0, log),
            ref_volume=get_value(row, "ref_volume", -1.0, log=log),
            obs_volume=get_value(row, "obs_volume", -1.0, log=log),
        )
    if not links:
        log.fatal("link.csv produced 0 usable links")
    return links


def _first(row: dict, keys: tuple, default, log: IssueLog):
    """Read the first present alias key; default+note only if none present."""
    for k in keys:
        if str(row.get(k, "")).strip() != "":
            return get_value(row, k, default, log=None)
    log.note_filled(keys[0])
    return default


def _split_ids(s: str) -> list[int]:
    return [int(float(x)) for x in str(s).replace(",", ";").split(";") if str(x).strip() not in ("", "nan")]


def load_columns(case_dir: str, log: IssueLog) -> list[Column]:
    """Reads route_assignment.csv or columns.csv (TAPLite / Path4GMNS — same schema)."""
    path = None
    for cand in ("route_assignment.csv", "columns.csv"):
        if os.path.exists(os.path.join(case_dir, cand)):
            path = os.path.join(case_dir, cand)
            break
    if path is None:
        log.warn("no route_assignment.csv/columns.csv; A must come from another source adapter")
        return []
    cols: list[Column] = []
    for row in _read_csv(path):
        seq = row.get("link_id_sequence") or row.get("link_sequence") or ""
        if not str(seq).strip():
            continue
        cols.append(Column(
            o_zone_id=get_value(row, "o_zone_id", 0, log=log),
            d_zone_id=get_value(row, "d_zone_id", 0, log=log),
            period=get_value(row, "demand_period", "all", log=log),
            volume=get_value(row, "volume", 0.0, log=log),
            link_ids=_split_ids(seq),
            node_ids=_split_ids(row.get("node_sequence") or row.get("node_ids") or ""),
        ))
    return cols


def load_measurements(case_dir: str, links: dict[int, Link], log: IssueLog) -> list[Measurement]:
    """Three normalized paths (A: ref_volume in link.csv, B: measurement.csv, C: target_count)."""
    out: list[Measurement] = []
    link_by_pair = {(lk.from_node_id, lk.to_node_id): lk.link_id for lk in links.values()}

    # Path A — ref_volume / obs_volume in link.csv
    for lk in links.values():
        v = lk.ref_volume if lk.ref_volume >= 1 else (lk.obs_volume if lk.obs_volume >= 0 else None)
        if v is not None and v >= 1:
            out.append(Measurement(obs_volume=v, link_id=lk.link_id,
                                   from_node_id=lk.from_node_id, to_node_id=lk.to_node_id,
                                   source_path="A"))

    # Path B — measurement.csv (West Jordan convention)
    mpath = os.path.join(case_dir, "measurement.csv")
    if os.path.exists(mpath):
        for row in _read_csv(mpath):
            count = get_value(row, "count", get_value(row, "obs_volume", -1.0, log=log), log=log)
            if count < 0:
                continue
            fn = get_value(row, "from_node_id", 0, log=log)
            tn = get_value(row, "to_node_id", 0, log=log)
            lid = link_by_pair.get((fn, tn))
            out.append(Measurement(
                obs_volume=count, link_id=lid, from_node_id=fn or None, to_node_id=tn or None,
                o_zone_id=get_value(row, "o_zone_id", 0, log=log) or None,
                d_zone_id=get_value(row, "d_zone_id", 0, log=log) or None,
                upper_bound_flag=get_value(row, "upper_bound_flag", 0, log=log),
                measurement_type=get_value(row, "measurement_type", "link_count", log=log),
                source_path="B"))

    # Path C — output_link_count.csv (TCGlite target_count)
    cpath = os.path.join(case_dir, "output_link_count.csv")
    if os.path.exists(cpath):
        for row in _read_csv(cpath):
            tgt = get_value(row, "target_count", -1.0, log=log)
            if tgt <= 0:
                continue
            out.append(Measurement(obs_volume=tgt,
                                   link_id=get_value(row, "link_id", 0, log=log) or None,
                                   source_path="C"))
    return out


def load_case(case_dir: str) -> tuple[CaseData, IssueLog]:
    log = IssueLog()
    name = os.path.basename(os.path.normpath(case_dir))
    settings = load_settings(case_dir, log)
    unit = settings.get("unit", {}) if isinstance(settings.get("unit"), dict) else {}
    length_unit = unit.get("length_unit", "mile")
    tg = time_grid_from_settings(settings, log)
    nodes = load_nodes(case_dir, log)
    links = load_links(case_dir, log, length_unit=length_unit)
    columns = load_columns(case_dir, log)
    measurements = load_measurements(case_dir, links, log)
    case = CaseData(name=name, nodes=nodes, links=links, columns=columns,
                    measurements=measurements, settings=settings, time_grid=tg)
    case.build_indexes()
    return case, log
