"""
Version 2 of final_figures.py - figures prepared to the Nature Reviews artwork guide
("Guide to designing figures" / "Guide to preparing figures").
Run final_analysis_v2.py first; this script reads data/results_v2.json (+ data/gujarat_boundary.geojson).

What the guide asks and how it is applied here
  - Vector files for data figures      -> every figure saved as PDF (editable text, TrueType fonts embedded);
                                           a 300 dpi PNG preview is written next to it for slides.
  - Whole figure AND each panel         -> FigN.pdf plus FigNa.pdf, FigNb.pdf ... for multi-panel figures.
  - Size max 180 mm x 215 mm, portrait  -> widths 88 mm (one column) or 180 mm (two columns); checked on save.
  - All text 8 pt; bold only for headings/panel letters, no italic or size for emphasis
                                        -> one font size (8 pt) everywhere; panel letters a, b, c bold.
  - No more than six panels per figure  -> the 14-panel grids of version 1 are replaced: area and perimeter per site
                                           become one heat-map figure (Fig. 3); outlines show six case-study sites
                                           (Fig. 6) and every site is kept as a supplementary map (Supplementary/).
  - Axes labelled with units, superscript exponents (ha yr⁻¹), axes include zero; italic single-letter variables
    (A, P); few abbreviations (no 'LF', 'MK', 'Th').
  - Key to colours and symbols; direct labels where they are clearer (Fig. 2 lines).
  - Colours used for grouping and kept consistent across figures:
        five most populous cities = blue #2a78d6, other cities = orange #eb6834 (validated CVD-safe pair);
        time (epochs, 2016 vs 2026) = grey ramp, light = 2016 -> black = 2026;
        land newly under waste = purple #4a3aa7, land no longer under waste = green #1baf7a;
        parts of a site = four colours, always also labelled with the part letter.
  - No figure titles inside the artwork (titles and legends belong in the caption; see figures_v2/caption_notes.md).
  - CMYK: matplotlib writes RGB PDFs. Convert at the end if a publisher asks, e.g. Ghostscript:
        gs -o Fig1_cmyk.pdf -sDEVICE=pdfwrite -sColorConversionStrategy=CMYK Fig1.pdf
Figure numbers run without gaps: Fig1 ... Fig10; Table 1 is written by final_analysis_v2.py.
"""
import json, math, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Polygon as MPoly
from matplotlib.colors import LinearSegmentedColormap

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, 'figures_v2')
os.makedirs(os.path.join(OUT, 'panels'), exist_ok=True); os.makedirs(os.path.join(OUT, 'supplementary'), exist_ok=True)
R = json.load(open(os.path.join(BASE, 'data', 'results_v2.json')))
GJ = json.load(open(os.path.join(BASE, 'data', 'gujarat_boundary.geojson')))
EP = R['epochs']; S = R['summary']; ROWS = R['rows']; LAB = R['labels']; GL = R['group_labels']
byid = {s['site_id']: s for s in S}; ORDER = R['order']
MM = 1 / 25.4; ONE, TWO, MAXH = 88, 180, 215                       # mm

# ---------- house style ----------
INK, INK2, GRID, AXIS = '#1a1a1a', '#4d4d4d', '#e3e3e3', '#8c8c8c'
MAJ, OTH = '#2a78d6', '#eb6834'
EGREY = ['#c9c9c9', '#a8a8a8', '#868686', '#646464', '#3f3f3f', '#111111']   # 2016 -> 2026
Y16, Y26 = EGREY[0], EGREY[-1]
NEW, GONE = '#4a3aa7', '#1baf7a'
PARTC = {'main': '#4a3aa7', 'a': '#1baf7a', 'b': '#e87ba4', 'c': '#eda100', 'a+b': '#8c8c8c'}
PARTL = {'main': 'old dump', 'a': 'a', 'b': 'b', 'c': 'c', 'a+b': 'a+b'}
LW = 0.75
plt.rcParams.update({
    'font.family': 'sans-serif', 'font.sans-serif': ['Arial', 'Helvetica', 'Liberation Sans', 'DejaVu Sans'],
    'font.size': 8, 'axes.titlesize': 8, 'axes.labelsize': 8, 'xtick.labelsize': 8, 'ytick.labelsize': 8,
    'legend.fontsize': 8, 'legend.title_fontsize': 8, 'figure.titlesize': 8, 'axes.titleweight': 'normal',
    'mathtext.default': 'regular', 'mathtext.fontset': 'custom', 'mathtext.it': 'sans:italic', 'mathtext.rm': 'sans', 'mathtext.cal': 'sans', 'mathtext.sf': 'sans', 'mathtext.tt': 'monospace', 'mathtext.bf': 'sans:bold', 'pdf.fonttype': 42, 'ps.fonttype': 42, 'svg.fonttype': 'none',
    'axes.linewidth': 0.5, 'xtick.major.width': 0.5, 'ytick.major.width': 0.5, 'xtick.major.size': 2.5, 'ytick.major.size': 2.5,
    'axes.edgecolor': AXIS, 'axes.labelcolor': INK, 'xtick.color': INK2, 'ytick.color': INK2, 'text.color': INK,
    'axes.spines.top': False, 'axes.spines.right': False, 'lines.linewidth': 1.0, 'legend.frameon': False,
    'figure.facecolor': 'white', 'axes.facecolor': 'white', 'savefig.facecolor': 'white'})
