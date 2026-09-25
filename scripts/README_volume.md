# Volume and height: all sites run (v2, 25 Sep 2026)

**Sites:** the 12 sites in `Locations of landfills in gujurat (3).kml`, excluding Khajod (SUR-02) and Vadodara (VAD-01/02) as instructed. The included sites are AHM-01, AHM-02A, AHM-02B, AHM-03, SUR-01, RAJ-01, BHV-01, GNR-01, JAM-01, BHJ-01, MEH-01 and VAP-01. Outlines are parsed with the same rules as `analysis/trend_analysis.py`, and outline areas match `site_summary.csv`.

Run with `python volume_height.py` (all sites) or `python volume_height.py AHM-01 RAJ-01` (selected sites).

## Files
| File | Contents |
|---|---|
| volume_height.py | v2 script: all sites, per-site DEM tiles, quality flag, change uncertainty |
| dem/glo30/glo30_<SITE>_clip.tif | Copernicus GLO-30 clip for each site (checked against the full tiles: identical) |
| dem/TDM1_* | DLR tiles. Currently only N21E072 is here (Bhavnagar, Surat) |
| outputs/all_sites_volume_by_dem.csv | One row per site × DEM: volume, uncertainty, heights, tonnes, quality flag |
| outputs/all_sites_volume_change.csv | DCM change per site (only sites whose DLR tile is present) |
| outputs/all_sites_volume_summary.png | Bar chart of all sites (log scale; hatched = poor base) |
| outputs/<SITE>/ | Height maps, profiles, run info and CSVs for each site |
| outputs/BHV-01_* (top level) | Old pilot outputs (24 Sep), superseded by outputs/BHV-01/. Identical numbers |

## Method (unchanged from the pilot, plus two additions)
- Footprint = union of all outlines. DEM on a 10 m UTM grid. Base = plane fitted to a ring 30-150 m outside the footprint (±3 MAD). Volume = net sum of height above base. Uncertainty = base level + noise + base-model spread.
- **New:** other sites' footprints are removed from each ring. This matters for Ahmedabad, where LF-2(a) and LF-2(b) are about 300 m apart.
- **New:** a quality flag for the absolute volume:
  - good: uncertainty ≤10%
  - fair: 10-25%
  - poor: >25%, meaning complex terrain or a noisy urban ring
  - below ground: net volume below zero (a pit or cell)
  - small: footprint under 3 ha
- **New:** change uncertainty. It combines the level error of the ring with random error over independent 30 m cells.
- The DCM change does **not** depend on the base surface. It is the robust number wherever a tile exists.

## Results (2011-15 surface, inside each site's full 2016-26 footprint)
| Site | Footprint ha | Volume m³ (± 1σ) | Max height m | Quality | Reading |
|---|---|---|---|---|---|
| AHM-01 Pirana | 47.4 | 3,951,000 ± 27,000 | 32 | good | Large legacy mound already in 2011-15 |
| GNR-01 Gandhinagar | 17.0 | 1,606,000 ± 629,000 | 21 | poor | Site is on the Sabarmati valley slope; the "volume" is mostly terrain. Do not use |
| BHJ-01 Bhuj | 10.3 | 472,000 ± 92,000 | 8.7 | fair | Undulating ground (flat base 293k vs IDW 407k). Treat as indicative |
| RAJ-01 Rajkot | 30.2 | 364,000 ± 164,000 | 7.4 | poor | Uneven surroundings. Do not use |
| BHV-01 Bhavnagar | 28.0 | 66,600 ± 3,100 (EDEM) | 4.7 | good | See change below |
| VAP-01 Vapi | 2.0 | 59,000 ± 26,000 | 5.8 | poor, small | Next to a ravine. Do not use |
| SUR-01 Bhatar | 2.3 | 44,900 ± 17,700 (EDEM) | 4.8 | poor, small | Urban ring |
| JAM-01 Jamnagar | 3.4 | 23,800 ± 5,500 | 2.2 | fair | Low mound |
| AHM-02B | 9.4 | 10,600 ± 20,800 | 2.6 | poor | About zero: little above ground in 2011-15 |
| MEH-01 Mehsana | 5.1 | -18,700 ± 10,100 | 6.1 | poor | About zero or slightly below ground |
| AHM-02A | 9.7 | -85,300 ± 16,000 | 0.5 | below ground | Ground was lower than the surroundings in 2011-15 (low land or pit later filled) |
| AHM-03 | 8.6 | -387,700 ± 16,600 | 4.8 | below ground | In 2011-15 a walled rectangular cell dug about 4-5 m below the surroundings. Waste went into a pit, so above-ground volume will understate it |

**Key point:** for most sites, the waste arrived after 2015 (see the area series). Their 2011-15 volume therefore mostly describes the ground before the waste, not the waste. The number that answers "how much waste was added" is the DCM change, and that needs the DLR tile for each site.

## Change 2011-13 → DCM date (tiles present)
| Site | DCM date | Change m³ (± 1σ) | Tonnes (0.8-1.2 t/m³) | Reading |
|---|---|---|---|---|
| BHV-01 | 20 Jun 2019 | **+121,500 ± 11,100** | 97,000-146,000 | Robust. The volume difference (+126,700) agrees within 4% |
| SUR-01 | 13 Mar 2019 | +25,600 ± 10,100 (raw +12,200) | 20,000-31,000 | Weak. Urban noise of ±2 m in the ring, and a small site. Report as "no clear change" or drop |

Checks: GLO-30 and TanDEM-X EDEM give the same volume at both sites (difference 260 and -173 m³).

## Pirana cross-check
The DEM gives 3.95 million m³ above the surrounding ground in 2011-15, with a 32 m peak (the ground around the site is about 43 m above sea level). The widely quoted 126 lakh t (12.6 Mt, AMC via press, 2023-24) would imply an impossible density of about 3.2 t/m³. So either the reported tonnage is inflated, or the DEM volume is a strong lower bound. Reasons it could be low:
- A 30 m DSM smooths the peaks (reported heights are 50-75 m).
- Waste below ground level is not counted.
- The traced 47 ha is smaller than the quoted 84 ha site.

This makes a good point for the discussion or limitations slide.

## To complete the change for the other sites (needs your DLR login)
Download the **DCM LAST** zip for each tile below and unzip it into `VOlume and height/dem/`. The EDEM is optional: the script falls back to GLO-30, which agreed within 0.4%.
| Tile | Sites |
|---|---|
| N22E072 | AHM-01, AHM-02A, AHM-02B, AHM-03 |
| N22E070 | RAJ-01, JAM-01 |
| N23E072 | GNR-01, MEH-01 |
| N23E069 | BHJ-01 |
| N20E072 | VAP-01 |

Then re-run `python volume_height.py`. No code changes are needed.

## Density
0.8-1.2 t/m³ comes from the MSW unit-weight literature (Zekkos et al. 2006, J. Geotech. Geoenviron. Eng. 132(10)). Verify it before citing. The CPCB legacy-waste guidelines (2019) give no density.

## Caveats for the limitations slide (points only)
- 30 m DEMs: sites under 3 ha (SUR-01, VAP-01) are unreliable.
- The base surface from the surrounding ground fails in valleys, on slopes and in dense urban areas (GNR, RAJ, VAP). The DCM change avoids this problem.
- These are surface models (DSM): sheds, trucks and trees count as height.
- Waste below ground level is not counted, so volumes are lower bounds (AHM-03 is an extreme case).
- Only 2 dates: 2011-15 and one DCM date per tile (2019 here). These do not line up with the area years.
- Radar penetration differences can create apparent change (DLR caveat).
