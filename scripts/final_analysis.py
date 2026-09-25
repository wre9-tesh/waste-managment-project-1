"""
FINAL area & perimeter trend analysis - Gujarat dumpsites 2016-2026
Input : ../Locations of landfills in gujurat completer.kml
Outputs (relative to 'FInal presentation material'):
  tables/final_results.xlsx (all tables), tables/*.csv
  data/outlines_by_site_epoch.geojson, data/outlines_by_part.geojson, data/results.json
Decisions (student, 25 Sep 2026):
  - Sites with parts (a, b, c, ...) are reported as ONE site: area and perimeter = sum of parts.
    Applies to Surat LF-2 Khajod (a+b+c), Vadodara LF-2 (old dump + a + b), Ahmedabad LF-2 (a+b).
  - A part not present in an epoch that the site was traced in counts as 0
    (Surat LF-2(a) remediated 2020; Ahmedabad LF-2(b) remediated 2026; Vadodara LF-2 old dump
    remediated 2022; Vadodara LF-2(a)/(b) = 0 in 2020: cleared, then illegal dumping resumed).
  - 2025 images used as the 2024 epoch. Jamnagar LF-2 (remediated) not included. SUR-03 dropped.
"""
import re, csv, json, math, itertools, os
import xml.etree.ElementTree as ET
from collections import defaultdict
from shapely.geometry import Polygon, mapping
from shapely.ops import transform, unary_union
from pyproj import Transformer
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KML = os.path.join(BASE, 'Locations of landfills in gujurat completer.kml')
T = lambda *p: os.path.join(BASE, 'tables', *p)
D = lambda *p: os.path.join(BASE, 'data', *p)
EPOCHS = [2016, 2018, 2020, 2022, 2024, 2026]
EPOCH_MAP = {2025: 2024}
CITY = {'ahmedabad': 'AHM', 'surat': 'SUR', 'vadodara': 'VAD', 'rajkot': 'RAJ', 'bhavnagar': 'BHV',
        'gandhinagar': 'GNR', 'jamnagar': 'JAM', 'bhuj': 'BHJ', 'mehsana': 'MEH', 'vapi': 'VAP'}
CITYNAME = {v: k.title() for k, v in CITY.items()}
NAMES = {'AHM-01': 'Ahmedabad LF-1 (Pirana)', 'AHM-02': 'Ahmedabad LF-2', 'AHM-03': 'Ahmedabad LF-3',
         'SUR-01': 'Surat LF-1 (Bhatar)', 'SUR-02': 'Surat LF-2 (Khajod)', 'VAD-01': 'Vadodara LF-1',
         'VAD-02': 'Vadodara LF-2', 'RAJ-01': 'Rajkot LF-1', 'BHV-01': 'Bhavnagar LF-1',
         'GNR-01': 'Gandhinagar LF-1', 'JAM-01': 'Jamnagar LF-1', 'BHJ-01': 'Bhuj LF-1',
         'MEH-01': 'Mehsana LF-1', 'VAP-01': 'Vapi LF-1'}
MAJOR = {'AHM', 'SUR', 'VAD', 'RAJ', 'BHV'}
SIMPLIFY, BUF = 5.0, 2.0
fwd = Transformer.from_crs(4326, 32643, always_xy=True).transform
inv = Transformer.from_crs(32643, 4326, always_xy=True).transform
loc = lambda t: t.split('}')[-1]

def parse(name):
    low = name.lower().replace('vadoara', 'vadodara')
    city = re.match(r'\s*([a-z]+)', low).group(1)
    m = re.search(r'lf\s*-?\s*(\d)(?!\d)\s*(?:\(\s*([a-z][a-z\s+]*)\s*\))?', low)
    lf = m.group(1) if m else '1'
    part = re.sub(r'\s+', '', m.group(2)) if (m and m.group(2)) else 'main'
    yr = re.search(r'(20\d\d)', low)
    flag = bool(re.search(r'remed|remid|\bnone\b', low))
    return city, lf, part, (int(yr.group(1)) if yr else None), flag