gcol = lambda s: MAJ if s['group'] == 'Major city' else OTH
GROUP_KEY = [Patch(color=MAJ, label=GL['Major city']), Patch(color=OTH, label=GL['Other city'])]
pm = lambda v, f='.1f': f'{v:+{f}}'.replace('-', '−')          # typographic minus sign
def grid(ax, axis='y'): ax.grid(axis=axis, color=GRID, lw=0.5); ax.set_axisbelow(True)
def letter(ax, l, x=-0.02, y=1.02):
    ax.text(x, y, l, transform=ax.transAxes, fontweight='bold', ha='right', va='bottom')

def save(fig, name, w_mm, h_mm):
    assert w_mm <= TWO and h_mm <= MAXH, f'{name}: {w_mm} x {h_mm} mm exceeds 180 x 215 mm'
    kw = dict(bbox_inches='tight', pad_inches=0.03)                    # trims empty margins
    bb = fig.get_tightbbox(fig.canvas.get_renderer())
    aw, ah = (bb.width + 0.06) * 25.4, (bb.height + 0.06) * 25.4       # final size of the saved file
    assert aw <= TWO and ah <= MAXH, f'{name}: saved size {aw:.0f} x {ah:.0f} mm exceeds 180 x 215 mm'
    fig.savefig(os.path.join(OUT, name + '.pdf'), **kw); fig.savefig(os.path.join(OUT, name + '.png'), dpi=300, **kw)
    plt.close(fig); print(f'saved {name}  ({aw:.0f} x {ah:.0f} mm)')

def figure(name, w_mm, h_mm, panels, layout=None, extra=None, panel_mm=None, fig_legend=None):
    """panels = list of draw(ax) functions. Saves the whole figure and, if >1 panel, each panel separately."""
    assert len(panels) <= 6, 'guide: no more than six panels per figure'
    nr, nc = layout or (1, len(panels))
    fig, axs = plt.subplots(nr, nc, figsize=(w_mm * MM, h_mm * MM), squeeze=False, **(extra or {}))
    axs = axs.ravel()
    for i, (ax, draw) in enumerate(zip(axs, panels)):
        draw(ax)
        if len(panels) > 1: letter(ax, 'abcdef'[i])
    for ax in axs[len(panels):]: ax.axis('off')
    if fig_legend:
        fig.legend(**fig_legend); fig.tight_layout(pad=0.4, rect=(0, 0.06, 1, 1))
    else: fig.tight_layout(pad=0.4)
    save(fig, name, w_mm, h_mm)
    if len(panels) > 1:
        pw, ph = panel_mm or (w_mm / nc, h_mm / nr)
        for i, draw in enumerate(panels):
            f, ax = plt.subplots(figsize=(pw * MM, ph * MM)); draw(ax); f.tight_layout(pad=0.4)
            f.savefig(os.path.join(OUT, 'panels', f'{name}{"abcdef"[i]}.pdf')); plt.close(f)

rows_of = lambda sid: [r for e in EP for r in ROWS if r['site_id'] == sid and r['epoch'] == e and r['status'] != 'missing']
area = lambda sid, e: next(r['area_ha'] for r in ROWS if r['site_id'] == sid and r['epoch'] == e)

