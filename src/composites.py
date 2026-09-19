"""Per-SOM-node composites of gridded daily precipitation.

Deliberately importable and free of any plotting dependency, so that the same code
runs in notebook 06 and in a cluster job next to the Zarr stores (where cartopy is
typically not installed). The reduction turns gigabytes of gridded daily data into a
file of a few tens of kilobytes; that asymmetry is the whole reason to run it next to
the data rather than pulling the daily fields across the network.
"""

import warnings

import numpy as np
import pandas as pd
import xarray as xr


def coord_names(ds):
    """Stores disagree: CHIRPS/ERA5 use latitude/longitude, IMERG uses lat/lon."""
    lat = "latitude" if "latitude" in ds.coords else "lat"
    lon = "longitude" if "longitude" in ds.coords else "lon"
    return lat, lon


def precip_var(ds):
    """First data variable whose name looks like a precipitation field."""
    for v in ds.data_vars:
        if "precip" in v.lower():
            return v
    raise KeyError(f"no precipitation-like variable in {list(ds.data_vars)}")


def subset_box(ds, extent):
    """Spatial subset that works regardless of latitude sort order.

    `extent` is (lon_min, lon_max, lat_min, lat_max).

    Slicing an ascending axis with descending bounds returns an EMPTY array and
    raises nothing, so the direction has to be detected rather than assumed. This
    is the single most common way to silently get an all-NaN composite.
    """
    lat_name, lon_name = coord_names(ds)
    lon_min, lon_max, lat_min, lat_max = extent

    lat_vals = ds[lat_name].values
    lat_slice = (slice(lat_min, lat_max) if lat_vals[0] < lat_vals[-1]
                 else slice(lat_max, lat_min))
    lon_vals = ds[lon_name].values
    lon_slice = (slice(lon_min, lon_max) if lon_vals[0] < lon_vals[-1]
                 else slice(lon_max, lon_min))

    out = ds.sel({lat_name: lat_slice, lon_name: lon_slice})
    if out.sizes[lat_name] == 0 or out.sizes[lon_name] == 0:
        raise ValueError(
            f"empty subset for extent {extent}: got "
            f"{out.sizes[lat_name]}x{out.sizes[lon_name]} cells")
    return out


def node_precip_composites(store, assignments, extent, thresholds=(25, 50),
                           n_nodes=9, verbose=True):
    """Composite daily precipitation within each SOM node.

    Parameters
    ----------
    store : str
        Path or URL of a Zarr store with a daily precipitation variable.
    assignments : DataFrame
        Columns ``date`` (datetime) and ``som_node`` (int).
    extent : tuple
        (lon_min, lon_max, lat_min, lat_max) subdomain to composite over.
    thresholds : iterable of float
        Daily totals (mm) at which to compute exceedance frequency.

    Returns
    -------
    xarray.Dataset
        ``mean_precip`` plus one ``freq_gt<T>`` field per threshold, each on
        (node, lat, lon), and ``n_days`` on (node,). Nodes with no covered days
        are all-NaN with ``n_days = 0``.

    Notes
    -----
    Days in `assignments` that the store does not cover are dropped and reported.
    IMERG starts in 2000, so it covers only part of a 1981-onward day list -- the
    per-node ``n_days`` is therefore product-specific and must be carried into any
    comparison between products.
    """
    ds = xr.open_zarr(store)
    lat_name, lon_name = coord_names(ds)
    sub = subset_box(ds, extent)
    var = precip_var(sub)

    store_days = pd.to_datetime(sub.time.values).normalize()
    want = assignments.assign(date=pd.to_datetime(assignments["date"]).dt.normalize())
    covered = want[want["date"].isin(set(store_days))]
    if verbose:
        print(f"{store}\n  variable: {var}; grid "
              f"{sub.sizes[lat_name]}x{sub.sizes[lon_name]}")
        print(f"  days requested {len(want)}, covered by store {len(covered)}"
              f"{'' if len(covered) == len(want) else '  <- product does not span the full list'}",
              flush=True)
    if covered.empty:
        raise ValueError("no requested days fall inside the store's time range")

    block = sub[var].sel(time=covered["date"].values).load()
    P = block.values
    node_id = covered["som_node"].to_numpy()

    ny, nx = P.shape[1], P.shape[2]
    fields = {"mean_precip": np.full((n_nodes, ny, nx), np.nan, "float32")}
    for t in thresholds:
        fields[f"freq_gt{int(t)}"] = np.full((n_nodes, ny, nx), np.nan, "float32")
    n_days = np.zeros(n_nodes, dtype="int32")

    for k in range(n_nodes):
        m = node_id == k
        n_days[k] = int(m.sum())
        if not m.any():
            continue
        b = P[m]
        # Cells that are NaN on every day of the node (outside the product's valid
        # mask) legitimately reduce to NaN; numpy warns on that and the warning is
        # noise here, not a signal worth surfacing on every run.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            fields["mean_precip"][k] = np.nanmean(b, axis=0)
            for t in thresholds:
                fields[f"freq_gt{int(t)}"][k] = 100.0 * np.nanmean(b > t, axis=0)
        if verbose:
            print(f"  node {k}: n={n_days[k]}", flush=True)

    out = xr.Dataset(
        {k: (("node", "lat", "lon"), v) for k, v in fields.items()}
        | {"n_days": (("node",), n_days)},
        coords={"node": np.arange(n_nodes),
                "lat": sub[lat_name].values, "lon": sub[lon_name].values},
    )
    out.attrs.update({
        "source_store": str(store),
        "precip_variable": var,
        "extent": str(extent),
        "thresholds_mm": list(thresholds),
        "n_days_requested": int(len(want)),
        "n_days_covered": int(len(covered)),
        "note": ("per-SOM-node composites of daily precipitation; n_days is "
                 "product-specific where the store does not span the full day list"),
    })
    for t in thresholds:
        out[f"freq_gt{int(t)}"].attrs["units"] = "% of the node's days"
    out["mean_precip"].attrs["units"] = "mm/day"
    return out
