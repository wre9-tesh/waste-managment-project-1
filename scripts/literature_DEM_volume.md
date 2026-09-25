# How DEMs are used to measure dumpsite height and volume: literature notes (25 Sep 2026)

Notes for planning the method. These are not slide text.

## 1. Muto & Tonooka (2025), *Sensors* 25(10): 3173
"Monitoring Long-Term Waste Volume Changes in Landfills in Developing Countries Using ASTER Time-Series Digital Surface Model Data". https://doi.org/10.3390/s25103173
- **Study area:** 15 landfills in 6 countries. **9 in India:**
  - Delhi: Ghazipur, Bhalswa, Okhla
  - Mumbai: Deonar, Mulund
  - Kolkata: Dhapa (active and closed parts)
  - Chennai: Kodungaiyur
  - Ahmedabad: **Pirana**

  The rest are in Jordan, Algeria, Egypt, Kyrgyzstan and Pakistan.
- **Data:** ASTER time-series DSMs from the MADAS archive (30 m; 2000-2024; 6-37 scenes per site). The TanDEM-X DEM Change Map (DCM, 2016-22) is used as a comparison at 6 sites.
- **Method:**
  - Boundaries are digitised by hand in Google Earth Pro, leaving out buildings.
  - Base elevation = the mean DSM value of the pixels two pixels outside the boundary, applied as one flat level to every pixel inside the site.
  - Relative volume = (target DSM − reference DSM) summed over the site × 900 m².
  - Horizontal alignment is corrected with a shift when it is off by more than 2 pixels.
  - Height bias is removed using the median offset over at least 5 stable 3×3-pixel reference areas several km away.
  - Cloudy or outlier scenes are removed by eye.
  - A quadratic trend is fitted to the time series.
- **Validation:** against reported tonnage, against assumed initial topography, and against the DCM.
- **Result for Pirana:** volume stalled from 2019, which matches the 2020 start of biomining.

## 2. Louw & Avtar (2025), *Resources, Conservation & Recycling* 212: 107924
"Methodology for measuring landfill dumping statistics globally using Digital Elevation Change maps". https://doi.org/10.1016/j.resconrec.2024.107924. Code: https://github.com/StephanLo/dcm_waste_study
- **Study area:** 100 landfills on 5 continents, taken from OpenStreetMap and chosen by population density. 76% had usable data (mostly 2018-2020).
- **Data:** TanDEM-X 30 m DCM, both the **FIRST** and **LAST** layers, with their DATE, CIM and HAI auxiliary layers.
- **Method (from their public code, 4_DCM_to_volume.R and 5_compile_statistics.R):**
  - Site polygon = OSM landfill polygon plus a 50 m buffer.
  - Change per pixel = DCM_LAST − DCM_FIRST (both are measured against the EDEM, so the EDEM cancels out), divided by the days between the two acquisition dates, giving a rate in m/day.
  - Pixels with less than 2 days between acquisitions are masked out.
  - The error per pixel is the two HAI values combined in quadrature. Pixels whose change is smaller than this error are filtered out.
  - Volume rate = sum of (rate × pixel area) inside the polygon, in m³/day. Site error = pixel errors combined in quadrature.
- **Validation:** against officially reported waste statistics. Median error was about 14.7 m³/day, and accuracy fell when the time between acquisitions was short.
- **Relevance:** this is the published method for exactly our DCM data. It uses FIRST→LAST, not EDEM→LAST. It needs no base surface.

## 3. Agrawal, Rakkasagi & Goyal (2025), *Scientific Reports*
"High-resolution landfill characterization using SAR remote sensing and cloud-based processing". https://www.nature.com/articles/s41598-025-32908-9
- **Study area:** 80 Indian landfills (a 2025 snapshot). Validation at Gondiya and at Ujjain (Ring Road trenching ground).
- **Data:** Sentinel-1 SLC pairs (January 2025), processed with InSAR in SNAP to a DEM of about 10 m. Boundaries are hand-drawn on Google Earth 2025 imagery.
- **Method:**
  - Height H = the average over n (from 10 to N/2) of [mean of the n highest pixels − mean of the n lowest pixels].
  - For small sites (≤75 pixels), outliers more than ±5 m from the mode are replaced.
  - Volume V = H × A.
- **Validation:** against DGPS, drone and total-station surveys. Volume error was 20.2% at Gondiya and 0.8% at Ujjain.
- **Note:** V = H × A treats the dump as a box, so it overestimates a mound. There is only one date. Its Appendix B lists every site; check it for Gujarat values.

## 4. Chakraborty, Basudhar, Sikdar & Roy Choudhury (2024), *Down To Earth*, 1-15 Oct 2024 (grey literature)
- **Study area:** Delhi: Bhalswa, Ghazipur and Okhla, 2013-2024.
- **Data:** SRTM DEM (called "2013"; SRTM itself was acquired in Feb 2000) against a 2024 Cartosat DEM. Landsat 5/9 for extent, with land surface temperature as a check.
- **Method:** difference between the two DEMs over the dump extent, converted to tonnes. The base surface and density are not described.
- **Results:** for example, Ghazipur about 1.1 Mt (2013) to 3.34 Mt (2024).
- **Relevance:** an Indian example of using an old DEM as the "before" surface.

