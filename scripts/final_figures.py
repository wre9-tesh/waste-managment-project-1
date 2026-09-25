"""
Slide-ready figures from data/results.json (run final_analysis.py first).
Saves PNG (200 dpi) into figures/ . Colours follow a CVD-validated palette:
Major-city sites = blue #2a78d6, other-city sites = orange #eb6834; epochs = blue ramp (light=2016 -> dark=2026).
"""
import json, math, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Polygon as MPoly

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = lambda *p: os.path.join(BASE, 'figures', *p)
os.makedirs(F('site_outlines'), exist_ok=True)
R = json.load(open(os.path.join(BASE, 'data', 'results.json')))
GJ = json.load(open(os.path.join(BASE, 'data', 'gujarat_boundary.geojson')))
EP = R['epochs']; S = R['summary']; ROWS = R['rows']; NAMES = R['names']
byid = {s['site_id']: s for s in S}
INK, INK2, MUTED, GRID, AXIS = '#0b0b0b', '#52514e', '#898781', '#e1e0d9', '#c3c2b7'
MAJ, OTH = '#2a78d6', '#eb6834'
ERAMP = ['#86b6ef', '#5598e7', '#2a78d6', '#1c5cab', '#104281', '#0d366b']
PARTC = {'main': '#4a3aa7', 'a': '#1baf7a', 'b': '#e87ba4', 'c': '#eda100', 'a+b': '#8a8a8a'}
gcol = lambda s: MAJ if s['group'] == 'Major city' else OTH
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 13, 'axes.edgecolor': AXIS, 'axes.labelcolor': INK2,
                     'xtick.color': INK2, 'ytick.color': INK2, 'axes.titlecolor': INK, 'axes.titlesize': 15,
                     'axes.titleweight': 'bold', 'axes.spines.top': False, 'axes.spines.right': False,
                     'figure.facecolor': 'white', 'axes.facecolor': 'white', 'savefig.facecolor': 'white'})
def grid(ax, axis='y'):
    ax.grid(axis=axis, color=GRID, lw=0.8); ax.set_axisbelow(True)
def save(fig, name):
    fig.savefig(F(name), dpi=200, bbox_inches='tight'); plt.close(fig); print('saved', name)
order = sorted(S, key=lambda s: (s['group'] != 'Major city', s['site_id']))
rows_of = lambda sid: [r for e in EP for r in ROWS if r['site_id'] == sid and r['epoch'] == e and r['status'] != 'missing']
SHORT = {'AHM-01': 'Ahmedabad-1\n(Pirana)', 'AHM-02': 'Ahmedabad-2', 'AHM-03': 'Ahmedabad-3', 'SUR-01': 'Surat-1\n(Bhatar)',
         'SUR-02': 'Surat-2\n(Khajod)', 'VAD-01': 'Vadodara-1', 'VAD-02': 'Vadodara-2', 'RAJ-01': 'Rajkot',
         'BHV-01': 'Bhavnagar', 'GNR-01': 'Gandhinagar', 'JAM-01': 'Jamnagar', 'BHJ-01': 'Bhuj', 'MEH-01': 'Mehsana', 'VAP-01': 'Vapi'}
one = lambda sid: SHORT[sid].replace('\n', ' ')

# ---------- fig01 study area map ----------
fig, ax = plt.subplots(figsize=(10, 8.2))
geom = GJ['geometry']; polys = geom['coordinates'] if geom['type'] == 'MultiPolygon' else [geom['coordinates']]
for poly in polys:
    ring = np.array(poly[0]); ax.add_patch(MPoly(ring, closed=True, fc='#f0efec', ec=MUTED, lw=0.8))
cities = {}
for s in S:
    lon, lat = R['centroids'][s['site_id']]
    size = 40 + 18 * s['area_2026_ha']
    ax.scatter(lon, lat, s=size, c=gcol(s), edgecolor='white', lw=1.2, zorder=3, alpha=0.9)
    cities.setdefault(s['city'], []).append((lon, lat))
LOFF = {'Ahmedabad': (0.12, 0.12), 'Gandhinagar': (0.12, 0.08), 'Mehsana': (0.12, 0.05), 'Vadodara': (0.12, 0.0), 'Surat': (0.12, 0.0),
        'Vapi': (0.12, 0.0), 'Bhavnagar': (0.12, -0.05), 'Rajkot': (0.12, 0.05), 'Jamnagar': (-0.12, 0.1), 'Bhuj': (0.12, 0.08)}