root = ET.parse(KML).getroot()
parts = defaultdict(list)          # (sid, epoch, part) -> [geom]
present = set(); log = []; points = {}
for pm in root.iter():
    if loc(pm.tag) != 'Placemark': continue
    name = next((c.text or '' for c in pm if loc(c.tag) == 'name'), '').strip()
    city, lf, part, yr, flag = parse(name)
    if city not in CITY: log.append(f'IGNORED (city): {name}'); continue
    if city == 'jamnagar' and lf == '2': log.append(f'IGNORED (Jamnagar LF-2 not in study): {name}'); continue
    sid = f'{CITY[city]}-{int(lf):02d}'
    polys = [e for e in pm.iter() if loc(e.tag) == 'Polygon']
    if not polys:
        pt = next((e for e in pm.iter() if loc(e.tag) == 'coordinates'), None)
        if yr is None:
            if pt is not None and part == 'main' and not flag: points[sid] = tuple(map(float, pt.text.split()[0].split(',')[:2]))
            log.append(f'point (no epoch): {name} -> {sid}'); continue
        ep = EPOCH_MAP.get(yr, yr); present.add((sid, ep))
        log.append(f'{name} -> {sid} part {part} epoch {ep}: no waste (0)'); continue
    if yr is None: log.append(f'IGNORED (polygon without year): {name}'); continue
    ep = EPOCH_MAP.get(yr, yr)
    if yr != ep: log.append(f'{name} -> {sid}: image {yr} used as epoch {ep}')
    for pg in polys:
        coords = next(e for e in pg.iter() if loc(e.tag) == 'coordinates').text.split()
        g = transform(fwd, Polygon([tuple(map(float, c.split(',')[:2])) for c in coords]))
        parts[(sid, ep, part)].append(g if g.is_valid else g.buffer(0))
    present.add((sid, ep))

sites = sorted({k[0] for k in present})
def perim(g):
    ps = [g] if g.geom_type == 'Polygon' else list(g.geoms)
    return sum(p.exterior.length for p in ps)

part_rows, rows, geoms = [], {}, {}
overlap_notes = []
for sid in sites:
    for ep in EPOCHS:
        if (sid, ep) not in present:
            rows[(sid, ep)] = dict(site_id=sid, epoch=ep, status='missing'); geoms[(sid, ep)] = None; continue
        pk = sorted(k[2] for k in parts if k[0] == sid and k[1] == ep)
        pg = {p: unary_union(parts[(sid, ep, p)]) for p in pk}
        A = P = U = 0.0
        for p, g in pg.items():
            a = g.area; pp = perim(g.simplify(SIMPLIFY, preserve_topology=True))
            u = (g.buffer(BUF).area - g.buffer(-BUF).area) / 2
            A += a; P += pp; U += u
            part_rows.append(dict(site_id=sid, site=NAMES[sid], epoch=ep, part=p, area_ha=a / 1e4, perimeter_m=pp))
        un = unary_union(list(pg.values())) if pg else None
        if un is not None and A - un.area > 100:
            overlap_notes.append(f'{sid} {ep}: parts overlap by {(A - un.area) / 1e4:.2f} ha (sum used)')
        n = 0 if un is None else (1 if un.geom_type == 'Polygon' else len(un.geoms))
        r = dict(site_id=sid, epoch=ep, status='traced' if A > 0 else 'none', n_parts=n,
                 parts_traced='+'.join(pk) if pk else '-', area_ha=A / 1e4, area_unc_ha=U / 1e4, perimeter_m=P)
        if A > 0:
            r.update(shape_index=P / (2 * math.sqrt(math.pi * A)), compactness=4 * math.pi * A / P ** 2,
                     fractal_dim=2 * math.log(P / 4) / math.log(A))
        rows[(sid, ep)] = r; geoms[(sid, ep)] = un

