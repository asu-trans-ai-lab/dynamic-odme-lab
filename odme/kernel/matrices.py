"""Explicit transportation computation-graph matrices: y = M . Delta . R . d.

  d  in R^K   : OD demand (K OD pairs)
  R  in R^PxK : OD-to-path share matrix       (path p belongs to OD k, share R[p,k])
  h = R d     : path flow (P paths)
  Delta in R^AxP : path-link incidence         (link a on path p)
  x = Delta h : link flow (A links)
  M  in R^SxA : sensor-link mapping            (sensor s on link a)
  y = M x     : observations (S sensors)

So the assignment-visible operator is  G = M . Delta . R  in R^SxK, and y = G d.
This formalizes what build_A does implicitly, and exposes rank(G) for the
underdetermination gate.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass

import numpy as np


def _read(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _ids(seq):
    return [int(float(x)) for x in str(seq).replace(",", ";").split(";") if str(x).strip()]


@dataclass
class Kernel:
    od_ids: list
    path_ids: list
    link_ids: list
    sensor_ids: list
    R: np.ndarray        # P x K
    Delta: np.ndarray    # A x P
    M: np.ndarray        # S x A
    d_seed: np.ndarray   # K
    G: np.ndarray        # S x K  (= M Delta R)

    def assign(self, d):
        return self.G @ d

    @property
    def rank_G(self):
        return int(np.linalg.matrix_rank(self.G)) if self.G.size else 0


def build_kernel(case_dir: str) -> Kernel:
    od = _read(os.path.join(case_dir, "od.csv"))
    paths = _read(os.path.join(case_dir, "path.csv"))
    links = _read(os.path.join(case_dir, "link.csv"))
    sensors = _read(os.path.join(case_dir, "sensor.csv"))

    od_ids = [int(r["od_id"]) for r in od]
    od_ix = {k: i for i, k in enumerate(od_ids)}
    path_ids = [int(r["path_id"]) for r in paths]
    link_ids = [int(float(r["link_id"])) for r in links]
    link_ix = {a: i for i, a in enumerate(link_ids)}
    sensor_ids = [r["sensor_id"] for r in sensors]

    K, P, A, S = len(od_ids), len(path_ids), len(link_ids), len(sensor_ids)
    R = np.zeros((P, K)); Delta = np.zeros((A, P)); M = np.zeros((S, A))

    for pi, r in enumerate(paths):
        R[pi, od_ix[int(r["od_id"])]] = float(r.get("share", 1.0) or 1.0)
        for a in _ids(r.get("link_id_sequence", "")):
            if a in link_ix:
                Delta[link_ix[a], pi] = 1.0
    for si, r in enumerate(sensors):
        a = int(float(r["link_id"]))
        if a in link_ix:
            M[si, link_ix[a]] = 1.0

    d_seed = np.array([float(r.get("seed_demand", 0) or 0) for r in od])
    G = M @ Delta @ R
    return Kernel(od_ids, path_ids, link_ids, sensor_ids, R, Delta, M, d_seed, G)


def load_observations(case_dir: str):
    """sensor_id -> {time_period: observed}.  Returns (obs_by_sensor, time_periods)."""
    rows = _read(os.path.join(case_dir, "measurement.csv"))
    obs = {}
    periods = []
    for r in rows:
        t = r.get("time_period", "0")
        if t not in periods:
            periods.append(t)
        obs.setdefault(r["sensor_id"], {})[t] = float(r["observed_count"])
    return obs, periods