# ---------- Fig1 study area ----------
def p_map(ax):
    geom = GJ['geometry']; polys = geom['coordinates'] if geom['type'] == 'MultiPolygon' else [geom['coordinates']]
    for poly in polys: ax.add_patch(MPoly(np.array(poly[0]), closed=True, fc='#f2f2f2', ec=AXIS, lw=0.5))
    cities = {}
    for s in S:
        lon, lat = R['centroids'][s['site_id']]
        ax.scatter(lon, lat, s=8 + 3 * s['area_2026_ha'], color=gcol(s), edgecolor='white', lw=0.5, zorder=3)
        cities.setdefault(s['city'], []).append((lon, lat))
    off = {'Jamnagar': -0.12, 'Mehsana': -0.12, 'Ahmedabad': 0.22}
    for c, pts in cities.items():
        lon = np.mean([p[0] for p in pts]); lat = np.mean([p[1] for p in pts]); dx = off.get(c, 0.14)
        ax.text(lon + dx, lat, c + (f' ({len(pts)})' if len(pts) > 1 else ''), ha='left' if dx > 0 else 'right', va='center', zorder=4)
    ax.set_aspect(1 / math.cos(math.radians(22.5))); ax.set_xlim(68.0, 74.8); ax.set_ylim(20.0, 24.8)
    ax.set_xlabel('Longitude (°E)'); ax.set_ylabel('Latitude (°N)')
    ax.plot([68.3, 68.3 + 100 / 102.8], [20.25, 20.25], color=INK, lw=1.2); ax.text(68.3, 20.35, '100 km')
    h = GROUP_KEY + [Line2D([], [], marker='o', ls='', color='#bdbdbd', mec='white', ms=math.sqrt(8 + 3 * a), label=f'{a} ha') for a in (2, 10, 30)]
    ax.legend(handles=h, loc='upper center', bbox_to_anchor=(0.5, -0.17), ncol=3, handletextpad=0.4, columnspacing=1.0)
figure('Fig1', ONE, 92, [p_map])

# ---------- Fig2 total footprint ----------
G = {k: {int(e): v for e, v in d.items()} for k, d in R['groups'].items()}
kh = {r['epoch']: r['area_ha'] for r in ROWS if r['site_id'] == 'SUR-02'}
majx = {e: G['Major city'][e] - kh[e] for e in EP}
def end_labels(ax, items, x=2026.4):
    ys = sorted(items, key=lambda t: t[0]); placed = []
    lim = ax.get_ylim(); gap = 0.11 * (lim[1] - lim[0])
    for y, txt in ys:
        yy = max(y, placed[-1] + gap) if placed else y; placed.append(yy); ax.text(x, yy, txt, va='center')
def p_total(ax):
    series = [(G['Major city'], MAJ, '-', GL['Major city']), (G['Other city'], OTH, '-', GL['Other city']), (G['All sites'], INK2, '--', GL['All sites'])]
    for d, c, ls, _ in series: ax.plot(EP, [d[e] for e in EP], color=c, ls=ls, marker='o', ms=3, lw=1.0)
    ax.set_xticks(EP); ax.set_xlim(2015.5, 2030.8); ax.set_ylim(0, 210); ax.set_ylabel('Traced waste area (ha)'); ax.set_xlabel('Year'); grid(ax)
    ax.spines['bottom'].set_bounds(2016, 2026)
    end_labels(ax, [(d[2026], f'{lab},\n{d[2026]:.0f} ha') for d, _, _, lab in series])
def p_index(ax):
    series = [(G['Major city'], MAJ, '-', GL['Major city']), (majx, MAJ, ':', 'Five most populous cities\nwithout Surat 2 (Khajod)'),
              (G['Other city'], OTH, '-', GL['Other city'])]
    for d, c, ls, _ in series: ax.plot(EP, [100 * d[e] / d[2016] for e in EP], color=c, ls=ls, marker='o', ms=3, lw=1.0)
    ax.hlines(100, 2016, 2026, color=AXIS, lw=0.5); ax.set_xticks(EP); ax.set_xlim(2015.5, 2030.8); ax.set_ylim(0, 260)
    ax.spines['bottom'].set_bounds(2016, 2026)
    ax.set_ylabel('Waste area relative to 2016 (2016 = 100)'); ax.set_xlabel('Year'); grid(ax)
    end_labels(ax, [(100 * d[2026] / d[2016], f'{lab},\n{100 * d[2026] / d[2016]:.0f}') for d, _, _, lab in series])