for c, pts in cities.items():
    lon = np.mean([p[0] for p in pts]); lat = np.mean([p[1] for p in pts]); dx, dy = LOFF.get(c, (0.12, 0))
    lab = c + (f' ({len(pts)} sites)' if len(pts) > 1 else '')
    ax.text(lon + dx, lat + dy, lab, fontsize=12, color=INK, ha='left' if dx > 0 else 'right', va='center', zorder=4)
ax.set_aspect(1 / math.cos(math.radians(22.5)))
ax.set_xlim(68.0, 74.8); ax.set_ylim(20.0, 24.8)
ax.set_xlabel('Longitude (°E)'); ax.set_ylabel('Latitude (°N)')
ax.plot([68.4, 68.4 + 100 / 102.8], [20.3, 20.3], color=INK, lw=3); ax.text(68.4, 20.42, '100 km', fontsize=11, color=INK)
h = [Line2D([], [], marker='o', ls='', color=MAJ, ms=10, label='Five most populous cities'),
     Line2D([], [], marker='o', ls='', color=OTH, ms=10, label='Other cities')]
for a in (2, 10, 30):
    h.append(Line2D([], [], marker='o', ls='', color='#bdbdbd', ms=math.sqrt(40 + 18 * a), label=f'{a} ha (2026 area)'))
ax.legend(handles=h, loc='center left', bbox_to_anchor=(1.01, 0.5), frameon=False, fontsize=11, labelspacing=1.3)


save(fig, 'fig01_study_area_map.png')

# ---------- fig02 total footprint ----------
G = {k: {int(e): v for e, v in d.items()} for k, d in R['groups'].items()}
kh = {r['epoch']: r['area_ha'] for r in ROWS if r['site_id'] == 'SUR-02'}
majx = {e: G['Major city'][e] - kh[e] for e in EP}
fig, axs = plt.subplots(1, 2, figsize=(14, 5.6), gridspec_kw={'width_ratios': [1.1, 1]})
ax = axs[0]
for name, d, c in [('Five most populous cities (9 sites)', G['Major city'], MAJ), ('Other cities (5 sites)', G['Other city'], OTH)]:
    ax.plot(EP, [d[e] for e in EP], color=c, lw=2.2, marker='o', ms=7, mec='white', mew=1.5)
    ax.text(2026.3, d[2026], f'{d[2026]:.0f} ha', color=INK, va='center', fontsize=12)
ax.plot(EP, [G['All sites'][e] for e in EP], color=INK2, lw=1.6, ls='--', marker='o', ms=5)
ax.text(2026.3, G['All sites'][2026], f'All: {G["All sites"][2026]:.0f} ha', color=INK, va='center', fontsize=12)
ax.annotate('Khajod part (a) cleared\n(−36.8 ha)', xy=(2020, G['Major city'][2020]), xytext=(2017.2, 60), fontsize=10.5, color=INK2,
            arrowprops=dict(arrowstyle='-', color=MUTED, lw=0.8))
ax.set_xticks(EP); ax.set_ylim(0, 220); ax.set_ylabel('Traced waste area (ha)'); grid(ax); ax.set_xlim(2015.5, 2028.2)
ax.set_title('Total waste footprint', loc='left')
ax.legend(handles=[Line2D([], [], color=MAJ, lw=2.2, marker='o', label='Five most populous cities'),
                   Line2D([], [], color=OTH, lw=2.2, marker='o', label='Other cities'),
                   Line2D([], [], color=INK2, lw=1.6, ls='--', label='All 14 sites')], frameon=False, loc='upper left', fontsize=11)
ax = axs[1]
for name, d, c, ls in [('Five most populous cities', G['Major city'], MAJ, '-'), ('… excluding Khajod', majx, MAJ, ':'), ('Other cities', G['Other city'], OTH, '-')]:
    idx = [100 * d[e] / d[2016] for e in EP]
    ax.plot(EP, idx, color=c, lw=2.2, ls=ls, marker='o', ms=6, mec='white', mew=1.2)
    ax.text(2026.3, idx[-1], f'{idx[-1]:.0f}', color=INK, va='center', fontsize=12)
