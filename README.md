# Final presentation material - Gujarat dumpsite footprints 2016-2026
Created 25 Sep 2026 from `Locations of landfills in gujurat completer.kml`.
Figures and tables are analysis outputs. Slide wording is to be written by the student (course rule).

## Folders
| Folder / file | Contents |
|---|---|
| figures/ | Slide-ready PNG figures (200 dpi). See list below |
| figures/site_outlines/ | One outline map per site (all six epochs, area per epoch in the legend) |
| tables/final_results.xlsx | All tables: site_summary, site_by_epoch, parts_by_epoch, city_totals, group_totals, transitions, notes (method + processing log) |
| tables/*.csv | Same tables as CSV |
| data/outlines_by_site_epoch.geojson | Site outlines per epoch (parts merged), WGS84 - opens in QGIS / Google Earth Pro |
| data/outlines_by_part.geojson | Individual parts (a, b, c, old dump) per epoch |
| data/results.json | All numbers used by the figures |
| data/gujarat_boundary.geojson | Gujarat state boundary (DataMeet India maps) for the study map |
| scripts/final_analysis.py | Re-run after any KML edit: `python final_analysis.py` |
| scripts/final_figures.py | Re-draws all figures from data/results.json |
| scripts/requirements.txt | Python packages: `python -m pip install -r requirements.txt` |
| docs/Figures_Method_and_Reproduction_Guide.pdf | Step-by-step method, data sources, checks and what each figure shows |

## Decisions applied
- Sites with parts are one site; area and perimeter = sum of parts: Surat LF-2 Khajod (a+b+c), Vadodara LF-2 (old dump + a + b), Ahmedabad LF-2 (a+b).
- A part absent in an epoch counts as 0: Khajod (a) remediated 2020; Ahmedabad LF-2(b) remediated 2026; Vadodara LF-2 old dump remediated 2022; Vadodara LF-2 (a)/(b) = 0 in 2020 (cleared; illegal dumping resumed afterwards).
- 2025 images = 2024 epoch (Ahmedabad LF-1, LF-2(a), LF-3; Bhuj; Vapi). Jamnagar LF-2 and Surat LF-3 not in the study.
- Area/perimeter in EPSG:32643 (UTM 43N); perimeter after 5 m simplification; edge uncertainty = +/-2 m buffer.
- Trajectory class threshold = max(15%, 2 x edge uncertainty). Theil-Sen slope; Mann-Kendall exact p (n = 6, descriptive only).

## Figures
| File | What it shows |
|---|---|
| fig01_study_area_map.png | 14 sites in 10 cities on the Gujarat map; marker size = 2026 waste area; colour = five most populous cities vs other cities |
| fig02_total_footprint_by_group.png | Left: summed waste area per epoch by city group (+ all sites). Right: same as index 2016 = 100, incl. major cities without Khajod |
| fig03_site_area_trends.png | Area per site per epoch with +/-2 m uncertainty band and trajectory class (own y-scale per site) |
| fig04_net_change_by_site.png | Net change 2016 -> 2026 per site in ha and % |
| fig05_trajectory_quadrant.png | Growth to largest extent (x, log) vs change from largest extent to 2026 (y) |
| fig06_outlines_all_sites.png | All sites' outlines, 2016 light -> 2026 dark |
| fig08_land_turnover.png | Per site: land newly covered by waste since 2016 vs land that held waste at some point but not in 2026 |
| fig09_compactness_2016_2026.png | Compactness (4piA/P^2) 2016 vs 2026 per site |
| fig10_multipart_sites.png | Stacked area of each part for Khajod, Vadodara LF-2, Ahmedabad LF-2 |
| fig11_site_perimeter_trends.png | Perimeter per site per epoch |
| fig12_city_totals.png | City totals 2016 -> 2026 |
| fig13_results_table.png | Summary table per site (area, change, largest extent, trend, MK p, perimeter, class) |

## Key numbers (for your own wording)
- Total, all 14 sites: 152.5 ha (2016) -> 142.7 (2020) -> 192.1 (2024, largest) -> 161.0 ha (2026) = +6% net.
- Five most populous cities (9 sites): 141.7 -> 134.8 ha (-5%); without Khajod 73.0 -> 103.6 ha (+42%).
- Other cities (5 sites): 10.7 -> 26.2 ha (+144%), larger at every epoch after 2018.
- Growth concentrated: Rajkot +20.8, Gandhinagar +11.5, Bhavnagar +11.1, Vadodara LF-1 +9.9 ha = 85% of all net gain (62.7 ha).
- Largest declines: Khajod -37.5 ha (-55%), Pirana -8.6 ha (-22%), Vadodara LF-2 -6.2 ha (-89%), Surat-Bhatar -1.6 ha (-79%).
- Classes: 7 expanding, 3 contracting, 3 rise-and-fall, 1 cleared-then-regrowing (Khajod: 68.7 -> 19.0 ha in 2020 -> 53.5 in 2024 -> 31.2 in 2026).
- Mann-Kendall p < 0.05: Ahmedabad LF-3, Gandhinagar, Rajkot, Vadodara LF-1 (increasing); Surat-Bhatar, Vadodara LF-2 (decreasing).
- Land turnover: 97.7 ha newly covered since 2016; 142.4 ha held waste at some point but is not under waste in 2026 (cleared, biomined, built over or reshaped).
- Shape: compactness fell sharply at Gandhinagar (0.80 -> 0.17), Mehsana (0.73 -> 0.15), Vadodara LF-1 (0.70 -> 0.31), Bhavnagar (0.44 -> 0.23); rose at Ahmedabad LF-2 (0.31 -> 0.49), Rajkot (0.33 -> 0.43), Bhuj (0.15 -> 0.24).
- City totals: Surat 70.7 -> 31.6 ha (-55%); Ahmedabad 50.0 -> 46.6 (-7%); Vadodara 10.0 -> 13.6 (+36%); Rajkot 7.3 -> 28.1 (+285%); Gandhinagar 1.1 -> 12.6 (+1033%).

## Open point
Rajkot: traced waste area grows 7.3 -> 28.1 ha while news/PIB report Nakrawadi's legacy dump turned into a 20-acre urban forest. Confirm the traced area is the active dumping area beside the remediated part.