figure('Fig2', TWO, 75, [p_total, p_index])

# ---------- Fig3 area and perimeter per site and epoch (heat maps) ----------
CMAP = LinearSegmentedColormap.from_list('grey', ['#f4f4f4', '#6e6e6e', '#1a1a1a'])
def heat(ax, key, fmt, show_labels):
    M = np.array([[next(r[key] for r in ROWS if r['site_id'] == sid and r['epoch'] == e) for e in EP] for sid in ORDER])
    rel = 100 * M / M.max(axis=1, keepdims=True)
    im = ax.pcolormesh(np.arange(len(EP) + 1) - 0.5, np.arange(len(ORDER) + 1) - 0.5, rel, cmap=CMAP, vmin=0, vmax=100)   # vector cells
    ax.set_xlim(-0.5, len(EP) - 0.5); ax.set_ylim(len(ORDER) - 0.5, -0.5)
    for i in range(len(ORDER)):
        for j in range(len(EP)):
            ax.text(j, i, fmt(M[i, j]), ha='center', va='center', color='white' if rel[i, j] > 55 else INK)
    ax.set_xticks(range(len(EP))); ax.set_xticklabels(EP); ax.xaxis.tick_top(); ax.tick_params(length=0)
    ax.set_yticks(range(len(ORDER))); ax.set_yticklabels([LAB[s] for s in ORDER] if show_labels else [])
    for sp in ax.spines.values(): sp.set_visible(False)
    nmaj = sum(1 for s in ORDER if byid[s]['group'] == 'Major city')
    ax.axhline(nmaj - 0.5, color='white', lw=2.5)
    if show_labels:
        for (y0, y1, g, c) in [(-0.5, nmaj - 0.5, 'Major city', MAJ), (nmaj - 0.5, len(ORDER) - 0.5, 'Other city', OTH)]:
            ax.plot([-0.62, -0.62], [y0 + 0.1, y1 - 0.1], color=c, lw=3, clip_on=False, solid_capstyle='butt')
        ax.tick_params(axis='y', pad=7)
    return im
def p_heat_area(ax):
    im = heat(ax, 'area_ha', lambda v: f'{v:.1f}', True); ax.set_xlabel('Traced waste area (ha)'); ax.xaxis.set_label_position('top')
    ax.legend(handles=GROUP_KEY, loc='upper center', bbox_to_anchor=(0.5, -0.02), ncol=2, title='Bar at left: city group')
def p_heat_per(ax):
    im = heat(ax, 'perimeter_m', lambda v: f'{v / 1000:.2f}', True); ax.set_xlabel('Perimeter (km)'); ax.xaxis.set_label_position('top')
    cax = ax.inset_axes([0.05, -0.075, 0.9, 0.022])                       # colour key drawn as vector cells
    v = np.linspace(0, 100, 101); cax.pcolormesh(v, [0, 1], v[None, :-1], cmap=CMAP, vmin=0, vmax=100)
    cax.set_yticks([]); cax.set_xticks(range(0, 101, 20)); cax.tick_params(width=0.5, length=2)
    for sp in cax.spines.values(): sp.set_visible(True); sp.set_linewidth(0.5)
    cax.set_xlabel("Shading: value as % of the site's own maximum")
figure('Fig3', 170, 125, [p_heat_area, p_heat_per])

# ---------- Fig4 net change ----------
def p_net(ax):
    d = sorted(S, key=lambda s: s['net_change_ha']); yy = np.arange(len(d))
    ax.barh(yy, [s['net_change_ha'] for s in d], color=[gcol(s) for s in d], height=0.62)
    for i, s in enumerate(d):
        v = s['net_change_ha']; ax.text(v + (0.6 if v >= 0 else -0.6), i, f"{pm(v)} ha ({pm(s['net_change_pct'], '.0f')}%)",
                                        va='center', ha='left' if v >= 0 else 'right')
    ax.set_yticks(yy); ax.set_yticklabels([LAB[s['site_id']] for s in d]); ax.tick_params(axis='y', length=0)
    ax.axvline(0, color=AXIS, lw=0.5); ax.set_xlim(-72, 40); grid(ax, 'x')
    ax.set_xlabel('Net change in traced waste area, 2016–2026 (ha)')
    ax.legend(handles=GROUP_KEY, loc='lower left', bbox_to_anchor=(0, 1.0), ncol=2)
