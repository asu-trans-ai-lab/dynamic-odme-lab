"""Core data structures shared across readers, matrix builder, and solver.

Everything is keyed so static (T=1) and dynamic (T>1) use the same objects:
a measurement is (link, t); a demand cell is (od, tau). At T=1 the time index is just 0.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Node:
    node_id: int
    zone_id: int = 0          # >=1 means this node is a zone/centroid
    x: float = 0.0
    y: float = 0.0


@dataclass
class Link:
    link_id: int
    from_node_id: int
    to_node_id: int
    lanes: int = 1
    capacity: float = 0.0     # per-lane veh/h; 0 means "filled/unknown" (flagged)
    free_speed: float = 10.0
    length: float = 1.0       # in model length unit (mile/km)
    link_type: int = 1
    alpha: float = 0.15
    beta: float = 4.0
    plf: float = 1.0
    ref_volume: float = -1.0  # Path A measurement; <0 means none
    obs_volume: float = -1.0
    fftt_min: float = 0.0     # free-flow travel time (minutes), derived if 0

    @property
    def link_capacity(self) -> float:
        return self.capacity * max(1, self.lanes)


@dataclass
class Column:
    """One path/route = one source of A entries."""
    o_zone_id: int
    d_zone_id: int
    period: str
    volume: float
    link_ids: list[int]
    node_ids: list[int] = field(default_factory=list)
    # departure-time bin (tau) for this column; used at T>1 to place its links in time
    tau: int = 0
    # base-path id linking the T time-columns that share a route (for temporal smoothing)
    group_id: int = -1
    # cumulative entry time (minutes) at each link on the path; refines tau per-link for T>1
    entry_times_min: Optional[list[float]] = None


@dataclass
class Measurement:
    """Normalized observation. link_id resolved from (from,to) when needed."""
    obs_volume: float
    link_id: Optional[int] = None
    from_node_id: Optional[int] = None
    to_node_id: Optional[int] = None
    o_zone_id: Optional[int] = None
    d_zone_id: Optional[int] = None
    weight: float = 1.0
    upper_bound_flag: int = 0
    measurement_type: str = "link_count"
    time_period: Optional[str] = None
    t_bin: Optional[int] = None   # time-interval index for y_{a,t}; None => broadcast to t=0
    source_path: str = "A"    # which ingestion path produced it (A/B/C)


@dataclass
class TimeGrid:
    start_hour: float = 7.0
    end_hour: float = 8.0
    interval_minutes: float = 60.0

    @property
    def T(self) -> int:
        span_min = (self.end_hour - self.start_hour) * 60.0
        if self.interval_minutes <= 0 or self.interval_minutes >= span_min:
            return 1
        return max(1, round(span_min / self.interval_minutes))

    @property
    def is_static(self) -> bool:
        return self.T == 1


@dataclass
class CaseData:
    name: str
    nodes: dict[int, Node] = field(default_factory=dict)
    links: dict[int, Link] = field(default_factory=dict)
    columns: list[Column] = field(default_factory=list)
    measurements: list[Measurement] = field(default_factory=list)
    settings: dict = field(default_factory=dict)
    time_grid: TimeGrid = field(default_factory=TimeGrid)
    # phi[(origin_or_ALL)] -> list of length T summing to 1; populated at T>1
    phi: dict = field(default_factory=dict)

    # derived lookups
    link_by_nodepair: dict = field(default_factory=dict)

    @property
    def zones(self) -> set[int]:
        return {n.zone_id for n in self.nodes.values() if n.zone_id >= 1}

    def build_indexes(self) -> None:
        self.link_by_nodepair = {
            (lk.from_node_id, lk.to_node_id): lk.link_id for lk in self.links.values()
        }