def theil_sen(x, y):
    s = sorted((y[j] - y[i]) / (x[j] - x[i]) for i, j in itertools.combinations(range(len(x)), 2))
    n = len(s); return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
def mk(y):
    n = len(y); sgn = lambda v: (v > 0) - (v < 0)
    S = sum(sgn(y[j] - y[i]) for i, j in itertools.combinations(range(n), 2))
    cnt = tot = 0
    for p in itertools.permutations(y):
        s = sum(sgn(p[j] - p[i]) for i, j in itertools.combinations(range(n), 2)); cnt += abs(s) >= abs(S); tot += 1
    return S, S / (n * (n - 1) / 2), cnt / tot
E = Polygon()
summary, trans = [], []
for sid in sites:
    ser = [(ep, rows[(sid, ep)]) for ep in EPOCHS if rows[(sid, ep)]['status'] != 'missing']
    x = [e for e, _ in ser]; y = [r['area_ha'] for _, r in ser]; per = [r['perimeter_m'] for _, r in ser]
    a0, a1 = y[0], y[-1]; ip = max(range(len(y)), key=lambda i: y[i]); pk, pky = y[ip], x[ip]
    rel = [r['area_unc_ha'] / r['area_ha'] for _, r in ser if r['area_ha'] > 0]; urel = sum(rel) / len(rel)
    Th = max(0.15, 2 * urel)
    net = (a1 - a0) / a0 if a0 else None; rise = (pk - a0) / a0 if a0 else None; fall = (a1 - pk) / pk if pk else None
    it = min(range(len(y)), key=lambda i: y[i]); tr = y[it]
    rebound = (a1 - tr) / tr if tr else None
    ch = [(y[i + 1] - y[i]) / y[i] if y[i] else 0 for i in range(len(y) - 1)]
    sig = [c for c in ch if abs(c) > Th]
    reversals = sum(1 for i in range(1, len(sig)) if (sig[i] > 0) != (sig[i - 1] > 0))
    if a0 == 0 and a1 > 0: cls = 'Emerging'
    elif a1 == 0: cls = 'Cleared'
    elif net < -Th and 0 < it < len(y) - 1 and rebound > Th: cls = 'Cleared then regrowing'
    elif 0 < ip < len(y) - 1 and rise > Th and fall < -Th: cls = 'Rise and fall'
    elif net > Th: cls = 'Expanding'
    elif net < -Th: cls = 'Contracting'
    else: cls = 'Stable'
    for (e0, r0), (e1, r1) in zip(ser, ser[1:]):
        g0 = geoms[(sid, e0)] or E; g1 = geoms[(sid, e1)] or E
        kept = g0.intersection(g1).area if not (g0.is_empty or g1.is_empty) else 0
        uni = g0.union(g1).area if not (g0.is_empty and g1.is_empty) else 0
        trans.append(dict(site_id=sid, from_epoch=e0, to_epoch=e1,
                          gained_ha=(g1.difference(g0).area if not g1.is_empty else 0) / 1e4,
                          lost_ha=(g0.difference(g1).area if not g0.is_empty else 0) / 1e4,
                          persistent_ha=kept / 1e4, iou=kept / uni if uni else None,
                          d_area_ha=r1['area_ha'] - r0['area_ha'],
                          d_area_pct=100 * (r1['area_ha'] - r0['area_ha']) / r0['area_ha'] if r0['area_ha'] else None))
    g0 = geoms[(sid, x[0])] or E; g1 = geoms[(sid, x[-1])] or E
    ever = unary_union([g for g in (geoms[(sid, e)] for e in x) if g is not None])
    S_, tau, p = mk(y)
    r0, r1 = ser[0][1], ser[-1][1]
    summary.append(dict(
        site_id=sid, site=NAMES[sid], city=CITYNAME[sid[:3]], group='Major city' if sid[:3] in MAJOR else 'Other city',
        n_parts_max=max(r['n_parts'] for _, r in ser), epochs=len(ser),
        area_2016_ha=a0, area_2026_ha=a1, net_change_ha=a1 - a0, net_change_pct=100 * net if net is not None else None,
        peak_ha=pk, peak_year=pky, peak_to_2026_pct=100 * fall if fall is not None else None,
        theil_sen_ha_per_yr=theil_sen(x, y), mk_S=S_, mk_tau=tau, mk_p_exact=p,
        perimeter_2016_m=per[0], perimeter_2026_m=per[-1],
        perimeter_change_pct=100 * (per[-1] - per[0]) / per[0] if per[0] else None,
        perimeter_theil_sen_m_per_yr=theil_sen(x, per),
        shape_index_2016=r0.get('shape_index'), shape_index_2026=r1.get('shape_index'),
        compactness_2016=r0.get('compactness'), compactness_2026=r1.get('compactness'),
        fractal_dim_2016=r0.get('fractal_dim'), fractal_dim_2026=r1.get('fractal_dim'),
        ever_under_waste_ha=ever.area / 1e4,
        newly_covered_since_2016_ha=(g1.difference(g0).area if not g1.is_empty else 0) / 1e4,
        no_longer_waste_2026_ha=(ever.area - (g1.area if not g1.is_empty else 0)) / 1e4,
        trough_ha=tr, trough_year=x[it], trough_to_2026_pct=100 * rebound if rebound is not None else None,
        significant_reversals=reversals,
        mean_edge_uncertainty_pct=100 * urel, change_threshold_pct=100 * Th, trajectory=cls))

