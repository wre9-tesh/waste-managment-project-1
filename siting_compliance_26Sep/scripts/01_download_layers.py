"""
Step 01 - download every feature layer needed for the siting check, per site.

Writes (all under data/):
  site_outlines.geojson                  2016 and 2026 outlines + all-epoch union per site (WGS84)
  raw/osm/<SITE>_local.json              OpenStreetMap features within 2.5 km (Overpass API): rivers, water bodies,
                                         roads, parks, residential and industrial land use, wetlands, coastline, tidal features, wells
  raw/osm/<SITE>_nonres.json             non-residential zones within 800 m (plants, works, industrial / commercial land)
  raw/osm/gujarat_protected.json         protected areas (sanctuaries, national parks, reserves) in Gujarat + margin
  raw/osm/gujarat_aerodromes.json        aerodromes / airfields in Gujarat + margin
  raw/ourairports_IN.csv                 OurAirports list for India (cross-check of the OSM aerodromes)
  raw/buildings/<SITE>.parquet           Overture Maps building footprints within 600 m (Google + Microsoft + OSM)
  raw/ghsl/<SITE>_ghsl_fun_2018.tif      GHSL residential / non-residential built-up map (2018, 10 m), clipped per site
  raw/jrc_flood/*_gujarat.tif            JRC / Copernicus global river flood hazard map, 100-year return period, and the
                                         JRC permanent-water layer, both clipped to Gujarat
  sources.json                           what was downloaded, from where, when, and data versions

Re-running skips files that already exist (delete a file to download it again).
"""
import json, os, time, datetime
import requests
import config as C
import outlines as O
from shapely.geometry import mapping
from shapely.ops import transform

os.makedirs(os.path.join(C.RAW, "osm"), exist_ok=True)
os.makedirs(os.path.join(C.RAW, "buildings"), exist_ok=True)
os.makedirs(os.path.join(C.RAW, "jrc_flood"), exist_ok=True)
SRC_FILE = os.path.join(C.DATA, "sources.json")
sources = json.load(open(SRC_FILE)) if os.path.exists(SRC_FILE) else {}
now = lambda: datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def bbox_wgs(geom_utm, radius):
    """(south, west, north, east) of the outline buffered by radius metres."""
    b = transform(O.inv, geom_utm.buffer(radius)).bounds   # minx, miny, maxx, maxy
    return (b[1], b[0], b[3], b[2])


def overpass(query, out_file):
    if os.path.exists(out_file):
        return json.load(open(out_file))
    last = None
    for attempt in range(4):
        for url in C.OVERPASS_URLS:
            try:
                r = requests.post(url, data={"data": query}, timeout=300)
                if r.status_code == 200 and r.text.strip().startswith("{"):
                    js = r.json()
                    if js.get("remark"):          # 'runtime error ... timed out' = incomplete answer -> retry
                        last = f"{url}: {js['remark'][:200]}"
                        continue
                    js["_query"] = query; js["_endpoint"] = url; js["_downloaded"] = now()
                    json.dump(js, open(out_file, "w"))
                    return js
                last = f"{url}: HTTP {r.status_code} {r.text[:200]}"
            except Exception as e:  # network hiccup -> try the other endpoint
                last = f"{url}: {e}"
        time.sleep(20 * (attempt + 1))
    raise RuntimeError(f"Overpass failed for {out_file}: {last}")


def q_local(bb):
    s = "{},{},{},{}".format(*bb)
    return f"""[out:json][timeout:240];
(
  way["waterway"~"^(river|riverbank|stream|canal|drain|tidal_channel)$"]({s});
  relation["waterway"~"^(river|riverbank)$"]({s});
  way["natural"="water"]({s});  relation["natural"="water"]({s});
  way["landuse"~"^(reservoir|basin)$"]({s});  relation["landuse"~"^(reservoir|basin)$"]({s});
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary)(_link)?$"]({s});
  way["leisure"~"^(park|recreation_ground|garden)$"]({s});  relation["leisure"~"^(park|recreation_ground)$"]({s});
  way["landuse"~"^(residential|landfill|industrial)$"]({s});  relation["landuse"~"^(residential|landfill|industrial)$"]({s});
  node["place"~"^(city|town|village|hamlet|suburb|neighbourhood|isolated_dwelling)$"]({s});
  way["natural"~"^(wetland|coastline|mud|bay)$"]({s});  relation["natural"~"^(wetland|bay)$"]({s});
  way["tidal"="yes"]({s});  relation["tidal"="yes"]({s});
  way["wetland"]({s});  relation["wetland"]({s});
  node["man_made"~"^(water_well|water_works|water_tower)$"]({s});  way["man_made"~"^(water_well|water_works)$"]({s});
);
out geom tags;"""