ax.axhline(100, color=AXIS, lw=1)
ax.set_xticks(EP); ax.set_ylabel('Index (2016 = 100)'); grid(ax); ax.set_xlim(2015.5, 2027.6)
ax.set_title('Growth relative to 2016', loc='left')
ax.legend(handles=[Line2D([], [], color=MAJ, lw=2.2, label='Five most populous cities'),
                   Line2D([], [], color=MAJ, lw=2.2, ls=':', label='… excluding Khajod'),
                   Line2D([], [], color=OTH, lw=2.2, label='Other cities')], frameon=False, loc='upper left', fontsize=11)
fig.tight_layout(); save(fig, 'fig02_total_footprint_by_group.png')

# ---------- fig03 / fig11 small multiples ----------
def small_multiples(key, unc, ylab, fname, title, fmt):
    fig, axs = plt.subplots(4, 4, figsize=(16, 13)); axs = axs.ravel()
    for ax, s in zip(axs, order):
        rs = rows_of(s['site_id']); x = [r['epoch'] for r in rs]; y = [r[key] for r in rs]; c = gcol(s)
        if unc:
            u = [r.get('area_unc_ha', 0) for r in rs]
            ax.fill_between(x, [max(0, a - b) for a, b in zip(y, u)], [a + b for a, b in zip(y, u)], color=c, alpha=0.15, lw=0)
        ax.plot(x, y, color=c, lw=2, marker='o', ms=5, mec='white', mew=1)
        ax.set_ylim(0, max(y) * 1.35 if max(y) > 0 else 1); ax.set_xticks([2016, 2020, 2026]); grid(ax)
        ax.set_title(one(s['site_id']), loc='left', fontsize=13)
        ax.text(0.02, 0.95, s['trajectory'] if key == 'area_ha' else f"{s['perimeter_change_pct']:+.0f}% since 2016", transform=ax.transAxes,
                fontsize=10.5, color=INK2, va='top')
        ax.text(0.98, 0.95, fmt(y[0], y[-1]), transform=ax.transAxes, fontsize=10.5, color=INK, ha='right', va='top')
        ax.tick_params(labelsize=10.5)
    for ax in axs[len(order):]: ax.axis('off')
    axs[len(order)].legend(handles=[Patch(color=MAJ, label='Five most populous cities'), Patch(color=OTH, label='Other cities')]
                           + ([Patch(color='#999999', alpha=0.3, label='±2 m edge uncertainty')] if unc else []), frameon=False, loc='center left', fontsize=12)
    fig.suptitle(title, x=0.01, ha='left', fontsize=17, fontweight='bold'); fig.supylabel(ylab, fontsize=13, color=INK2)
    fig.tight_layout(); save(fig, fname)
small_multiples('area_ha', True, 'Traced waste area (ha) - each panel on its own scale', 'fig03_site_area_trends.png',
                'Waste area per site, 2016–2026', lambda a, b: f'{a:.1f} → {b:.1f} ha')
small_multiples('perimeter_m', False, 'Perimeter (m, 5 m simplified) - each panel on its own scale', 'fig11_site_perimeter_trends.png',
                'Perimeter per site, 2016–2026', lambda a, b: f'{a:,.0f} → {b:,.0f} m')

# ---------- fig04 net change ----------
d = sorted(S, key=lambda s: s['net_change_ha'])
fig, ax = plt.subplots(figsize=(11, 7))
yy = np.arange(len(d))
ax.barh(yy, [s['net_change_ha'] for s in d], color=[gcol(s) for s in d], height=0.62)
for i, s in enumerate(d):
    v = s['net_change_ha']; ax.text(v + (0.6 if v >= 0 else -0.6), i, f"{v:+.1f} ha ({s['net_change_pct']:+.0f}%)", va='center',
                                    ha='left' if v >= 0 else 'right', fontsize=11, color=INK)
ax.set_yticks(yy); ax.set_yticklabels([one(s['site_id']) for s in d]); ax.axvline(0, color=AXIS, lw=1)
ax.set_xlim(-60, 40); ax.set_xlabel('Change in traced waste area, 2016 → 2026 (ha)'); grid(ax, 'x')
ax.legend(handles=[Patch(color=MAJ, label='Five most populous cities'), Patch(color=OTH, label='Other cities')], frameon=False, loc='lower right')
ax.set_title('Net change in waste area per site, 2016 → 2026', loc='left')
save(fig, 'fig04_net_change_by_site.png')

