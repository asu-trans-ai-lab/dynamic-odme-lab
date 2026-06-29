"""Approximate / inherit adapter.

Last-resort A enrichment when measured links have NO column coverage: synthesize a
shortest-path column forced through each uncovered link, seeded with a modest volume so
the gradient solver can grow it toward the observation. Flagged loudly in the report.
"""
from __future__ import annotations

import heapq

from ...model import CaseData, Column


def _graph(case: CaseData):
    adj: dict[int, list] = {}
    for lk in case.links.values():
        cost = lk.length / max(lk.free_speed, 1.0)
        adj.setdefault(lk.from_node_id, []).append((lk.to_node_id, lk.link_id, cost))
    return adj


def _dijkstra(adj, src, dst):
    """Return (link_ids, node_ids) for the shortest path src->dst, or None."""
    if src == dst:
        return [], [src]
    pq = [(0.0, src, [], [src])]
    seen = set()
    while pq:
        d, u, links, nodes = heapq.heappop(pq)
        if u == dst:
            return links, nodes
        if u in seen:
            continue
        seen.add(u)
        for (v, lid, c) in adj.get(u, []):
            if v not in seen:
                heapq.heappush(pq, (d + c, v, links + [lid], nodes + [v]))
    return None


def _zone_to_node(case: CaseData) -> dict[int, int]:
    return {n.zone_id: n.node_id for n in case.nodes.values() if n.zone_id >= 1}


def augment(case: CaseData, uncovered_link_ids, seed_fraction: float = 0.1) -> list[Column]:
    """Append forced-through columns covering the uncovered measured links. Returns the new columns."""
    adj = _graph(case)
    z2n = _zone_to_node(case)
    added: list[Column] = []
    # OD demand proxy: total column volume per OD (fallback to first OD)
    od_vol: dict = {}
    for c in case.columns:
        od_vol[(c.o_zone_id, c.d_zone_id)] = od_vol.get((c.o_zone_id, c.d_zone_id), 0.0) + c.volume

    for lid in sorted(set(uncovered_link_ids)):
        lk = case.links.get(lid)
        if lk is None:
            continue
        # choose an OD to route through this link: prefer an existing OD, else any zone pair
        if od_vol:
            (o, d), tot = max(od_vol.items(), key=lambda kv: kv[1])
        elif len(z2n) >= 2:
            zs = sorted(z2n)
            (o, d), tot = (zs[0], zs[-1]), 1000.0
        else:
            continue
        o_node, d_node = z2n.get(o), z2n.get(d)
        if o_node is None or d_node is None:
            continue
        head = _dijkstra(adj, o_node, lk.from_node_id)
        tail = _dijkstra(adj, lk.to_node_id, d_node)
        if head is None or tail is None:
            continue
        link_ids = head[0] + [lid] + tail[0]
        node_ids = head[1] + tail[1][1:]  # avoid duplicating the join node
        seed = max(1.0, seed_fraction * tot)
        col = Column(o_zone_id=o, d_zone_id=d, period="all", volume=seed,
                     link_ids=link_ids, node_ids=node_ids)
        case.columns.append(col)
        added.append(col)
    return added
