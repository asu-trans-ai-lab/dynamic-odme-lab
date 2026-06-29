"""Cross-file consistency checks. Most are non-fatal-but-reported; a few gate ODME."""
from __future__ import annotations

from ..model import CaseData
from .field_reader import IssueLog


def run_checks(case: CaseData, log: IssueLog) -> dict:
    stats: dict = {}

    # 1. link endpoints exist in node table
    missing_ep = 0
    for lk in case.links.values():
        if lk.from_node_id not in case.nodes or lk.to_node_id not in case.nodes:
            missing_ep += 1
    if missing_ep:
        log.warn(f"{missing_ep} links reference a node absent from node.csv")

    # 2. columns reference valid links; count coverage per link
    link_ids = set(case.links)
    covered: dict[int, float] = {}
    dropped_cols = 0
    for col in case.columns:
        if any(l not in link_ids for l in col.link_ids):
            dropped_cols += 1
            continue
        for l in col.link_ids:
            covered[l] = covered.get(l, 0.0) + col.volume
    if dropped_cols:
        log.warn(f"{dropped_cols} columns reference a link absent from link.csv (would be dropped)")
    stats["covered_links"] = covered

    # 3. resolve measurements to links + check column coverage (the key ODME identifiability gate)
    resolved, unresolved, uncovered, covered_meas = 0, 0, [], 0
    for m in case.measurements:
        lid = m.link_id
        if lid is None and m.from_node_id is not None:
            lid = case.link_by_nodepair.get((m.from_node_id, m.to_node_id))
            m.link_id = lid
        if lid is None or lid not in link_ids:
            unresolved += 1
            continue
        resolved += 1
        if covered.get(lid, 0.0) <= 0.0:
            uncovered.append(lid)
        else:
            covered_meas += 1
    stats["measurements_resolved"] = resolved
    stats["measurements_unresolved"] = unresolved
    stats["measurements_uncovered"] = uncovered
    if unresolved:
        log.warn(f"{unresolved} measurements could not be matched to a link")
    if uncovered:
        u = sorted(set(uncovered))
        head = u[:20]; tail = f" …(+{len(u)-20})" if len(u) > 20 else ""
        log.warn(f"{len(u)} measured link(s) carried by NO column -> ODME cannot fit them: "
                 f"links {head}{tail}. Need columns (run assignment) or the approximate adapter.")

    # 4. fatal gates (mirror TAPLite missing-ODME-target exit)
    usable = covered_meas
    stats["measurements_usable"] = usable
    if resolved == 0:
        log.fatal("zero usable measurements resolved -> nothing to fit")
    if not case.columns and not case.measurements:
        log.fatal("no columns and no measurements -> nothing to estimate")
    if usable <= 0 and resolved > 0:
        log.warn("all measurements are on links with no column coverage -> ODME will not move the fit "
                 "until A gains paths through those links (Stage-1 approximate adapter)")

    # 5. zones / OD sanity
    stats["zones"] = len(case.zones)
    stats["od_pairs_in_columns"] = len({(c.o_zone_id, c.d_zone_id) for c in case.columns})
    return stats