def q_nonres(bb):
    """Non-residential zones used to screen building footprints (R4): plants, works, industrial/commercial land."""
    s = "{},{},{},{}".format(*bb)
    return f"""[out:json][timeout:240];
(
  way["landuse"~"^(industrial|commercial|retail|railway|quarry|construction|brownfield|landfill|depot|garages)$"]({s});
  relation["landuse"~"^(industrial|commercial|retail|railway|quarry|construction|brownfield|landfill|depot)$"]({s});
  way["man_made"~"^(wastewater_plant|water_works|works|storage_tank|silo)$"]({s});
  relation["man_made"~"^(wastewater_plant|water_works|works)$"]({s});
  way["power"~"^(plant|substation|generator)$"]({s});  relation["power"~"^(plant|substation)$"]({s});
  way["amenity"~"^(waste_transfer_station|recycling|fuel|bus_station)$"]({s});
);
out geom tags;"""


def q_protected(bb):
    s = "{},{},{},{}".format(*bb)
    return f"""[out:json][timeout:240];
(
  way["boundary"~"^(protected_area|national_park)$"]({s});  relation["boundary"~"^(protected_area|national_park)$"]({s});
  way["leisure"="nature_reserve"]({s});  relation["leisure"="nature_reserve"]({s});
);
out geom tags;"""


def q_aero(bb):
    s = "{},{},{},{}".format(*bb)
    return f"""[out:json][timeout:240];
(
  nwr["aeroway"="aerodrome"]({s});
  nwr["military"~"^(airfield|base)$"]["aeroway"]({s});
);
out geom tags;"""


# ------------------------------------------------------------------ outlines
by_epoch, log = O.read_outlines(C.KML)
union = O.footprints(by_epoch)
SITES = sorted(union)
feats = []
for s in SITES:
    for ep in (C.COMPARE_EPOCH, C.MAIN_EPOCH):
        g = by_epoch.get((s, ep))
        if g is not None:
            feats.append(dict(type="Feature", properties=dict(site=s, name=O.NAMES[s], layer=f"outline_{ep}",
                                                              area_ha=round(g.area / 1e4, 2)),
                              geometry=mapping(transform(O.inv, g))))
    feats.append(dict(type="Feature", properties=dict(site=s, name=O.NAMES[s], layer="union_2016_2026",
                                                      area_ha=round(union[s].area / 1e4, 2)),
                      geometry=mapping(transform(O.inv, union[s]))))
json.dump(dict(type="FeatureCollection", features=feats), open(os.path.join(C.DATA, "site_outlines.geojson"), "w"))
print(f"outlines: {len(SITES)} sites written to data/site_outlines.geojson")

# ------------------------------------------------------------------ OpenStreetMap (Overpass)
# local features: one query per site (run 4 at a time); protected areas and aerodromes: one query for all of Gujarat
from concurrent.futures import ThreadPoolExecutor

def fetch_local(s):
    js = overpass(q_local(bbox_wgs(union[s], C.LOCAL_RADIUS)), os.path.join(C.RAW, "osm", f"{s}_local.json"))
    overpass(q_nonres(bbox_wgs(union[s], C.BUILDING_RADIUS + 200)), os.path.join(C.RAW, "osm", f"{s}_nonres.json"))
    return s, len(js["elements"]), js.get("osm3s", {}).get("timestamp_osm_base", "?")

