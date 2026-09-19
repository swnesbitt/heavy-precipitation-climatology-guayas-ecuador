#!/usr/bin/env python
"""Run the notebook-06 reduction next to the Zarr stores.

Notebook 06 calls exactly the same function; this driver exists so the reduction can
run on the cluster that hosts the stores, where a plotting stack is usually absent.
It writes the two small composite files the notebook then reads from ``data/``.

    python scripts/compute_node_composites.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import (CHIRPS_ZARR, IMERG_ZARR, DATA_DIR, ECUADOR_EXTENT,
                    PRECIP_THRESHOLDS, SOM_GRID)
from composites import node_precip_composites

assign_path = DATA_DIR / "som_node_assignments.csv"
if not assign_path.exists():
    assign_path = DATA_DIR / "som_node_assignments_reference.csv"
assignments = pd.read_csv(assign_path, parse_dates=["date"])
print(f"node assignments: {assign_path.name} ({len(assignments)} days)\n")

n_nodes = SOM_GRID[0] * SOM_GRID[1]
for store, out_name in [(CHIRPS_ZARR, "chirps_som_node_composites.nc"),
                        (IMERG_ZARR, "imerg_som_node_composites.nc")]:
    ds = node_precip_composites(store, assignments, ECUADOR_EXTENT,
                                thresholds=PRECIP_THRESHOLDS, n_nodes=n_nodes)
    target = DATA_DIR / out_name
    ds.to_netcdf(target)
    print(f"  -> {target}  ({target.stat().st_size / 1e3:.0f} kB)\n")

print("done")