## 5. Esposito, Matano & Sacchi (2018), *Geosciences* 8(9): 348
"Detection and Geometrical Characterization of a Buried Landfill Site by Integrating Land Use Historical Analysis, Digital Photogrammetry and Airborne Lidar Data".
- **Study area:** Monte di Procida, Campi Flegrei coast, Naples, Italy.
- **Data:** DEMs made from 1956 and 1974 aerial stereo photos, plus a 2008 airborne LiDAR survey (±0.18 m), plus historical maps.
- **Method:**
  - The pre-landfill ground comes from the 1956 photogrammetric DEM, and the later surface from LiDAR.
  - Volume is the DEM of Difference (Geomorphic Change Detection software), keeping only changes above a minimum level of detection (minLoD ±0.83 m and ±0.93 m).
- **Results:** 14,350 m², about 8 m average thickness, about 100,000 m³.
- **Relevance:** it uses a real pre-dump DEM instead of an interpolated base, and a noise threshold (minLoD).

## 6. Mello, Salim & Simões (2022), *Waste Management* 137: 253-263
"UAV-based landfill operation monitoring: A year of volume and topographic measurements".
- **Study area:** a 12 ha active sanitary landfill in Minas Gerais, Brazil.
- **Data:** a low-cost multirotor UAV with an RGB camera, flown monthly for a year. Two ground-control-point layouts were tested.
- **Method:** Structure-from-Motion DEMs, with monthly volume from differencing successive surveys. Checked against total-station surveys.
- **Results:** 9% volume difference with control points on the perimeter only, 4% with control points on the working faces.

## 7. Son, Kim, Sung & Yu (2020), *Remote Sensing* 12(10): 1615
"Integrating UAV and TLS Approaches for Environmental Management: A Case Study of a Waste Stockpile Area".
- **Study area:** a waste disposal site at Jipyeon-ri, Sejong City, South Korea (about 6,000 m², about 20 m high).
- **Data:** a terrestrial laser scanner (20 stations), UAV photogrammetry (8 flight scenarios) and 311 GNSS ground points.
- **Method:** volume above a reference base surface computed cell by cell, comparing laser scanner, UAV and a fusion of both.
- **Results:** about 41,200-41,500 m³. RMSE was 0.20 m for the laser scanner, 0.03 m for the UAV and 0.03 m for the fusion.

## 8. Dhakal, Manandhar, Shah & Khanal (2025), *Remote Sensing* 17(18): 3136
"Integrating UAS Remote Sensing and Edge Detection for Accurate Coal Stockpile Volume Estimation".
- **Study area:** a coal storage yard near Cadiz, Ohio, USA (about 70,000 m²).
- **Data:** UAV LiDAR (Velodyne VLP-16) as the reference, plus UAV multispectral photogrammetry.
- **Method:** pile edges are found by edge detection. Where the ground under a pile is unknown, the base terrain is **kriging-interpolated from the surrounding ground**.
- **Results:** 2.06% error against LiDAR.
- **Relevance:** it supports interpolating a base surface (kriging) from the edge instead of fitting one plane.

## Where our current method sits
| Step | Ours now | Literature |
|---|---|---|
| Boundary | Hand-traced, Google Earth | Same (Muto & Tonooka; Agrawal) |
| Base surface | Plane from a 30-150 m ring (plus flat and IDW variants) | Flat ring mean (Muto & Tonooka); n-lowest pixels (Agrawal); kriging from the edge (Dhakal); real pre-dump DEM (Esposito; DTE Delhi) |
| Change | EDEM → DCM LAST, corrected by the ring median | DCM LAST − FIRST per day, HAI-filtered (Louw & Avtar); bias from stable far-away areas (Muto & Tonooka); minLoD (Esposito) |
| Validation | None yet | Reported tonnage (Muto & Tonooka; Louw & Avtar); field surveys (Agrawal) |

## Upgrades suggested by the literature
1. **DCM change as in Louw & Avtar:** use LAST − FIRST where the two dates differ, add the per-pixel HAI error filter, and report a rate in m³/day and m³/yr. Keep EDEM → DCM as the longer baseline.
2. **Bias correction as in Muto & Tonooka:** use ≥5 stable reference areas away from the site (open flat land, not the urban ring) instead of the ring median.
3. **Pre-dump DEM as the base (Esposito; DTE):** for sites that were empty in Feb 2000 (Gandhinagar, Rajkot, AHM-03 and others; to check against imagery), use SRTM 2000 as the "before" ground. Waste volume = later DEM − SRTM, with a minLoD threshold.
4. **Interpolated base (Dhakal):** kriging or IDW from the boundary ring where no pre-dump DEM exists, instead of a single plane.
5. **Height as in Agrawal:** also report the n-highest minus n-lowest height, so our numbers can be compared with that 80-site India dataset.
6. **Validation:** compare with Agrawal et al. Appendix B for the Gujarat sites, and with reported tonnages (with a density range).

Not read in full: the Louw & Avtar article text is paywalled (their public code was read instead); the PubMed page for Agrawal et al. was rate-limited (the Nature page was read); a 2025 *Geocarto* paper on curvature-aware earthwork volume returned an access error.