# ---------- fig05 trajectory quadrant ----------
fig, ax = plt.subplots(figsize=(11, 8))
LBL = {'AHM-03': (0, 10, 'center'), 'RAJ-01': (0, -18, 'center'), 'VAD-01': (8, 10, 'left'), 'GNR-01': (0, 12, 'center'),
       'JAM-01': (8, 4, 'left'), 'BHJ-01': (-8, 4, 'right'), 'MEH-01': (8, 0, 'left'), 'VAP-01': (8, 0, 'left'), 'BHV-01': (8, 0, 'left'),
       'AHM-01': (10, 0, 'left'), 'SUR-02': (10, 0, 'left'), 'SUR-01': (10, 0, 'left'), 'VAD-02': (10, 0, 'left'), 'AHM-02': (10, 0, 'left')}
for s in S:
    x = s['peak_ha'] / s['area_2016_ha']; y = s['peak_to_2026_pct']
    ax.scatter(x, y, s=110, color=gcol(s), edgecolor='white', lw=1.5, zorder=3)
    dx, dy, ha = LBL.get(s['site_id'], (8, 0, 'left'))
    ax.annotate(one(s['site_id']), (x, y), xytext=(dx, dy), textcoords='offset points', ha=ha, va='center', fontsize=11, color=INK)
ax.set_xscale('log', base=2); ax.set_xticks([1, 2, 4, 8, 16]); ax.set_xticklabels(['no growth', '×2', '×4', '×8', '×16'])
ax.set_xlim(0.85, 20); ax.set_ylim(-100, 8); grid(ax, 'both')
ax.axvline(1.15, color=MUTED, ls='--', lw=1); ax.axhline(-15, color=MUTED, ls='--', lw=1)
ax.text(19, -10, 'grew, still at largest extent', ha='right', color=INK2, fontsize=11.5)
ax.text(19, -96, 'grew, then fell back', ha='right', color=INK2, fontsize=11.5)
ax.text(0.9, -96, 'shrank from 2016', ha='left', color=INK2, fontsize=11.5)
ax.set_xlabel('Largest extent reached ÷ 2016 area (log scale)'); ax.set_ylabel('Change from largest extent to 2026 (%)')
ax.legend(handles=[Patch(color=MAJ, label='Five most populous cities'), Patch(color=OTH, label='Other cities')], frameon=False, loc='lower center')
ax.set_title('Trajectory of each site (dashed lines = 15% change threshold)', loc='left')
save(fig, 'fig05_trajectory_quadrant.png')

# ---------- outline maps ----------
def draw_outlines(ax, sid, legend=False, bar=True):
    sh = R['shapes'][sid]; handles = []
    for i, e in enumerate(EP):
        rings = sh.get(str(e))
        if not rings: continue
        for k, ring in enumerate(rings):
            a = np.array(ring); ax.plot(a[:, 0], a[:, 1], color=ERAMP[i], lw=2.4 if e == 2026 else 1.4)
        area = [r for r in ROWS if r['site_id'] == sid and r['epoch'] == e][0]['area_ha']
        handles.append(Line2D([], [], color=ERAMP[i], lw=2.4 if e == 2026 else 1.6, label=f'{e}: {area:.1f} ha'))
    ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values(): sp.set_visible(False)
    xs = [p[0] for rs in sh.values() for ring in rs for p in ring]; ys = [p[1] for rs in sh.values() for ring in rs for p in ring]
    span = max(xs) - min(xs); L = 100 if span < 900 else 200 if span < 2000 else 500
    if bar:
        x0, y0 = min(xs), min(ys) - 0.08 * (max(ys) - min(ys) + 1)
        ax.plot([x0, x0 + L], [y0, y0], color=INK, lw=3); ax.text(x0, y0 - 0.02 * (max(ys) - min(ys) + 1), f'{L} m', va='top', fontsize=10, color=INK)
    return handles
fig, axs = plt.subplots(4, 4, figsize=(16, 16)); axs = axs.ravel()
for ax, s in zip(axs, order):
    draw_outlines(ax, s['site_id']); ax.set_title(one(s['site_id']), loc='left', fontsize=13)
for ax in axs[len(order):]: ax.axis('off')
axs[len(order)].legend(handles=[Line2D([], [], color=ERAMP[i], lw=2.4 if e == 2026 else 1.6, label=str(e)) for i, e in enumerate(EP)],
                       frameon=False, loc='center left', fontsize=13, title='Epoch', title_fontsize=13)