figure('Fig4', ONE + 30, 90, [p_net])

# ---------- Fig5 trajectory ----------
def p_traj(ax):
    LBL = {'AHM-03': (0, 7, 'center'), 'RAJ-01': (0, -8, 'center'), 'VAD-01': (5, 6, 'left'), 'GNR-01': (0, 7, 'center'),
           'JAM-01': (5, 3, 'left'), 'BHJ-01': (-5, 3, 'right')}
    for s in S:
        x = s['peak_ha'] / s['area_2016_ha']; y = s['peak_to_2026_pct']
        ax.scatter(x, y, s=16, color=gcol(s), edgecolor='white', lw=0.5, zorder=3)
        dx, dy, ha = LBL.get(s['site_id'], (5, 0, 'left'))
        ax.annotate(LAB[s['site_id']], (x, y), xytext=(dx, dy), textcoords='offset points', ha=ha, va='center')
    ax.set_xscale('log', base=2); ax.set_xticks([1, 2, 4, 8, 16]); ax.set_xticklabels(['1', '2', '4', '8', '16'])
    ax.minorticks_off(); ax.set_xlim(0.85, 20); ax.set_ylim(-100, 10); grid(ax, 'both')
    ax.axvline(1.15, color=AXIS, ls='--', lw=0.5); ax.axhline(-15, color=AXIS, ls='--', lw=0.5)
    ax.text(19, -11, 'grew, still at or near largest area', ha='right', color=INK2)
    ax.text(19, -95, 'grew, then fell back', ha='right', color=INK2); ax.text(0.9, -95, 'largest in 2016', ha='left', color=INK2)
    ax.set_xlabel('Largest area reached ÷ area in 2016 (log scale)'); ax.set_ylabel('Change from largest area to 2026 (%)')
    ax.legend(handles=GROUP_KEY + [Line2D([], [], color=AXIS, ls='--', lw=0.5, label='15% change threshold')], loc='lower center', ncol=3,
              bbox_to_anchor=(0.5, 1.0))
figure('Fig5', TWO, 110, [p_traj])

# ---------- outlines ----------
def draw_outlines(ax, sid, legend_areas=False):
    sh = R['shapes'][sid]; handles = []
    for i, e in enumerate(EP):
        for ring in sh.get(str(e), []):
            a = np.array(ring); ax.plot(a[:, 0], a[:, 1], color=EGREY[i], lw=1.2 if e == 2026 else 0.6)
        handles.append(Line2D([], [], color=EGREY[i], lw=1.2 if e == 2026 else 0.8, label=f'{e}: {area(sid, e):.1f} ha' if legend_areas else str(e)))
    ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values(): sp.set_visible(False)
    xs = [p[0] for rs in sh.values() for ring in rs for p in ring]; ys = [p[1] for rs in sh.values() for ring in rs for p in ring]
    span = max(xs) - min(xs); L = 100 if span < 900 else 200 if span < 2000 else 500
    x0, y0 = min(xs), min(ys) - 0.08 * (max(ys) - min(ys) + 1)
    ax.plot([x0, x0 + L], [y0, y0], color=INK, lw=1.2); ax.text(x0, y0 - 0.02 * (max(ys) - min(ys) + 1), f'{L} m', va='top')
    return handles
CASE = ['SUR-02', 'AHM-01', 'RAJ-01', 'VAD-02', 'GNR-01', 'BHV-01']
def p_out(sid):
    def f(ax):
        draw_outlines(ax, sid); ax.set_title(f'{LAB[sid]}: {area(sid, 2016):.1f} → {area(sid, 2026):.1f} ha', loc='left', pad=6)
    return f
EPOCH_KEY = [Line2D([], [], color=EGREY[i], lw=1.2 if e == 2026 else 0.8, label=str(e)) for i, e in enumerate(EP)]
figure('Fig6', TWO, 150, [p_out(s) for s in CASE], layout=(2, 3), panel_mm=(60, 75),
       fig_legend=dict(handles=EPOCH_KEY, loc='lower center', ncol=6, title='Year of the traced outline'))
