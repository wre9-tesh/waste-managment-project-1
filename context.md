# Project Context: Gujarat Dumpsite RS-GIS Study

**Last updated:** Friday 25 September 2026, ~2:30 am (volume run for all 12 sites)
**Submission:** Saturday 26 September 2026, 2:00 pm
**Previous version:** old/context_22Sep_superseded.md (earlier progress was discarded; the project restarted from zero on 22 Sep)

## Who this is for
Solo PhD student, Civil Engineering, IIT Gandhinagar (MIR Lab). Mid-semester project for the Integrated Waste Management and Circular Economy course.

**Hard constraint:** the instructor prohibits AI-generated text and slides (zero-marks penalty). Claude's role: planning, methods, data, literature, analysis, code, figures. All slide and report text is written by the student.

## Scope (fixed)
| Component | Specification |
|---|---|
| Sites | 15 dumpsites in 10 cities (SUR-03 dropped): 5 most populous (Ahmedabad, Surat, Vadodara, Rajkot, Bhavnagar) + Bhuj, Mehsana, Jamnagar, Vapi (spread) + Gandhinagar (capital). Junagadh dropped. |
| Area & perimeter | Epochs 2016, 2018, 2020, 2022, 2024, 2026 |
| Height & volume | 2 epochs: TanDEM-X EDEM (2011-13) or Copernicus GLO-30 baseline vs TanDEM-X DEM Change Map (one date per tile, 2016-22). All 12 sites run 25 Sep (Khajod + Vadodara excluded); DCM change only where the DLR tile is present (N21E072 so far) |
| Emissions | DROPPED (student decision 24 Sep: no fires, no methane) |
| Output | Insights for a presentation (student writes slides) |
| Dropped | US comparison site (Apex) - no US site |

## Site list (site_inventory_v3.csv)
| ID | City | KML name | Notes |
|---|---|---|---|
| AHM-01 | Ahmedabad | LF-1 (Pirana) | Opened 1982; biomining since ~2019-20 |
| AHM-02A / AHM-02B | Ahmedabad | LF-2(a) / LF-2(b) | LF-2 split into two parts ~300 m apart; LF-2(b) remediated by 2026 (area 0) |
| AHM-03 | Ahmedabad | LF-3 | New site (old "suspected" LF-3 removed) |
| SUR-01 | Surat | LF-1 (Bhatar old garbage dumping site) | |
| ~~SUR-03~~ | Surat | LF-3 | DROPPED 25 Sep (not in KML) |
| SUR-02 | Surat | LF-2 (Khajod) | Closure date unclear (2020 vs still used 2023) |
| VAD-01 | Vadodara | LF-1 | Near Jambuva sanitary landfill |
| VAD-02 | Vadodara | LF-2 (Atladara) | Reported cleared |
| RAJ-01 | Rajkot | LF-1 (Nakrawadi?) | Reported remediated to urban forest, BUT traced area grows 7.3 -> 28.1 ha - OPEN QUESTION to student |
| BHV-01 | Bhavnagar | LF-1 | Kumbharwada/Kharapat; fires 2026 |
| GNR-01 | Gandhinagar | LF-1 | |
| JAM-01 | Jamnagar | LF-1 | Gulabnagar; fire May 2026. Jamnagar LF-2 (remediated) exists but is ignored for now |
| BHJ-01, MEH-01, VAP-01 | Bhuj, Mehsana, Vapi | LF-1 | |

