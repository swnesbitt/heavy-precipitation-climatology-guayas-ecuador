"""Shared paths, domain bounds, and analysis parameters.

Every notebook imports from here so that a change of domain, threshold, or store
location happens in exactly one place. Values that are *scientific choices* rather
than conveniences are commented with the reasoning.
"""

import os
from pathlib import Path

# --------------------------------------------------------------------------- #
# Local paths
# --------------------------------------------------------------------------- #
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
FIG_DIR = REPO_ROOT / "figures"
DATA_DIR.mkdir(exist_ok=True)
FIG_DIR.mkdir(exist_ok=True)

PROVINCES_GPKG = DATA_DIR / "ecuador_provinces.gpkg"
ETOPO_NC = DATA_DIR / "etopo2_nwsa.nc"

# Cartopy's Natural Earth cache, kept inside the repo rather than in the user's home
# directory. Two reasons: the default ~/.local/share/cartopy path is not writable in
# some managed/containerised environments, and pinning it here means a run does not
# silently depend on whatever happens to be cached in a given user's home. Cartopy
# downloads what it needs on first use (~10 MB); the directory is gitignored.
CARTOPY_DIR = REPO_ROOT / "cartopy_data"
CARTOPY_DIR.mkdir(exist_ok=True)
try:
    import cartopy as _cartopy
    _cartopy.config["data_dir"] = str(CARTOPY_DIR)
except ImportError:      # notebooks 01-03 do not need cartopy
    pass

# --------------------------------------------------------------------------- #
# Zarr stores
#
# These are analysis-ready subsets held on a group filesystem, NOT public data.
# Override with environment variables to point at your own copies, or see
# README.md for how they were built from the upstream products.
# --------------------------------------------------------------------------- #
ZARR_ROOT = os.environ.get("ZARR_ROOT", "/data/gpm/a/snesbitt")

CHIRPS_ZARR = os.environ.get("CHIRPS_ZARR", f"{ZARR_ROOT}/chirps-nwsa.zarr")
IMERG_ZARR = os.environ.get("IMERG_ZARR", f"{ZARR_ROOT}/imerg-nwsa.zarr")
ERA5_MONTHLY_PL_ZARR = os.environ.get("ERA5_MONTHLY_PL_ZARR", f"{ZARR_ROOT}/era5-monthly-pl-nwsa.zarr")
ERA5_MONTHLY_SFC_ZARR = os.environ.get("ERA5_MONTHLY_SFC_ZARR", f"{ZARR_ROOT}/era5-monthly-sfc-nwsa.zarr")
ESACCI_SM_ZARR = os.environ.get("ESACCI_SM_ZARR", f"{ZARR_ROOT}/esacci-sm-nwsa.zarr")

# ARCO-ERA5: public, anonymous read, no credentials needed.
ARCO_STORE = "gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3"

# Same store addressed as a bucket-qualified HTTPS endpoint. Used as a fallback by
# open_arco() below: gcsfs talks to the *path-style* JSON API at storage.googleapis.com,
# which many institutional networks and egress proxies block, while the virtual-hosted
# bucket URL is ordinary HTTPS and usually passes.
ARCO_STORE_HTTPS = ("https://gcp-public-data-arco-era5.storage.googleapis.com"
                    "/ar/full_37-1h-0p25deg-chunk-1.zarr-v3")


def _gcs_json_api_reachable(timeout=5):
    """Can we resolve the path-style GCS API host that gcsfs uses?"""
    import socket
    try:
        socket.setdefaulttimeout(timeout)
        socket.getaddrinfo("storage.googleapis.com", 443)
        return True
    except OSError:
        return False


def open_arco(quiet=True, **kwargs):
    """Open the ARCO-ERA5 Zarr store, tolerating restricted networks.

    Prefers the canonical ``gs://`` path via gcsfs. gcsfs talks to the *path-style*
    JSON API at ``storage.googleapis.com``; where that host is blocked or unresolvable
    (institutional egress proxies commonly allow only virtual-hosted bucket URLs), this
    falls back to the same store over plain HTTPS at the bucket-qualified hostname,
    with ``trust_env`` so ``HTTPS_PROXY`` / ``NO_PROXY`` are honoured.

    The reachability probe is a cheap DNS lookup done up front, so the fallback path
    does not have to surface a gcsfs stack trace to discover it is needed.

    Returns an ``xarray.Dataset``; extra kwargs pass through to ``open_zarr``.
    """
    import xarray as xr

    opts = {"chunks": None, "decode_timedelta": True, **kwargs}

    if _gcs_json_api_reachable():
        try:
            return xr.open_zarr(ARCO_STORE, storage_options={"token": "anon"}, **opts)
        except Exception as exc_gs:
            if not quiet:
                print(f"gs:// route failed ({type(exc_gs).__name__}); trying HTTPS")

    try:
        import fsspec
        mapper = fsspec.filesystem("https", client_kwargs={"trust_env": True}).get_mapper(
            ARCO_STORE_HTTPS)
        ds = xr.open_zarr(mapper, **opts)
        if not quiet:
            print("opened ARCO-ERA5 via the bucket-qualified HTTPS endpoint")
        return ds
    except Exception as exc_http:
        raise RuntimeError(
            "ARCO-ERA5 is unreachable.\n"
            f"  path-style GCS host resolvable: {_gcs_json_api_reachable()}\n"
            f"  HTTPS route -> {type(exc_http).__name__}: {str(exc_http)[:200]}"
        ) from exc_http