fig.suptitle('Traced waste outlines, 2016 (light) → 2026 (dark)', x=0.01, ha='left', fontsize=17, fontweight='bold')
fig.tight_layout(); save(fig, 'fig06_outlines_all_sites.png')
for s in S:
    fig, ax = plt.subplots(figsize=(8, 7))
    h = draw_outlines(ax, s['site_id'])
    ax.legend(handles=h, frameon=False, loc='upper left', bbox_to_anchor=(1.0, 1.0), fontsize=12, title='Epoch: area', title_fontsize=12)
    ax.set_title(f"{NAMES[s['site_id']]}: traced outlines", loc='left')
    save(fig, os.path.join('site_outlines', f"{s['site_id']}_outlines.png"))

# ---------- fig08 land turnover ----------
d = sorted(S, key=lambda s: s['newly_covered_since_2016_ha'] - s['no_longer_waste_2026_ha'])
fig, ax = plt.subplots(figsize=(12, 7.5)); yy = np.arange(len(d))
NEW, GONE = '#4a3aa7', '#1baf7a'
ax.barh(yy, [s['newly_covered_since_2016_ha'] for s in d], color=NEW, height=0.6)
ax.barh(yy, [-s['no_longer_waste_2026_ha'] for s in d], color=GONE, height=0.6)
for i, s in enumerate(d):
    a, b = s['newly_covered_since_2016_ha'], s['no_longer_waste_2026_ha']
    if a > 0.05: ax.text(a + 0.5, i, f'+{a:.1f}', va='center', fontsize=10.5, color=INK)
    if b > 0.05: ax.text(-b - 0.5, i, f'−{b:.1f}', va='center', ha='right', fontsize=10.5, color=INK)
ax.set_yticks(yy); ax.set_yticklabels([one(s['site_id']) for s in d]); ax.axvline(0, color=AXIS, lw=1); grid(ax, 'x')
tn = sum(s['newly_covered_since_2016_ha'] for s in S); tg = sum(s['no_longer_waste_2026_ha'] for s in S)
ax.set_xlim(-90, 35); ax.set_xlabel('Hectares')
ax.legend(handles=[Patch(color=NEW, label=f'Newly covered by waste since 2016 (total {tn:.0f} ha)'),
                   Patch(color=GONE, label=f'Held waste at some point, not in 2026 (total {tg:.0f} ha)')], frameon=False, loc='upper left', fontsize=11)
ax.set_title('Land turnover per site, 2016–2026', loc='left')
save(fig, 'fig08_land_turnover.png')

# ---------- fig09 compactness dumbbell ----------
d = sorted([s for s in S if s['compactness_2026'] is not None], key=lambda s: s['compactness_2026'] - s['compactness_2016'])
fig, ax = plt.subplots(figsize=(11, 7)); yy = np.arange(len(d))
for i, s in enumerate(d):
    a, b = s['compactness_2016'], s['compactness_2026']
    ax.plot([a, b], [i, i], color=AXIS, lw=2, zorder=1)
    ax.scatter(a, i, s=90, color=ERAMP[0], edgecolor='white', zorder=3); ax.scatter(b, i, s=90, color=ERAMP[5], edgecolor='white', zorder=3)
ax.set_yticks(yy); ax.set_yticklabels([one(s['site_id']) + (f" ({s['n_parts_max']} parts)" if s['n_parts_max'] > 1 else '') for s in d])
ax.set_xlim(0, 0.9); ax.set_xlabel('Compactness 4πA/P²  (1 = circle; lower = more irregular or fragmented)'); grid(ax, 'x')
ax.legend(handles=[Line2D([], [], marker='o', ls='', color=ERAMP[0], ms=9, label='2016'), Line2D([], [], marker='o', ls='', color=ERAMP[5], ms=9, label='2026')],
          frameon=False, loc='upper right')
ax.set_title('Shape: compactness 2016 vs 2026', loc='left')
save(fig, 'fig09_compactness_2016_2026.png')