## Method decisions
1. **Automated Sentinel-2 outlines tried and rejected** (GEE scripts v1-v3): outlines leaked into the city (v1, ~10x area), then filled the drawn envelope and did not shrink at known cleared sites (v3). Cause: cleared/biomined bare ground looks like waste at 10 m. Evidence: qa_v3_flags.csv. Worth one line in methods.
2. **Manual tracing in Google Earth Pro historical imagery** - the standard in the literature (Singhal & Goel 2021; Sharma et al. 2024; Chatterjee & Chattopadhyay 2026; Agrawal et al. 2026; Muto & Tonooka 2025). Rules in tracing_protocol.md.
3. Naming: `<City> LF-<n> - <year>` (LF number required for multi-site cities; `(a)/(b)` for Ahmedabad LF-2); year in the name = image year; a 2025 image is used as the 2024 epoch (Bhuj, Vapi, Ahmedabad LF-1/2(a)/3). `NONE` or `(remediated)` pin = no waste that year. Duplicate 'Rajkot LF - 2018': 2nd occurrence = 2016 (student decision).
6. Leachate pools: excluded from the waste area (water ponding on top of the mound stays in); optional separate layer `... LEACHATE`.
7. Biomining: count waste still present (undug mounds, excavated waste awaiting screening); exclude trommels/sheds, clearly separate output stockpiles (RDF, soil fines) and cleared ground; optional separate layer `... BIOMINING`.
4. Metrics in EPSG:32643 (UTM 43N); perimeter reported after 5 m simplification.
5. Screenshots with imagery date: all epochs for case sites (Pirana, Rajkot, Khajod, Atladara, Bhavnagar), first/last/jump epochs for others; saved as screenshots/<SITE>/SITEID_epoch_imagedate.png. KML is the single master file (Claude exports shapefiles/GeoJSON at the end); keep dated KML backups.

## Pilot validation (5 sites x 6 epochs: BHJ, BHV, JAM, MEH, VAP) - pilot/
| Check | Result |
|---|---|
| Completeness / valid geometry | 30/30, all valid - PASS |
| Perimeter vs tracing detail | 5 m simplification changes perimeter <=2.5% - PASS |
| Buffer uncertainty (+/-2 m) | 3-15% of area (Vapi highest) - use as error bars |
| Epoch-to-epoch consistency | 10/25 jumps >30%; all confirmed as real change by the student (log in pilot_validation_report.md) - PASS (explained) |
| Imagery agreement (Step 5) | PENDING - run pilot/gee_pilot_step5_imagery_check.js in GEE |
| Repeatability (Step 6) | PENDING - blind re-trace one epoch per pilot site, name e.g. `Bhuj LF - 2020 R` |

Thresholds (literature-based where possible): repeat-trace area difference <=10% for sites >=5 ha, <=20% for <5 ha (Paul et al. 2013, 2020 glacier outlines; small objects 8-44%); overlap (IoU) >=0.80 (0.5 is the usual minimum match); >30% epoch jump = flag to explain. No landfill-specific repeatability standard exists.

Pilot areas 2016 -> 2026 (ha): BHJ 5.0 -> 6.7; BHV 3.7 -> peak 19.7 (2020) -> 14.8; JAM 1.6 -> 2.8; MEH 2.6 -> 2.8 (parts cleared and built on, waste stacked); VAP 0.5 -> 1.4.

## Interim area/perimeter results (analysis/, run 25 Sep ~1 am)
12 sites in this run: AHM-01, 02A, 02B, 03, SUR-01, RAJ-01, BHV-01, GNR-01, JAM-01, BHJ-01, MEH-01, VAP-01. Not yet in: SUR-02 Khajod, VAD-01, VAD-02 (still to trace). Master KML = `Locations of landfills in gujurat (3).kml`.
Results page (live): https://claude.ai/artifact/9y1CEAM1F2QfdeAaA7heAZ ; copy: analysis/gujarat_dumpsite_footprints.html. Script: analysis/trend_analysis.py (re-run when new sites land).

| Site | 2016 ha | 2026 ha | Net | Largest (year) | Class |
|---|---|---|---|---|---|
| AHM-01 Pirana | 38.5 | 29.9 | -22% | 38.7 (2020) | Contracting |
| AHM-02A | 3.8 | 8.2 | +115% | 9.6 (2022) | Expanding |
| AHM-02B | 4.7 | 0 | -100% | 9.3 (2020) | Cleared |
| AHM-03 | 3.1 | 8.6 | +175% | 8.6 (2024) | Expanding |
| SUR-01 Bhatar | 2.0 | 0.4 | -79% | 2.0 (2016) | Contracting |
| RAJ-01 | 7.3 | 28.1 | +285% | 28.3 (2024) | Expanding |
| BHV-01 | 3.7 | 14.8 | +299% | 19.7 (2020) | Rise and fall |
| GNR-01 | 1.1 | 12.6 | +1033% | 12.6 (2026) | Expanding |
| JAM-01 | 1.6 | 2.8 | +80% | 2.9 (2020) | Expanding |
| BHJ-01 | 5.0 | 6.7 | +34% | 7.7 (2024) | Expanding |
| MEH-01 | 2.6 | 2.8 | +8% | 4.3 (2024) | Rise and fall |
| VAP-01 | 0.5 | 1.4 | +167% | 1.7 (2022) | Expanding |