# BOM Real-time Multivariate MJO (RMM) index, Wheeler-Hendon.
# NOTE the path: the widely-cited /climate/mjo/graphics/ copy of this file stopped
# updating in early 2024. This /clim_data/IDCKGEM000/ path is the live one.
BOM_RMM_URL = "https://www.bom.gov.au/clim_data/IDCKGEM000/rmm.74toRealtime.txt"

# --------------------------------------------------------------------------- #
# Domain
#
# NW South America window. Wide enough to contain the synoptic features that
# notebook 04's sensitivity test shows are doing real classificatory work
# (cross-equatorial flow, the Pacific moisture band, Amazon-side circulation).
# --------------------------------------------------------------------------- #
NWSA_LAT = (-20.0, 15.0)            # (south, north)
NWSA_LON = (-95.0, -60.0)           # (west, east), -180..180 convention
NWSA_LON_360 = (265.0, 300.0)       # same window in the 0..360 convention ARCO-ERA5 uses
NWSA_EXTENT = (-95, -60, -20, 15)   # cartopy set_extent order

ECUADOR_EXTENT = (-81.4, -74.9, -5.3, 1.8)
GUAYAQUIL = (-2.1894, -79.8891)     # (lat, lon)

# --------------------------------------------------------------------------- #
# ENSO phase thresholds, on the daily Nino 1+2 anomaly (deg C)
#
# +/-0.5 is the conventional ENSO threshold. The +2.0 "super" cut is a deliberate
# addition: Nino 1+2 anomalies during coastal events reach values where the
# rainfall response is plausibly non-linear, and lumping those with +0.6 C days
# would hide it. See notebook 02.
# --------------------------------------------------------------------------- #
NINO12_THRESHOLDS = {"super": 2.0, "regular": 0.5}

# Number of wettest days to rank before subsetting to El Nino phases.
N_TOP_DAYS = 250

# --------------------------------------------------------------------------- #
# ERA5 retrieval
# --------------------------------------------------------------------------- #
WIND_LEVEL = 850          # hPa; ~1500 m -- see the terrain caveat in notebook 03
SNAPSHOT_HOUR = 12        # UTC; ~07:00 local in Ecuador

# Levels for the IVT column integral (hPa, ascending). 300 hPa top is the
# conventional cut in the atmospheric-river literature; spacing is denser near
# the surface where the moisture is.
IVT_LEVELS = [300, 350, 400, 450, 500, 550, 600, 650, 700, 750,
              775, 800, 825, 850, 875, 900, 925, 950, 975, 1000]

G = 9.80665               # m/s^2, standard gravity

# Terrain above this height is masked in wind and IVT figures: the 850 hPa
# surface lies at or below ground there, so ERA5 reports a downward
# extrapolation rather than a measurement. Verified in notebooks 03 and 05 by
# stratifying the field against elevation -- the collapse appears identically
# in every SOM node, which is what distinguishes an artifact from a signal.
TERRAIN_MASK_M = 1500

# Drawn as a reference contour on precipitation maps -- NOT a mask. Roughly the
# height at which the coastal plain gives way to the Andean slope, so it marks
# where an orographic rainfall maximum is expected. Distinct in purpose from
# TERRAIN_MASK_M above, which hides non-physical reanalysis values.
TERRAIN_CONTOUR_M = 750

# --------------------------------------------------------------------------- #
# SOM configuration
#
# 3x3 = 9 nodes. Driven by sample size first (~137 days / 9 nodes ~ 15 days per
# node; a 4x4 grid leaves the smallest nodes uninterpretable), and consistent
# with the 6-12 node range typical in the synoptic-SOM literature. Notebook 04
# measures this rather than asserting it (quantization / topographic error).
#
# random_seed is fixed because SOM training is stochastic; an unseeded run is
# not reproducible.
# --------------------------------------------------------------------------- #
SOM_GRID = (3, 3)
SOM_PARAMS = {
    "sigma": 1.0,
    "learning_rate": 0.5,
    "random_seed": 42,
    "neighborhood_function": "gaussian",
    "n_iterations": 8000,
}

# Precipitation thresholds for the per-node exceedance-frequency composites (mm/day).
PRECIP_THRESHOLDS = [25, 50]