with ThreadPoolExecutor(max_workers=4) as ex:
    for s, n, ts in ex.map(fetch_local, SITES):
        print(f"{s}: {n} OSM features within {C.LOCAL_RADIUS/1000:.1f} km (OSM data as of {ts})")
        sources.setdefault("osm_local", {})[s] = ts
jp = overpass(q_protected(C.GUJARAT_BBOX), os.path.join(C.RAW, "osm", "gujarat_protected.json"))
ja = overpass(q_aero(C.GUJARAT_BBOX), os.path.join(C.RAW, "osm", "gujarat_aerodromes.json"))
print(f"Gujarat: {len(jp['elements'])} protected-area features, {len(ja['elements'])} aerodromes")
sources["osm_gujarat"] = dict(bbox=C.GUJARAT_BBOX, protected=jp.get("osm3s", {}).get("timestamp_osm_base", "?"),
                              aerodromes=ja.get("osm3s", {}).get("timestamp_osm_base", "?"))

# ------------------------------------------------------------------ OurAirports (cross-check list)
ap_file = os.path.join(C.RAW, "ourairports_IN.csv")
if not os.path.exists(ap_file):
    r = requests.get(C.OURAIRPORTS_URL, timeout=300); r.raise_for_status()
    lines = r.text.splitlines()
    keep = [lines[0]] + [l for l in lines[1:] if ',"IN",' in l]
    open(ap_file, "w", encoding="utf-8").write("\n".join(keep))
    sources["ourairports"] = dict(url=C.OURAIRPORTS_URL, downloaded=now())
sources.setdefault("ourairports", dict(url=C.OURAIRPORTS_URL, downloaded="(file already present)"))
print("OurAirports India list:", ap_file)

# ------------------------------------------------------------------ JRC flood hazard map, 100-year return period
# The two global tiles covering the sites (ID178_N30_E60, ID184_N30_E70; see tile_extents.geojson) are downloaded and
# each is cut to GUJARAT_BBOX on its own native grid (a window read: no resampling); only the clips are kept.
import rasterio
from rasterio.windows import from_bounds as win_from_bounds
JRC_BASE = "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/CEMS-GLOFAS/flood_hazard/"
jdir = os.path.join(C.RAW, "jrc_flood")
for sub, suffix in (("RP100", "_RP100_depth.tif"), ("Permanent_WaterBodies", "_permanent_water.tif")):
    for tile in ("ID178_N30_E60", "ID184_N30_E70"):
        clip = os.path.join(jdir, tile + suffix.replace(".tif", "_gujarat.tif"))
        if os.path.exists(clip):
            continue
        f = os.path.join(jdir, tile + suffix)
        if not os.path.exists(f):
            r = requests.get(JRC_BASE + f"{sub}/{tile}{suffix}", timeout=900); r.raise_for_status()
            open(f, "wb").write(r.content)
        with rasterio.open(f) as src:
            s_, w_, n_, e_ = C.GUJARAT_BBOX
            bb = src.bounds
            win = win_from_bounds(max(w_, bb.left), max(s_, bb.bottom), min(e_, bb.right), min(n_, bb.top), src.transform)
            win = win.round_offsets().round_lengths()
            arr = src.read(window=win)
            prof = src.profile.copy()
            prof.update(height=arr.shape[1], width=arr.shape[2], transform=src.window_transform(win), compress="deflate",
                        tiled=True, blockxsize=256, blockysize=256)
        with rasterio.open(clip, "w", **prof) as w:
            w.write(arr)
        os.remove(f)                     # keep only the clip
        print(f"  JRC {sub} {tile}: clipped to Gujarat {arr.shape[1:]}")
for extra in ("README.txt", "CHANGELOG.txt", "copyright.txt", "tile_extents.geojson"):
    f = os.path.join(jdir, extra)
    if not os.path.exists(f):
        open(f, "wb").write(requests.get(JRC_BASE + extra, timeout=300).content)
sources["jrc_flood"] = dict(url=JRC_BASE, version="2.1.2 (README of 12 Jan 2026)", return_period=100,
                            resolution="3 arc-seconds (~90 m)", downloaded=sources.get("jrc_flood", {}).get("downloaded", now()))
