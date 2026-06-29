"""from_external adapter — reconstruct route columns from a foreign path file.

Some engines (e.g. TCGlite) emit paths as coordinate LINESTRINGs rather than link/node
sequences. This maps each geometry vertex to the nearest node, derives the link sequence,
and writes a standard columns.csv so the normal `from_columns` pipeline runs unchanged.
"""
from __future__ import annotations

import csv
import os


def _read(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _node_coords(node_csv):
    out = []
    for n in _read(node_csv):
        out.append((int(n["node_id"]), float(n["x_coord"]), float(n["y_coord"])))
    return out


def _pair2link(link_csv):
    p2l = {}
    for l in _read(link_csv):
        p2l[(int(l["from_node_id"]), int(l["to_node_id"]))] = int(float(l["link_id"]))
    return p2l


def _zone2node(node_csv):
    z2n = {}
    for n in _read(node_csv):
        z = n.get("zone_id", "")
        if str(z).strip() not in ("", "0", "-1"):
            z2n[int(float(z))] = int(n["node_id"])
    return z2n


def _nearest(x, y, ncoord, tol=2e-3):
    best, bd = None, 1e18
    for nid, nx, ny in ncoord:
        d = (nx - x) ** 2 + (ny - y) ** 2
        if d < bd:
            bd, best = d, nid
    return best if bd <= tol * tol else None


def _vertices(geom):
    inside = geom[geom.find("(") + 1: geom.rfind(")")]
    out = []
    for part in inside.split(","):
        s = part.strip().split()
        if len(s) >= 2:
            out.append((float(s[0]), float(s[1])))
    return out


def reconstruct_columns(paths_csv, node_csv, link_csv, out_csv,
                        flow_field="estimated_flow", tol=2e-3):
    """Write a columns.csv (o_zone_id,d_zone_id,volume,node_sequence,link_id_sequence).

    Returns (n_written, n_failed)."""
    ncoord = _node_coords(node_csv)
    p2l = _pair2link(link_csv)
    z2n = _zone2node(node_csv)
    rows, failed = [], 0
    for p in _read(paths_csv):
        nseq = [_nearest(x, y, ncoord, tol) for (x, y) in _vertices(p["geometry"])]
        if any(n is None for n in nseq):
            failed += 1
            continue
        # orient path origin->destination (some engines draw geometry dest->origin)
        o_node = z2n.get(int(float(p["o_zone_id"])))
        if o_node is not None and nseq and nseq[0] != o_node and nseq[-1] == o_node:
            nseq = nseq[::-1]
        lseq = [p2l.get((a, b)) for a, b in zip(nseq, nseq[1:])]
        if not lseq or any(l is None for l in lseq):
            failed += 1
            continue
        vol = p.get(flow_field) or p.get("target_flow") or "0"
        rows.append({
            "o_zone_id": int(float(p["o_zone_id"])),
            "d_zone_id": int(float(p["d_zone_id"])),
            "demand_period": "all",
            "volume": float(vol),
            "node_sequence": ";".join(str(n) for n in nseq),
            "link_id_sequence": ";".join(str(l) for l in lseq),
        })
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["o_zone_id", "d_zone_id", "demand_period",
                                          "volume", "node_sequence", "link_id_sequence"])
        w.writeheader()
        w.writerows(rows)
    return len(rows), failed
