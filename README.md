# Heavy Precipitation Climatology — Guayas, Ecuador

**ENSO-conditioned daily extremes, an 850 hPa wind self-organizing map, and integrated vapor
transport.**

A didactic, five-notebook workflow that goes from analysis-ready precipitation and reanalysis
Zarr stores to a self-organizing-map classification of the 850 hPa flow regimes that produce
heavy rainfall over **Guayas province, Ecuador** during El Niño, and then to the integrated
vapor transport associated with each regime.

The notebooks are written to be **read as well as run**. Each one explains why a choice was made,
not only what the code does, and flags the places where a different defensible choice would
change the answer.

## The chain

```
01  Zarr stores  ──►  province-mean daily precipitation series
                      (CHIRPS + IMERG, area-weighted, cross-checked)
        │
02      └──►  daily Niño 1+2 index  ──►  ENSO phase per day
                                    ──►  top-250 wettest days
                                    ──►  El Niño subset  (the SOM sample)
        │
03      └──►  ARCO-ERA5 850 hPa u,v for exactly those days
                                    ──►  terrain-artifact diagnosis + mask
        │
04      └──►  3×3 SOM on standardized vector wind
                                    ──►  node composites + precipitation/ENSO summary
                                    ──►  QE/TE grid diagnostics
                                    ──►  domain-sensitivity test
        │
05      └──►  IVT = (1/g)∫ q·V dp   ──►  per-node moisture-transport composites
                                    ──►  does transport explain the rainfall differences?
```

| Notebook | What it establishes |
|---|---|
| [`01_data_sources_and_regional_series.ipynb`](notebooks/01_data_sources_and_regional_series.ipynb) | Store structure and chunking; province masking; area-weighted reduction; CHIRPS-vs-IMERG magnitude offset |
| [`02_enso_phase_and_day_selection.ipynb`](notebooks/02_enso_phase_and_day_selection.ipynb) | Why Niño 1+2 over Niño 3.4; monthly→daily index interpolation; phase thresholds; **frequency-normalized enrichment**; the province-mean vs. spatial-max disagreement |
| [`03_era5_wind_retrieval.ipynb`](notebooks/03_era5_wind_retrieval.ipynb) | Why ARCO-ERA5's chunk geometry makes a sparse day list cheap; snapshot vs. daily mean; the 850 hPa-below-ground terrain artifact and how to prove it |
| [`04_som_construction.ipynb`](notebooks/04_som_construction.ipynb) | Vector wind vs. wind speed as SOM input; per-cell standardization; compositing physical fields rather than SOM weights; QE/TE; **domain sensitivity** |
| [`05_ivt_fields.ipynb`](notebooks/05_ivt_fields.ipynb) | IVT column integral on uneven levels; vector mean vs. mean magnitude; repeating the terrain check for a new quantity; real dry corridor vs. masked artifact |

## Three results worth knowing before you start

1. **The precipitation metric changes the ENSO answer.** Super El Niño is ~2× overrepresented
   among the wettest *province-mean* days but shows **no** enrichment among the wettest
   *single-cell* days. The strongest warm events drive widespread organized rainfall; they do not
   make an individual convective cell more intense. (Notebook 02.)

2. **Flow regime carries information the SST index does not.** Ranking SOM nodes by mean rainfall
   does not reproduce their ranking by Niño 1+2 anomaly. A node can be the wettest while having
   the *fewest* super-El-Niño days. (Notebooks 04–05.)

3. **The 850 hPa terrain artifact is large and easy to misread.** Over the Andes the 850 hPa
   surface is below ground, and ERA5's extrapolated values produce a convincing-looking band of
   near-zero wind and low IVT along the cordillera. The tell is that it appears *identically in
   every node* — a real orographic effect would vary between flow regimes. (Notebooks 03, 05.)

## Getting started

```bash
conda env create -f environment.yml
conda activate ecuador-enso-som
jupyter lab notebooks/
```

Run the notebooks in order. Each caches its expensive output to `data/`, so re-running a later
notebook does not repeat an earlier retrieval.

### Data access

| Source | Access | Needed by |
|---|---|---|
| **ARCO-ERA5** (`gs://gcp-public-data-arco-era5/...`) | Public, anonymous — no credentials | 03, 05 |
| **BOM RMM MJO index** | Public HTTP | optional extension |
| Small reference files (province polygons, ETOPO2 subset, prepared indices, cached series) | **Ship with this repo**, in `data/` | all |
| **CHIRPS / IMERG / ERA5-monthly Zarr stores** | Group filesystem, not public | 01 only |

Because the cached series in `data/` are included, **notebooks 02–05 run end-to-end without
access to the Zarr stores.** Notebook 01 documents how those stores are structured and how the
series were derived from them; point `ZARR_ROOT` (or the individual `*_ZARR` variables) at your
own copies to re-run it:

```bash
export ZARR_ROOT=/path/to/your/zarr/stores
```

The stores themselves are subsets of public products — CHIRPS v2.0 daily from UCSB CHC, GPM
IMERG Final Daily V07 from NASA GES DISC (via `earthaccess`), and ERA5 monthly means — clipped to
`lat [-20, 15], lon [-95, -60]` and appended along time.

## Layout

```
├── notebooks/        the five notebooks, run in order
├── src/config.py     all paths, domain bounds, thresholds, SOM parameters
├── data/             reference inputs + cached intermediates (see above)
├── figures/          notebook output
└── environment.yml
```

Reference outputs from the original run are in `data/*_reference.csv`, so you can check your
results against them.

## Caveats carried through the whole workflow

- **Small sample.** ~137 days over 9 nodes; the smallest nodes are 1–2 weather events, not
  regimes. Every figure is labelled with its per-node `n` for this reason. Enlarging the sample
  (percentile-based day selection instead of a fixed top-250) is the highest-value extension.
- **Daily ENSO classification conflates ENSO with the annual cycle**, since El Niño days are not
  uniformly distributed across calendar months even within the wet season. A stricter variant
  would use month-stratified thresholds.
- **IMERG and CHIRPS are not interchangeable in absolute terms.** IMERG runs systematically lower
  over this domain (documented behaviour for tropical/orographic rainfall). Percentiles and
  exceedance counts are computed from each product's own distribution; any figure showing both
  must say which product a threshold came from.
- **A SOM is a classification, not a decomposition.** There is no variance-explained and no
  significance test. Its output is exactly as defensible as the documented choices — which is
  why notebook 04 measures grid size and domain sensitivity rather than asserting them.
- **Nothing here establishes causality or trend.** The workflow characterizes co-occurring
  structure in a fixed historical sample.

## Method references

- Hewitson, B. C. & Crane, R. G. (2002). Self-organizing maps: applications to synoptic
  climatology. *Climate Research* 22, 13–26. — the paper that brought SOMs into synoptic
  climatology.
- Sheridan, S. C. & Lee, C. C. (2011). The self-organizing map in synoptic climatological
  research. *Progress in Physical Geography* 35(1), 109–119. — standard methods review; the
  non-linearity argument for SOM over PCA/EOF.
- Wheeler, M. C. & Hendon, H. H. (2004). An all-season real-time multivariate MJO index.
  *Monthly Weather Review* 132, 1917–1932. — the RMM index definition.
- Gibson, P. B. et al. (2017). On the use of self-organizing maps for studying climate extremes.
  *JGR Atmospheres* 122. — per-node exceedance compositing for extremes.
