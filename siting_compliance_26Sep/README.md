# siting_compliance_26Sep - dumpsites vs the SWM Rules 2026 landfill siting criteria, 14 sites

Full step-by-step documentation: `docs/Siting_Compliance_Method_and_Reproduction_Guide.docx` (PDF copy beside it).

Rules: Solid Waste Management Rules, 2026 (S.O. 388(E), 27 Jan 2026), Schedule II(A)(vii)-(viii) - the
"Landfill siting rules (SWM 2026 rules)" table of Lecture 8. 10 of the 12 criteria are checked; water-supply
wells and the land-use-plan criterion are not assessable from open data.

## Run
```
cd scripts
python -m pip install -r requirements.txt
python 01_download_layers.py    # OSM (Overpass), aerodromes, protected areas, Overture buildings, GHSL, JRC flood map (~15 min)
python 02_siting_check.py       # rule-by-rule check, 2026 outline (main) and 2016 outline (comparison) (~10 s)
python 03_figures_tables.py     # figures/figS1-S6, per-site maps, siting_results.xlsx, Google Earth KML (~8 min)
python 04_verify.py             # recomputes the key numbers by an independent route
```
or double-click `scripts/run_all.bat`. Step 01 skips files already in `data/raw`, so keeping that folder
reproduces the exact numbers (OSM and Overture change over time).

## Inputs
- `../Locations of landfills in gujurat Completed.kml` (master outlines; same parsing as final_analysis.py)
- downloaded by step 01 into `data/raw/` (sources and dates in `data/sources.json`)

## Main results
- `outputs/tables/siting_results.xlsx` - summary, verdict matrices (2026, 2016), distances, detail, habitation, airports
- `outputs/tables/siting_long.csv` - one row per site x epoch x rule: measured value, nearest feature, verdict, basis
- `figures/figS1_compliance_matrix_2026.png` - the site x rule grid
- `outputs/siting_check_layers.kml` - outlines, 100/200 m rings and flagged features, for checking in Google Earth Pro

Habitation (R4) includes an imagery review stored in `scripts/config.py` (HABITATION_REVIEW); confirm the four
'uncertain' sites in Google Earth Pro and edit / re-run step 02 if needed.
