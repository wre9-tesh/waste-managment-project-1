"""
Read the master KML into site outlines (UTM 43N).
The name-parsing rules are copied unchanged from waste-managment-project-1/scripts/final_analysis.py,
so the siting check uses exactly the polygons behind the final area/perimeter and volume results:
  - '<City> LF - <n> (<part>) <year>'  ->  site <CITY>-0<n>, part a / b / c / olddump / main
  - parts of one site are merged (AHM-02 = a+b, SUR-02 = a+b+c, VAD-02 = old dump + a + b)
  - a 2025 image is the 2024 epoch; Jamnagar LF-2 is not in the study; pins without polygons are skipped
"""
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from shapely.geometry import Polygon
from shapely.ops import transform, unary_union
from pyproj import Transformer
import config as C

CITY = {'ahmedabad': 'AHM', 'surat': 'SUR', 'vadodara': 'VAD', 'rajkot': 'RAJ', 'bhavnagar': 'BHV',
        'gandhinagar': 'GNR', 'jamnagar': 'JAM', 'bhuj': 'BHJ', 'mehsana': 'MEH', 'vapi': 'VAP'}
NAMES = {'AHM-01': 'Ahmedabad LF-1 (Pirana)', 'AHM-02': 'Ahmedabad LF-2', 'AHM-03': 'Ahmedabad LF-3',
         'SUR-01': 'Surat LF-1 (Bhatar)', 'SUR-02': 'Surat LF-2 (Khajod)', 'VAD-01': 'Vadodara LF-1',
         'VAD-02': 'Vadodara LF-2 (Atladara)', 'RAJ-01': 'Rajkot LF-1', 'BHV-01': 'Bhavnagar LF-1',
         'GNR-01': 'Gandhinagar LF-1', 'JAM-01': 'Jamnagar LF-1', 'BHJ-01': 'Bhuj LF-1',
         'MEH-01': 'Mehsana LF-1', 'VAP-01': 'Vapi LF-1'}
fwd = Transformer.from_crs(4326, 32643, always_xy=True).transform
inv = Transformer.from_crs(32643, 4326, always_xy=True).transform
loc = lambda t: t.split('}')[-1]


def parse(name):
    """Same function as final_analysis.py: returns city, LF number, part, image year, 'no waste' flag."""
    low = name.lower().replace('vadoara', 'vadodara')
    city = re.match(r'\s*([a-z]+)', low).group(1)
    m = re.search(r'lf\s*-?\s*(\d)(?!\d)\s*(?:\(\s*([a-z][a-z\s+]*)\s*\))?', low)
    lf = m.group(1) if m else '1'
    part = re.sub(r'\s+', '', m.group(2)) if (m and m.group(2)) else 'main'
    yr = re.search(r'(20\d\d)', low)
    flag = bool(re.search(r'remed|remid|\bnone\b', low))
    return city, lf, part, (int(yr.group(1)) if yr else None), flag


def read_outlines(kml=C.KML):
    """Returns (by_epoch, log). by_epoch[(site_id, epoch)] = merged UTM geometry of all parts of that epoch."""
    root = ET.parse(kml).getroot()
    parts = defaultdict(list); log = []
    for pm in root.iter():
        if loc(pm.tag) != 'Placemark':
            continue
        name = next((c.text or '' for c in pm if loc(c.tag) == 'name'), '').strip()
        city, lf, part, yr, flag = parse(name)
        if city not in CITY:
            continue
        if city == 'jamnagar' and lf == '2':
            continue
        polys = [e for e in pm.iter() if loc(e.tag) == 'Polygon']
        if not polys or yr is None:
            continue
        sid = f'{CITY[city]}-{int(lf):02d}'
        ep = C.EPOCH_MAP.get(yr, yr)
        for pg in polys:
            outer = next((e for e in pg.iter() if loc(e.tag) == 'outerBoundaryIs'), pg)
            coords = next(e for e in outer.iter() if loc(e.tag) == 'coordinates').text.split()
            g = transform(fwd, Polygon([tuple(map(float, c.split(',')[:2])) for c in coords]))
            parts[(sid, ep)].append(g if g.is_valid else g.buffer(0))
        log.append(f'{name} -> {sid} epoch {ep} part {part}')
    by_epoch = {k: unary_union(v) for k, v in parts.items()}
    return by_epoch, log


def footprints(by_epoch):
    """Union of each site's outlines over all six epochs (used to recognise on-site sheds, not scored)."""
    sites = sorted({s for s, _ in by_epoch})
    return {s: unary_union([g for (t, _), g in by_epoch.items() if t == s]) for s in sites}
