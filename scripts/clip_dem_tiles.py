"""
Clip downloaded DEM tiles (TanDEM-X DCM / EDEM zips or GeoTIFFs) to a small window around each site,
so the clips are small enough to push to GitHub.
Usage:  python clip_dem_tiles.py <folder with the downloaded zips/tifs>
Output: dem_clips/<SITE>/<original tif name>.tif  (every raster inside every zip that overlaps the site)
Window: bounding box of all outlines of the site (all epochs) + 1.5 km on each side.
Needs: rasterio, shapely (same environment as volume_height.py).
"""
import sys, os, json, zipfile, glob
import rasterio
from rasterio.windows import from_bounds
from shapely.geometry import shape
from shapely.ops import unary_union

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, 'dem')
OUT = os.path.join(BASE, 'dem_clips')
PAD_DEG = 1.5 / 111.0

g = json.load(open(os.path.join(BASE, 'data', 'outlines_by_site_epoch.geojson')))
geoms = {}
for f in g['features']:
    geoms.setdefault(f['properties']['site_id'], []).append(shape(f['geometry']))
boxes = {s: unary_union(v).bounds for s, v in geoms.items()}

rasters = []
for p in glob.glob(os.path.join(SRC, '**', '*'), recursive=True):
    low = p.lower()
    if low.endswith('.zip'):
        with zipfile.ZipFile(p) as z:
            rasters += ['/vsizip/' + p + '/' + n for n in z.namelist() if n.lower().endswith(('.tif', '.tiff'))]
    elif low.endswith(('.tif', '.tiff')):
        rasters.append(p)
print(f'{len(rasters)} rasters found in {SRC}')

n = 0
for r in rasters:
    with rasterio.open(r) as src:
        if src.crs is None or src.crs.to_epsg() != 4326:
            print('SKIP (not EPSG:4326):', r); continue
        L, B, R, T = src.bounds
        for sid, (x0, y0, x1, y1) in boxes.items():
            x0, y0, x1, y1 = x0 - PAD_DEG, y0 - PAD_DEG, x1 + PAD_DEG, y1 + PAD_DEG
            if x1 < L or x0 > R or y1 < B or y0 > T:
                continue
            win = from_bounds(max(x0, L), max(y0, B), min(x1, R), min(y1, T), src.transform).round_offsets().round_lengths()
            data = src.read(window=win)
            prof = src.profile.copy()
            prof.update(height=data.shape[1], width=data.shape[2], transform=src.window_transform(win),
                        compress='deflate', tiled=False)
            prof.pop('blockxsize', None); prof.pop('blockysize', None)
            os.makedirs(os.path.join(OUT, sid), exist_ok=True)
            dst = os.path.join(OUT, sid, os.path.basename(r))
            with rasterio.open(dst, 'w', **prof) as d:
                d.write(data)
            n += 1
            print(f'{sid}: {os.path.basename(r)} {data.shape[2]}x{data.shape[1]} px')
print(f'{n} clips written to {OUT}')