for sid in ORDER:                                                        # supplementary: every site
    fig, ax = plt.subplots(figsize=(ONE * MM, 80 * MM))
    h = draw_outlines(ax, sid, legend_areas=True)
    ax.legend(handles=h, loc='upper left', bbox_to_anchor=(1.0, 1.0), title='Year: traced area')
    ax.set_title(LAB[sid], loc='left', fontweight='bold')
    fig.tight_layout(pad=0.4); fig.savefig(os.path.join(OUT, 'supplementary', f'SupplFig_{sid}_outlines.pdf'))
    fig.savefig(os.path.join(OUT, 'supplementary', f'SupplFig_{sid}_outlines.png'), dpi=300); plt.close(fig)
print('saved supplementary outline maps (14)')

# ---------- Fig7 land turnover ----------
def p_turn(ax):
    d = sorted(S, key=lambda s: s['newly_covered_since_2016_ha'] - s['no_longer_waste_2026_ha']); yy = np.arange(len(d))
    ax.barh(yy, [s['newly_covered_since_2016_ha'] for s in d], color=NEW, height=0.6)
    ax.barh(yy, [-s['no_longer_waste_2026_ha'] for s in d], color=GONE, height=0.6)
    for i, s in enumerate(d):
        a, b = s['newly_covered_since_2016_ha'], s['no_longer_waste_2026_ha']
        if a > 0.05: ax.text(a + 0.8, i, f'+{a:.1f}', va='center')
        if b > 0.05: ax.text(-b - 0.8, i, f'−{b:.1f}', va='center', ha='right')
    ax.set_yticks(yy); ax.set_yticklabels([LAB[s['site_id']] for s in d]); ax.tick_params(axis='y', length=0)
    ax.axvline(0, color=AXIS, lw=0.5); grid(ax, 'x'); ax.set_xlim(-90, 35)
    ax.set_xlabel('Land area, 2016–2026 (ha)')
    tn = sum(s['newly_covered_since_2016_ha'] for s in S); tg = sum(s['no_longer_waste_2026_ha'] for s in S)
    ax.legend(handles=[Patch(color=NEW, label=f'Newly under waste since 2016 (total {tn:.0f} ha)'),
                       Patch(color=GONE, label=f'Under waste in an earlier year, not in 2026 (total {tg:.0f} ha)')],
              loc='lower left', bbox_to_anchor=(0, 1.0))
figure('Fig7', ONE + 30, 90, [p_turn])

# ---------- dumbbell helper (Fig8 compactness, Fig10 city totals) ----------
def dumbbell(ax, items, xlab, xlim, fmt=None):
    yy = np.arange(len(items))
    for i, (lab, a, b) in enumerate(items):
        ax.plot([a, b], [i, i], color=GRID, lw=2.0, zorder=1, solid_capstyle='butt')
        ax.scatter(a, i, s=16, color=Y16, edgecolor='white', lw=0.4, zorder=3); ax.scatter(b, i, s=16, color=Y26, edgecolor='white', lw=0.4, zorder=3)
        if fmt: ax.text(max(a, b) + 0.015 * (xlim[1] - xlim[0]) + 0.6 * (xlim[1] - xlim[0]) / 100, i, fmt(i), va='center')
    ax.set_yticks(yy); ax.set_yticklabels([t[0] for t in items]); ax.tick_params(axis='y', length=0)
    ax.set_xlim(*xlim); ax.set_ylim(-0.7, len(items) - 0.3); grid(ax, 'x'); ax.set_xlabel(xlab)
    ax.legend(handles=[Line2D([], [], marker='o', ls='', color=Y16, ms=4, label='2016'), Line2D([], [], marker='o', ls='', color=Y26, ms=4, label='2026')],
              loc='lower left', bbox_to_anchor=(0, 1.0), ncol=2)

# ---------- Fig8 compactness ----------
def p_comp(ax):
    d = sorted(S, key=lambda s: s['compactness_2026'] - s['compactness_2016'])
    dumbbell(ax, [(LAB[s['site_id']] + (f" ({s['n_parts_max']} parts)" if s['n_parts_max'] > 1 else ''), s['compactness_2016'], s['compactness_2026']) for s in d],
             r'Compactness, 4π$\mathit{A}$/$\mathit{P}^{2}$ (1 = circle; lower = more irregular)', (0, 0.9))
