# `data/`

Two kinds of file live here.

## Tracked — reference inputs and cached series

These ship with the repository so that **notebooks 02–05 run without access to the Zarr
stores**, and so you can check your results against the original run.

| File | What it is | Produced by |
|---|---|---|
| `ecuador_provinces.gpkg` | Ecuador province polygons (GeoPackage) | external |
| `etopo2_nwsa.nc` | ETOPO2 elevation, clipped to the NWSA window | external |
| `enso_daily_1981-present.csv` | Daily Niño 1+2 anomaly, mid-month anchored and linearly interpolated from CPC monthly ERSST anomalies (1991–2020 base) | notebook 02 |
| `mjo_rmm_index_1981_present.csv` | BOM RMM MJO index (RMM1, RMM2, phase, amplitude), parsed | optional extension |
| `guayas_daily_series.csv` | Guayas province area-weighted mean + spatial max daily CHIRPS precipitation | notebook 01 |
| `guayas_imerg_daily_series.csv` | Same reduction on IMERG (2000-06 onward) | notebook 01 |
| `heavy_enso_positive_days.csv` | The selected day list: top-250 province-mean days ∩ El Niño | notebook 02 |
| `*_reference.csv` | Outputs of the original run, for comparison | notebooks 04–05 |

## Untracked — regenerated on demand

Listed in `.gitignore`. These are retrieval caches and derived arrays; delete them to force a
re-fetch or recompute.

| File | Size | Produced by |
|---|---|---|
| `era5_850_wind_heavy_enso.nc` | ~30 MB | notebook 03 |
| `era5_ivt_heavy_enso.nc` | ~65 MB | notebook 05 |
| `terrain_mask_1500m.npy` | small | notebook 03 |
| `som_node_*.csv`, `som_node_composites_*.npz` | small | notebooks 04–05 |

## A note on the daily ENSO index

Monthly CPC values are anchored at **day 15** of each month before interpolation. Anchoring at
the 1st instead would shift the whole index ~15 days early, which is enough to misclassify days
near a threshold crossing during a rapidly developing event.