# ---------- fig10 multi-part sites ----------
multi = [s['site_id'] for s in S if s['n_parts_max'] > 1 or s['site_id'] in ('SUR-02', 'VAD-02', 'AHM-02')]
multi = [m for m in ['SUR-02', 'VAD-02', 'AHM-02'] if m in byid]
fig, axs = plt.subplots(1, len(multi), figsize=(6 * len(multi), 5.5))
PLAB = {'main': 'old dump (unlabelled)', 'a': 'part (a)', 'b': 'part (b)', 'c': 'part (c)', 'a+b': '(a)+(b) traced together'}
for ax, sid in zip(np.atleast_1d(axs), multi):
    prs = [p for p in R['parts'] if p['site_id'] == sid]; keys = [k for k in ['main', 'a', 'b', 'c', 'a+b'] if any(p['part'] == k for p in prs)]
    bottom = np.zeros(len(EP))
    for k in keys:
        v = np.array([sum(p['area_ha'] for p in prs if p['part'] == k and p['epoch'] == e) for e in EP])
        ax.bar([str(e) for e in EP], v, bottom=bottom, color=PARTC[k], label=PLAB[k], width=0.62, edgecolor='white', lw=1.5)
        bottom += v
    for i, t in enumerate(bottom): ax.text(i, t + max(bottom) * 0.02, f'{t:.1f}', ha='center', fontsize=10.5, color=INK)
    ax.set_title(NAMES[sid], loc='left'); ax.set_ylabel('Waste area (ha)'); grid(ax); ax.set_ylim(0, max(bottom) * 1.15)
    ax.legend(frameon=False, fontsize=10.5, loc='upper right')
fig.suptitle('Sites traced in parts: area of each part (stacked = site total)', x=0.01, ha='left', fontsize=16, fontweight='bold')
fig.tight_layout(); save(fig, 'fig10_multipart_sites.png')

# ---------- fig12 city totals ----------
C = sorted(R['cities'], key=lambda c: c['net_change_ha'])
fig, ax = plt.subplots(figsize=(11, 6.5)); yy = np.arange(len(C))
for i, c in enumerate(C):
    a, b = c['2016'], c['2026']; col = MAJ if c['group'] == 'Major city' else OTH
    ax.annotate('', xy=(b, i), xytext=(a, i), arrowprops=dict(arrowstyle='-|>', color=col, lw=2, mutation_scale=16))
    ax.scatter(a, i, s=50, color='white', edgecolor=col, lw=2, zorder=3)
    ax.text(max(a, b) + 1.5, i, f"{a:.1f} → {b:.1f} ha ({c['net_change_pct']:+.0f}%)", va='center', fontsize=11, color=INK)
ax.set_yticks(yy); ax.set_yticklabels([f"{c['city']} ({c['n_sites']})" if c['n_sites'] > 1 else c['city'] for c in C])
ax.set_xlim(0, 100); ax.set_xlabel('Total traced waste area in the city (ha)   ○ 2016 → ▶ 2026'); grid(ax, 'x')
ax.legend(handles=[Patch(color=MAJ, label='Five most populous cities'), Patch(color=OTH, label='Other cities')], frameon=False, loc='center right')
ax.set_title('City totals, 2016 → 2026 (number of sites in brackets)', loc='left')
save(fig, 'fig12_city_totals.png')

# ---------- fig13 results table ----------
cols = ['Site', '2016 ha', '2026 ha', 'Net %', 'Largest (year)', 'Trend ha/yr', 'MK p', 'Perimeter (m)', 'Class']
data = [[one(s['site_id']), f"{s['area_2016_ha']:.1f}", f"{s['area_2026_ha']:.1f}", f"{s['net_change_pct']:+.0f}%",
         f"{s['peak_ha']:.1f} ({s['peak_year']})", f"{s['theil_sen_ha_per_yr']:+.2f}", f"{s['mk_p_exact']:.3f}",
         f"{s['perimeter_2016_m']:,.0f} → {s['perimeter_2026_m']:,.0f}", s['trajectory']] for s in order]
fig, ax = plt.subplots(figsize=(18, 7.2)); ax.axis('off')
tb = ax.table(cellText=data, colLabels=cols, loc='center', cellLoc='center', colLoc='center', colWidths=[0.17, 0.065, 0.065, 0.07, 0.105, 0.08, 0.06, 0.155, 0.17])
tb.auto_set_font_size(False); tb.set_fontsize(11.5); tb.scale(1, 1.7)
for (r, c), cell in tb.get_celld().items():
    cell.set_edgecolor(GRID); cell.set_linewidth(0.6)
    if r == 0: cell.set_text_props(color=INK2, fontweight='bold'); cell.set_facecolor('#f5f5f2')
    elif c == 0: cell.set_text_props(color=MAJ if order[r - 1]['group'] == 'Major city' else '#b4481c', fontweight='bold')
ax.set_title('Results per site (Theil–Sen trend; Mann–Kendall exact p, n = 6; blue = five most populous cities)', loc='left', fontsize=14)
save(fig, 'fig13_results_table.png')