figure('Fig8', ONE + 30, 85, [p_comp])

# ---------- Fig9 sites traced in parts ----------
def p_parts(sid):
    def f(ax):
        prs = [p for p in R['parts'] if p['site_id'] == sid]; keys = [k for k in ['main', 'a', 'b', 'c', 'a+b'] if any(p['part'] == k for p in prs)]
        bottom = np.zeros(len(EP)); top = 0
        tot = np.array([sum(p['area_ha'] for p in prs if p['epoch'] == e) for e in EP]); top = tot.max()
        for k in keys:
            v = np.array([sum(p['area_ha'] for p in prs if p['part'] == k and p['epoch'] == e) for e in EP])
            ax.bar(range(len(EP)), v, bottom=bottom, color=PARTC[k], width=0.62, edgecolor='white', lw=0.8, label=PARTL[k])
            for i in range(len(EP)):                                     # part letter inside the segment (secondary encoding; old dump = the only purple)
                if v[i] > 0.09 * top and k != 'main': ax.text(i, bottom[i] + v[i] / 2, PARTL[k], ha='center', va='center', color='white')
            bottom += v
        for i, t in enumerate(bottom): ax.text(i, t + top * 0.02, f'{t:.1f}', ha='center')
        ax.set_xticks(range(len(EP))); ax.set_xticklabels(EP); ax.set_xlabel('Year')
        ax.set_title(LAB[sid], loc='left'); ax.set_ylabel('Traced waste area (ha)'); grid(ax); ax.set_ylim(0, top * 1.15)
        ax.legend(loc='upper right', title='Part', handlelength=1, handleheight=1)
    return f
figure('Fig9', TWO, 70, [p_parts(s) for s in ['SUR-02', 'VAD-02', 'AHM-02']])

# ---------- Fig10 city totals ----------
def p_city(ax):
    C = sorted(R['cities'], key=lambda c: c['net_change_ha'])
    dumbbell(ax, [(f"{c['city']} ({c['n_sites']})", c['2016'], c['2026']) for c in C], 'Total traced waste area in the city (ha)', (0, 100),
             fmt=lambda i: f"{C[i]['2016']:.1f} → {C[i]['2026']:.1f} ha ({pm(C[i]['net_change_pct'], '.0f')}%)")
figure('Fig10', ONE + 30, 80, [p_city])

# ---------- caption notes ----------
open(os.path.join(OUT, 'caption_notes.md'), 'w', encoding='utf-8').write('''# Caption notes for the version-2 figures (write the final captions in your own words)

Figures have no titles inside the artwork (Nature Reviews style); each needs a caption. Facts each caption should carry:

| File | Content | Must mention |
|---|---|---|
| Fig1 | Study area map, 14 sites in 10 cities | Marker area = traced waste area in 2026; boundary source DataMeet India maps; number of sites in brackets |
| Fig2 a, b | Total traced area per city group; same as index (2016 = 100) | Line ends are labelled directly; dashed = all 14 sites; dotted = five most populous cities without Surat 2 (Khajod) |
| Fig3 a, b | Area (ha) and perimeter (km) per site and year | Shading = value as % of that site's own maximum (compare rows, not columns); perimeter after 5 m simplification; blue/orange bar = city group |
| Fig4 | Net change 2016–2026 per site | Colour = city group |
| Fig5 | Largest area ÷ 2016 area vs change from largest area to 2026 | Dashed lines = 15% threshold (class threshold is higher for Surat 1 (Bhatar) 20%, Vapi 21%, Vadodara 2 26%) |
| Fig6 a–f | Traced outlines of six case-study sites | Grey ramp light = 2016 to black = 2026; scale bar per panel; all 14 sites in Supplementary |
| Fig7 | Land turnover per site | Newly under waste = 2026 outline minus 2016 outline; not in 2026 = union of all outlines minus 2026 outline |
| Fig8 | Compactness 2016 vs 2026 | 4πA/P², A area, P perimeter |
| Fig9 a–c | Area of each traced part | Letters in the bars = part; number on top = site total |
| Fig10 | City totals 2016 vs 2026 | Number of sites in brackets |
| Table 1 | tables_v2/table1_site_summary.csv | Theil–Sen slope; Mann–Kendall exact P with n = 6 (descriptive) |
''')
print('saved caption_notes.md')