print("JRC flood tiles ready")

# ------------------------------------------------------------------ GHSL residential / non-residential built-up (2018, 10 m)
# GHS-BUILT-C FUN R2023A: 0 = not built, 1 = residential, 2 = non-residential (JRC GHSL Data Package 2023). The global
# GeoTIFF is read window by window over HTTP (no 44 GB download).
import rasterio
from rasterio.windows import from_bounds
from pyproj import Transformer
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.makedirs(os.path.join(C.RAW, "ghsl"), exist_ok=True)
to_moll = Transformer.from_crs(32643, "ESRI:54009", always_xy=True).transform
with rasterio.open("/vsicurl/" + C.GHSL_FUN_URL) as r:
    for s in SITES:
        f = os.path.join(C.RAW, "ghsl", f"{s}_ghsl_fun_2018.tif")
        if os.path.exists(f):
            continue
        b = transform(to_moll, union[s].buffer(C.BUILDING_RADIUS + 200)).bounds
        win = from_bounds(*b, r.transform).round_offsets().round_lengths()
        a = r.read(1, window=win)
        prof = dict(driver="GTiff", height=a.shape[0], width=a.shape[1], count=1, dtype="uint8", crs=r.crs,
                    transform=r.window_transform(win), nodata=255, compress="lzw")
        with rasterio.open(f, "w", **prof) as w:
            w.write(a, 1)
        print(f"  {s}: GHSL clip {a.shape}, residential cells {(a == 1).sum()}, non-residential {(a == 2).sum()}")
sources["ghsl_fun"] = dict(url=C.GHSL_FUN_URL, product="GHS-BUILT-C FUN E2018 R2023A, 10 m, Mollweide",
                           classes="0 not built, 1 residential, 2 non-residential")

# ------------------------------------------------------------------ Overture Maps buildings (DuckDB, anonymous S3)
import duckdb
for k in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
    os.environ.pop(k, None)            # the bucket is public: never send credentials
con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs; SET s3_region='us-west-2'; "
            "SET s3_access_key_id=''; SET s3_secret_access_key=''; SET s3_session_token='';")
rel = C.OVERTURE_RELEASE
if rel is None:
    txt = requests.get("https://overturemaps-us-west-2.s3.amazonaws.com/?list-type=2&prefix=release/&delimiter=/",
                       timeout=60).text
    import re
    rels = sorted(re.findall(r"<Prefix>release/(\d{4}-\d{2}-\d{2}\.\d+)/</Prefix>", txt))
    rel = rels[-1]
con.execute("SET enable_http_metadata_cache=true; SET parquet_metadata_cache=true; SET memory_limit='3GB';")  # footers read once
path = C.OVERTURE_BUCKET.format(rel=rel)
for s in SITES:
    f = os.path.join(C.RAW, "buildings", f"{s}.parquet")
    if os.path.exists(f):
        continue
    b = bbox_wgs(union[s], C.BUILDING_RADIUS)          # one AND-ed bbox per query so row groups can be skipped
    t0 = time.time()
    df = con.execute(f"""SELECT id, sources[1].dataset AS source, subtype, class, height, num_floors,
                                bbox.xmin AS xmin, bbox.ymin AS ymin, bbox.xmax AS xmax, bbox.ymax AS ymax, geometry
                         FROM read_parquet('{path}', hive_partitioning=1)
                         WHERE bbox.xmin > {b[1]} AND bbox.xmax < {b[3]} AND bbox.ymin > {b[0]} AND bbox.ymax < {b[2]}""").df()
    df.to_parquet(f, index=False)
    print(f"  {s}: {len(df)} Overture buildings within {C.BUILDING_RADIUS:.0f} m ({time.time() - t0:.0f} s)", flush=True)
sources["overture_buildings"] = dict(release=rel, bucket=C.OVERTURE_BUCKET.format(rel=rel),
                                     radius_m=C.BUILDING_RADIUS,
                                     downloaded=sources.get("overture_buildings", {}).get("downloaded", now()))
json.dump(sources, open(SRC_FILE, "w"), indent=1)
print("done - sources written to data/sources.json")