# city & group totals
city_tot = defaultdict(dict); grp = defaultdict(lambda: defaultdict(float))
for sid in sites:
    for ep in EPOCHS:
        r = rows[(sid, ep)]
        if r['status'] == 'missing': continue
        c = CITYNAME[sid[:3]]; city_tot[c][ep] = city_tot[c].get(ep, 0) + r['area_ha']
        g = 'Major city' if sid[:3] in MAJOR else 'Other city'
        grp[g][ep] += r['area_ha']; grp['All sites'][ep] += r['area_ha']
city_rows = [dict(city=c, group='Major city' if CITY[c.lower()] in MAJOR else 'Other city',
                  n_sites=len([s for s in sites if CITYNAME[s[:3]] == c]), **{str(e): d.get(e) for e in EPOCHS},
                  net_change_ha=d[2026] - d[2016], net_change_pct=100 * (d[2026] - d[2016]) / d[2016])
             for c, d in sorted(city_tot.items())]
grp_rows = [dict(group=g, **{str(e): d[e] for e in EPOCHS}, net_change_ha=d[2026] - d[2016],
                 net_change_pct=100 * (d[2026] - d[2016]) / d[2016]) for g, d in grp.items()]

epoch_rows = [dict(site=NAMES[k[0]], **{kk: vv for kk, vv in rows[k].items()}) for k in sorted(rows)]
def rnd(v): return round(v, 4) if isinstance(v, float) else v
dfs = {'site_summary': summary, 'site_by_epoch': epoch_rows, 'parts_by_epoch': part_rows,
       'city_totals': city_rows, 'group_totals': grp_rows, 'transitions': trans}