Key numbers and inferences (analysis notes; slide wording is the student's):
1. Total footprint 73.8 -> 124.8 (2024) -> 116.2 ha (+58%); 2-yr changes +20, +26, +7, +4, -7% - growth slowed after 2020, reversed only 2024-26 (timing coincides with SBM-U 2.0, Oct 2021; not causal proof).
2. Two speeds: other cities 10.7 -> 26.2 ha (+144%, rising every epoch after 2018); major-city sites 63.0 -> 90.0 (+43%) but -11% since 2024 peak.
3. Growth concentrated: Rajkot, Gandhinagar, Bhavnagar = 75% of area gained (Rajkot 36%). Gandhinagar (capital) ~11x, mostly after 2020.
4. Remediation visible from space: Pirana flat 2016-20 then -22% (matches Muto & Tonooka 2025 volume stall since 2019); AHM-02B cleared; Surat-Bhatar -79%. Mann-Kendall p<0.05 (exact, n=6): AHM-03, GNR, RAJ, SUR-01.
5. Ahmedabad displacement pattern: non-Pirana sites 11.6 -> 25.0 ha (2024) while Pirana shrank; Ahmedabad total 50.0 -> 59.4 (2022) -> 46.6 ha (-7%).
6. Land churn: 57.2 ha that held waste is not under waste in 2026 (Pirana 17.5, BHV 13.2, AHM-02B 9.4) vs 70.6 ha newly covered.
7. Shape: less compact - GNR 0.80 -> 0.17, MEH 0.73 -> 0.15, BHV 0.44 -> 0.23; more compact - RAJ 0.33 -> 0.43, BHJ 0.15 -> 0.24.
Caveats: interim (Khajod/Vadodara missing); Rajkot unresolved; area is not volume (MEH area down while stacked higher); 6 epochs, single analyst, +/-3-11% edge uncertainty.
Suggested use: inference 2 = headline; 4 and 5 = case studies; 6 = circular-economy slide.

## Volume and height (VOlume and height/, v2 run 25 Sep ~2:30 am, 12 sites)
Script volume_height.py v2: reads `Locations of landfills in gujurat (3).kml` (same rules as trend_analysis.py; excludes Khajod + Vadodara), finds the GLO-30 clip and DLR tile for each site, and writes outputs/<SITE>/ plus all_sites_volume_by_dem.csv, all_sites_volume_change.csv and all_sites_volume_summary.png. Method: footprint = union of outlines; base = plane fitted to a ring 30-150 m outside the footprint with other sites removed; quality flag good/fair/poor/below ground/small.
2011-15 volume above surrounding ground (m3): AHM-01 3.95M +/-27k (good, peak 32 m); BHJ 472k +/-92k (fair); JAM 24k (fair); BHV 66.6k (good). Poor base (terrain/urban), do not use: GNR 1.6M +/-629k (Sabarmati valley slope), RAJ 364k +/-164k, VAP, SUR-01, AHM-02B, MEH. Below ground: AHM-03 -388k (walled cell dug ~4-5 m) and AHM-02A -85k.
Most sites got their waste after 2015, so the 2011-15 volume describes the ground, not the waste. The DCM change is the waste-added number.
DCM change: BHV-01 +121,500 +/-11,100 m3 (20 Jun 2019, robust); SUR-01 +25,600 +/-10,100 (13 Mar 2019, weak, urban noise, small site).
Pirana check: 3.95M m3 vs reported 12.6 Mt implies an impossible ~3.2 t/m3, so the DEM volume is a lower bound (30 m DSM smooths peaks; below-ground waste not counted; 47 vs 84 ha footprint) or the tonnage is inflated. Good point for discussion.
NEEDED from student: DCM LAST zips for N22E072 (Ahmedabad x4), N22E070 (RAJ, JAM), N23E072 (GNR, MEH), N23E069 (BHJ), N20E072 (VAP) into dem/. Then re-run `python volume_height.py` (no code changes).
Caveats: sites <3 ha unreliable; ring base fails in valleys/urban areas (the DCM change avoids this); DSMs include structures; volumes are lower bounds; DCM dates do not match area epochs; radar penetration. Density 0.8-1.2 t/m3 (Zekkos et al. 2006) to verify. BHV raised features south of site still to check.

## Analysis plan (analysis_plan.md)
Per site: net change and %, peak and peak year, change from peak, Theil-Sen rate (ha/yr), Mann-Kendall (descriptive only, n=6; no forecasting), land newly covered vs reclaimed (overlaps), shape index / compactness / fractal dimension / elongation / number of parts, uncertainty bands. Trajectory classes: expanding, rise-and-fall, contracting-remediated, stable, emerging, fluctuating. Figures: class-coloured study map; small-multiple area charts with events (SBM-U 2.0 Oct 2021, NGT orders, biomining, closures); trajectory quadrant plot; gain/loss maps for case sites; master table.
Hypothesis to test (not a finding): big-city sites show remediation while smaller-city dumps keep growing.

## Presentation (presentation_storyline_plan.md)
18-slide storyline in 5 parts: why it matters -> gap and questions -> how -> what changed -> what it means. Slides 1-8 and limitations can be written before results.

## Status and next steps
| When | Student | Claude |
|---|---|---|
| Thu night (done) | Traced 7 more sites (12 of 15 now); started screenshots | Interim trend analysis + results page |
| Fri | Trace Khajod + Vadodara x2; answer Rajkot question; download 5 DCM tiles; Step 5 + Step 6 if time; write slides from afternoon | Re-run trends with all 15; volume change once tiles land (done for 12 sites on GLO-30); figures |
| Sat by noon | Final review, submit before 2 pm | Fixes |
Fall-back order if behind: volume for small sites dropped first; area/perimeter is the core. (Fires and methane already dropped.)

DLR EOC Geoservice: access working (EDEM + DCM tiles downloaded for N21E072).

Open questions for the student: (1) Rajkot - is the traced area the active cell next to the remediated forest? (2) Vapi 2022 southern strip recorded as waste. (3) BHV raised features south of site (volume pilot).

## Files in this folder
| File | Contents |
|---|---|
| context.md | This file |
| Locations of landfills in gujurat (3).kml | MASTER: points + outlines for 12 sites (25 Sep) |
| Locations of landfills in gujurat (2).kml | Pilot version (5 sites) |
| Locations of landfills in gujurat.kml | Earlier points-only version |
| site_inventory_v3.csv | Site list (still lists SUR-03, now dropped) (v1, v2 superseded) |
| tracing_protocol.md | Locked tracing rules for the remaining sites |
| pilot/ | Pilot validation: metrics, figures, report, Step 5 GEE script |
| analysis/ | Interim trend analysis: trend_analysis.py, site_summary.csv, site_epoch_metrics.csv, transitions.csv, group_totals.csv, outlines.geojson, results.json, gujarat_dumpsite_footprints.html |
| VOlume and height/ | Volume/height, all 12 sites: volume_height.py (v2), README_volume.md, dem/ (DLR tiles + glo30/ per-site clips), outputs/<SITE>/ + all_sites_* (outputs/BHV-01_* at top level = old pilot) |
| photos/ | Dated Google Earth screenshots (Ahmedabad started) |
| analysis_plan.md | Trend metrics, figures, literature on presentation |
| presentation_storyline_plan.md | Slide-by-slide storyline (planning only) |
| kml_to_metrics.py | Area/perimeter from KML (SITEID_YEAR naming version; pilot script handles city-name naming) |
| gee_export_for_qgis.js | Export Sentinel-2 composites (sites/cities) as GeoTIFF for QGIS |
| gee_area_perimeter_v1-v3.js, dumpsite_*_v3*, qa_v3_flags.csv | Rejected automated method and its QA (keep for methods) |
| dumpsite_tracker.html | Offline copy of the tracker (live version saves changes: https://claude.ai/artifact/LQHHTKGqxvyRBfwkDunVRj) |
| old/ | Superseded files from before the 22 Sep restart |

## Working style
Short, direct answers. Explain steps before executing when asked. Save everything in this folder.
