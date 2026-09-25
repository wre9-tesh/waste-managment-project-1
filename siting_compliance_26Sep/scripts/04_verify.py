"""
Step 04 (check) - recompute key numbers of step 02 by an independent route and compare.
  a) nearest-feature distances recomputed in UTM 43N (the CRS of the area analysis) instead of the per-site
     azimuthal equidistant projection, then converted to a true geodesic length between the two nearest points;
  b) airport distances as geodesic distances (WGS84 ellipsoid) from every outline vertex to the airport reference point;
  c) residential-building counts within 200 m recomputed in UTM 43N.
Writes outputs/tables/verification.csv and prints the largest differences.
"""
import os, json
import numpy as np
import pandas as pd
from pyproj import Geod, Transformer
from shapely.geometry import shape
from shapely.ops import transform, nearest_points
import config as C
import outlines as O

geod = Geod(ellps="WGS84")
to_utm = Transformer.from_crs(4326, 32643, always_xy=True).transform
to_wgs = Transformer.from_crs(32643, 4326, always_xy=True).transform
by_epoch, _ = O.read_outlines(C.KML)
near = pd.read_csv(os.path.join(C.TABLES, "nearest_features_2026.csv")).set_index("site")
rows = []
for s in near.index:
    fc = json.load(open(os.path.join(C.SITES_OUT, s, f"{s}_layers.geojson")))
    out_wgs = transform(O.inv, by_epoch[(s, C.MAIN_EPOCH)])
    out_utm = transform(to_utm, out_wgs)
    for layer, col, scale in (("river", "river_m", 1), ("pond", "pond_m", 1), ("highway", "highway_m", 1),
                              ("park", "park_m", 1)):
        feats = [shape(f["geometry"]) for f in fc["features"] if f["properties"]["layer"] == layer]
        if layer == "pond":      # step 02 ignores water mostly inside the dump and < 100 m2
            feats = [g for g in feats if transform(to_utm, g).area >= C.MIN_POND_M2]
        if not feats or pd.isna(near.loc[s, col]):
            continue
        best = None
        for g in feats:
            gu = transform(to_utm, g)
            d = out_utm.distance(gu)
            if best is None or d < best[0]:
                best = (d, gu)
        p1, p2 = nearest_points(out_utm, best[1])
        (x1, y1), (x2, y2) = to_wgs(p1.x, p1.y), to_wgs(p2.x, p2.y)
        dg = geod.inv(x1, y1, x2, y2)[2] if best[0] > 0 else 0.0
        rows.append(dict(site=s, check=f"{layer} distance (m)", step02=near.loc[s, col], independent=round(dg, 1)))
    # airport: geodesic from outline vertices to the reference point
    arps = [shape(f["geometry"]) for f in fc["features"] if f["properties"]["layer"] == "airport_reference_point"]
    if arps:
        xs, ys = np.array(out_wgs.exterior.coords if out_wgs.geom_type == "Polygon" else
                          [c for g in out_wgs.geoms for c in g.exterior.coords]).T
        dmin = min(geod.inv(xs, ys, np.full_like(xs, a.x), np.full_like(ys, a.y))[2].min() for a in arps)
        rows.append(dict(site=s, check="airport reference point (km)", step02=near.loc[s, "airport_km"],
                         independent=round(dmin / 1000, 2)))
    # buildings within 200 m: count features of layer building with step-02 distance < 200 recomputed in UTM
    b = [shape(f["geometry"]) for f in fc["features"] if f["properties"]["layer"] == "building"
         and not f["properties"].get("in_industrial_zone") and f["properties"].get("ghsl_2018") == 1]
    n = sum(out_utm.distance(transform(to_utm, g)) < 200 for g in b)
    rows.append(dict(site=s, check="residential buildings within 200 m", step02=near.loc[s, "buildings_within_200m"], independent=n))
v = pd.DataFrame(rows)
v["difference"] = (v.independent - v.step02).round(2)
v["relative_%"] = (100 * v.difference / v.step02.replace(0, np.nan)).round(2)
v.to_csv(os.path.join(C.TABLES, "verification.csv"), index=False)
print(v.to_string(index=False))
print("\nmax |difference| per check:")
print(v.groupby("check").difference.apply(lambda x: x.abs().max()).to_string())