with pd.ExcelWriter(T('final_results.xlsx')) as xw:
    for name, data in dfs.items():
        df = pd.DataFrame([{k: rnd(v) for k, v in d.items()} for d in data])
        df.to_excel(xw, sheet_name=name, index=False); df.to_csv(T(f'{name}.csv'), index=False)
    notes = pd.DataFrame({'note': [
        'Area/perimeter in EPSG:32643 (UTM 43N). Perimeter after 5 m Douglas-Peucker simplification.',
        'Multi-part sites (AHM-02, SUR-02, VAD-02): area and perimeter = sum of parts (student decision).',
        'Edge uncertainty: +/-2 m buffer method (Paul et al. 2013, 2020), summed over parts.',
        'Trajectory threshold = max(15%, 2 x mean relative edge uncertainty). Classes: Emerging, Cleared, Cleared then regrowing (net decline > threshold but 2026 > threshold above an interior low), Rise and fall, Expanding, Contracting, Stable. significant_reversals = direction changes among epoch-to-epoch changes larger than the threshold (>=2 = volatile path).',
        'Theil-Sen = median pairwise slope; Mann-Kendall exact permutation p with n=6 (descriptive).',
        'no_longer_waste_2026 = ever outlined 2016-2026 minus 2026 outline (cleared, biomined, built over, reshaped).'
    ] + [f'LOG: {l}' for l in log] + [f'OVERLAP: {o}' for o in overlap_notes]})
    notes.to_excel(xw, sheet_name='notes', index=False)

feats = [{'type': 'Feature', 'properties': {'site_id': s, 'site': NAMES[s], 'epoch': e, 'area_ha': round(g.area / 1e4, 3)},
          'geometry': mapping(transform(inv, g))} for (s, e), g in geoms.items() if g is not None and not g.is_empty]
json.dump({'type': 'FeatureCollection', 'features': feats}, open(D('outlines_by_site_epoch.geojson'), 'w'))
pf = [{'type': 'Feature', 'properties': {'site_id': s, 'epoch': e, 'part': p},
       'geometry': mapping(transform(inv, unary_union(g)))} for (s, e, p), g in parts.items()]
json.dump({'type': 'FeatureCollection', 'features': pf}, open(D('outlines_by_part.geojson'), 'w'))

shapes = {}
for sid in sites:
    allg = unary_union([g for g in (geoms[(sid, e)] for e in EPOCHS) if g is not None and not g.is_empty])
    cx, cy = allg.centroid.x, allg.centroid.y; shapes[sid] = {}
    for ep in EPOCHS:
        g = geoms[(sid, ep)]
        if g is None or g.is_empty: continue
        ps = [g] if g.geom_type == 'Polygon' else list(g.geoms)
        shapes[sid][ep] = [[[round(a - cx, 1), round(b - cy, 1)] for a, b in p.simplify(1.0).exterior.coords] for p in ps]
cent = {}
for sid in sites:
    if sid in points: cent[sid] = points[sid]
    else:
        allg = unary_union([g for g in (geoms[(sid, e)] for e in EPOCHS) if g is not None and not g.is_empty])
        cent[sid] = transform(inv, allg.centroid).coords[0]
json.dump(dict(epochs=EPOCHS, names=NAMES, rows=[rows[k] for k in sorted(rows)], parts=part_rows, summary=summary,
               transitions=trans, groups={g: dict(d) for g, d in grp.items()}, cities=city_rows, shapes=shapes,
               centroids=cent, log=log, overlaps=overlap_notes), open(D('results.json'), 'w'), default=float)
print('\n'.join(log)); print('OVERLAPS:', overlap_notes or 'none')
print('sites:', sites)
for s in summary:
    print(f"{s['site_id']:7} {s['area_2016_ha']:6.2f} -> {s['area_2026_ha']:6.2f}  net {s['net_change_pct']:+6.0f}%  peak {s['peak_ha']:5.1f}@{s['peak_year']}  TS {s['theil_sen_ha_per_yr']:+.2f}  tau {s['mk_tau']:+.2f} p {s['mk_p_exact']:.3f}  P {s['perimeter_2016_m']:.0f}->{s['perimeter_2026_m']:.0f}  parts {s['n_parts_max']}  {s['trajectory']}")
for r in grp_rows: print(r['group'], {e: round(r[str(e)], 1) for e in EPOCHS}, f"{r['net_change_pct']:+.0f}%")
for r in city_rows: print(r['city'], {e: round(r[str(e)] or 0, 1) for e in EPOCHS}, f"{r['net_change_pct']:+.0f}%")
