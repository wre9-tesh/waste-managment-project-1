"""
Step 03 (version 2) - the siting figures redrawn to the Nature Reviews artwork guide.
Reads the step-02 outputs (outputs/tables/*.csv, outputs/sites/<SITE>/<SITE>_layers.geojson); numbers are unchanged.
Writes figures_v2/ : FigS1 ... FigS6 as PDF (vector, editable text) + 300 dpi PNG, and figures_v2/panels/ (each panel alone).

How the guide is applied
  - Vector PDF for every figure; TrueType fonts embedded so text stays editable.
  - All text 8 pt; bold only for panel letters; no titles inside the artwork (titles go in the caption).
  - Size: portrait figures within 180 mm x 215 mm (checked on save). FigS5 is landscape on request
    (within 215 mm x 180 mm, i.e. the same page turned); it has 14 map panels, more than the guide's six,
    so every map is also saved as its own file in panels/.
  - Units on every axis; site names without abbreviations ('Vadodara 1', not 'VAD-01 Vadodara LF-1');
    rule names in words ('National or state highway', not 'NH / SH'; 'Coastal regulation zone', not 'CRZ').
  - Colours only for meaning and the same everywhere: breach = red, conditional or to check = amber,
    meets the rule = green, each also marked with a symbol (✘ ? ✔) so the grid is readable without colour;
    2016 vs 2026 = light grey vs black, as in the footprint figures (figures_v2/ of the main analysis).
  - FigS5 maps: satellite imagery is added when the Esri tiles can be downloaded (a bitmap layer under
    vector features, scale bar and labels, as the guide asks); otherwise the maps are drawn vector-only.
  - CMYK: matplotlib writes RGB; convert if requested, e.g.
        gs -o FigS1_cmyk.pdf -sDEVICE=pdfwrite -sColorConversionStrategy=CMYK FigS1.pdf
Run:  python 03_figures_v2.py            (after 02_siting_check.py)
      python 03_figures_v2.py --no-imagery
"""
import os, sys
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle
from matplotlib.lines import Line2D
import config as C

OUT = os.path.join(C.ROOT, "figures_v2")
os.makedirs(os.path.join(OUT, "panels"), exist_ok=True)
MM = 1 / 25.4
IMAGERY = "--no-imagery" not in sys.argv

# ---------------- house style (same as scripts/final_figures_v2.py of the area analysis) ----------------
INK, INK2, GRID, AXIS = "#1a1a1a", "#4d4d4d", "#e3e3e3", "#8c8c8c"
Y16, Y26 = "#c9c9c9", "#111111"
STATUS = {"breach": "#c0392b", "conditional": "#e0a100", "check": "#e0a100", "ok": "#2e8b57", "not assessable": "#d9d9d9"}
STATUS_TXT = {"breach": "#ffffff", "conditional": INK, "check": INK, "ok": "#ffffff", "not assessable": INK2}
SYM = {"breach": "✘", "conditional": "?", "check": "?", "ok": "✔", "not assessable": "–"}
plt.rcParams.update({
    "font.family": ["Arial", "Liberation Sans", "DejaVu Sans"],          # DejaVu supplies ✘ ✔ if the main font lacks them
    "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "legend.fontsize": 8, "legend.title_fontsize": 8, "axes.titleweight": "normal",
    "mathtext.default": "regular", "mathtext.fontset": "custom", "mathtext.bf": "sans:bold", "mathtext.rm": "sans", "mathtext.it": "sans:italic", "mathtext.cal": "sans", "pdf.fonttype": 42, "ps.fonttype": 42,
    "axes.linewidth": 0.5, "xtick.major.width": 0.5, "ytick.major.width": 0.5, "xtick.major.size": 2.5, "ytick.major.size": 2.5,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white"})

LAB = {"AHM-01": "Ahmedabad 1 (Pirana)", "AHM-02": "Ahmedabad 2", "AHM-03": "Ahmedabad 3", "BHJ-01": "Bhuj",
       "BHV-01": "Bhavnagar", "GNR-01": "Gandhinagar", "JAM-01": "Jamnagar", "MEH-01": "Mehsana", "RAJ-01": "Rajkot",
       "SUR-01": "Surat 1 (Bhatar)", "SUR-02": "Surat 2 (Khajod)", "VAD-01": "Vadodara 1", "VAD-02": "Vadodara 2 (Atladara)",
       "VAP-01": "Vapi"}
RULE = {"R1": "River", "R2": "Pond", "R3": "National or state highway", "R4": "Habitation", "R5": "Public park",
        "R6": "Water-supply well", "R7": "Airport or airbase", "R8": "Flood plain (100-year)", "R9": "Coastal regulation zone",
        "R10": "Wetland", "R11": "Critical habitat or eco-fragile area", "R12": "Town-planning land-use plan"}
LIMIT = {"R1": "≥ 100 m", "R2": "≥ 200 m", "R3": "≥ 200 m", "R4": "≥ 200 m", "R5": "≥ 200 m", "R7": "≥ 20 km",
         "R8": "outside", "R9": "outside", "R10": "outside", "R11": "outside"}
UNIT = {"R1": "m", "R2": "m", "R3": "m", "R4": "buildings", "R5": "m", "R7": "km", "R8": "% of outline",
        "R9": "m", "R10": "m", "R11": "km"}
SCORED = [r["id"] for r in C.RULES if r["kind"] != "na"]

long = pd.read_csv(os.path.join(C.TABLES, "siting_long.csv"))
m26 = pd.read_csv(os.path.join(C.TABLES, "siting_matrix_2026.csv"), index_col="site")
m16 = pd.read_csv(os.path.join(C.TABLES, "siting_matrix_2016.csv"), index_col="site")
near = pd.read_csv(os.path.join(C.TABLES, "nearest_features_2026.csv")).set_index("site")
L26 = long[long.epoch == C.MAIN_EPOCH].set_index(["site", "rule_id"])
ORDER = m26.sort_values(["breaches", "conditional_or_check"], ascending=[False, False]).index.tolist()
RULE_NAMES = {r["id"]: r["rule"] for r in C.RULES}
names_of = lambda s: [] if pd.isna(s) or not s else [x.strip() for x in s.split(",")]
RID_OF = {}                                  # 'Highway (NH / SH)' -> 'R3', to rename the rule lists of the summary table
for r in C.RULES: RID_OF[r["rule"]] = r["id"]


def letter(ax, l, x=-0.02, y=1.02):
    ax.text(x, y, l, transform=ax.transAxes, fontweight="bold", ha="right", va="bottom")


def save(fig, name, maxw=180, maxh=215):
    kw = dict(bbox_inches="tight", pad_inches=0.03)
    bb = fig.get_tightbbox(fig.canvas.get_renderer())
    w, h = (bb.width + 0.06) * 25.4, (bb.height + 0.06) * 25.4
    assert w <= maxw + 0.5 and h <= maxh + 0.5, f"{name}: {w:.0f} x {h:.0f} mm exceeds {maxw} x {maxh} mm"
    fig.savefig(os.path.join(OUT, name + ".pdf"), **kw)
    fig.savefig(os.path.join(OUT, name + ".png"), dpi=300, **kw)
    plt.close(fig); print(f"saved {name}  ({w:.0f} x {h:.0f} mm)")


def save_panel(draw, name, w_mm, h_mm):
    f, ax = plt.subplots(figsize=(w_mm * MM, h_mm * MM)); draw(ax); f.tight_layout(pad=0.4)
    f.savefig(os.path.join(OUT, "panels", name + ".pdf"), bbox_inches="tight", pad_inches=0.03); plt.close(f)


def value_text(s, rid):
    r = L26.loc[(s, rid)]; v = r["value"]
    if r["verdict"] == "not assessable": return SYM[r["verdict"]]
    if rid == "R4": return f"{SYM[r['verdict']]} {int(r['n_within_limit'])}"
    if pd.isna(v) or (UNIT[rid] == "m" and v >= 2500): return f"{SYM[r['verdict']]} >2.5k"
    if UNIT[rid] == "km": return f"{SYM[r['verdict']]} {v:.1f}"
    if UNIT[rid].startswith("%"): return f"{SYM[r['verdict']]} {v:.0f}"
    return f"{SYM[r['verdict']]} {v:.0f}"


STATUS_KEY = [Patch(color=STATUS["breach"], label="✘  breach"),
              Patch(color=STATUS["conditional"], label="?  conditional (airport 10–20 km, needs a no-objection certificate) or to check"),
              Patch(color=STATUS["ok"], label="✔  meets the rule")]


# ---------------- FigS1 verdict matrix ----------------
def p_matrix(ax):
    nr, nc = len(ORDER), len(SCORED)
    for i, s in enumerate(ORDER):
        for j, rid in enumerate(SCORED):
            v = L26.loc[(s, rid)]["verdict"]
            ax.add_patch(Rectangle((j + 0.04, nr - i - 1 + 0.06), 0.92, 0.88, color=STATUS[v], lw=0))
            ax.text(j + 0.5, nr - i - 0.5, value_text(s, rid), ha="center", va="center", color=STATUS_TXT[v])
        ax.text(nc + 0.25, nr - i - 0.5, f"{int(m26.loc[s, 'breaches'])}", ha="left", va="center")
        ax.text(-0.12, nr - i - 0.5, LAB[s], ha="right", va="center")
    for j, rid in enumerate(SCORED):
        ax.text(j + 0.5, nr + 0.12, f"{RULE[rid]}\n{LIMIT[rid]}\n({UNIT[rid]})", ha="center", va="bottom", rotation=90,
                linespacing=1.15)
    ax.text(nc + 0.25, nr + 0.12, "Rules\nbreached\n(of 10)", ha="left", va="bottom", rotation=90, linespacing=1.15)
    ax.set_xlim(-0.05, nc + 1.0); ax.set_ylim(0, nr); ax.axis("off")
    ax.legend(handles=STATUS_KEY, loc="upper left", bbox_to_anchor=(-0.22, -0.01), ncol=1, handlelength=1.2)


def fig_s1():
    fig, ax = plt.subplots(figsize=(178 * MM, 150 * MM)); p_matrix(ax)
    fig.subplots_adjust(left=0.20, right=0.97, top=0.72, bottom=0.12); save(fig, "FigS1")


# ---------------- FigS2 rules breached per site ----------------
def p_per_site(ax):
    d = m26.loc[ORDER[::-1]]; y = np.arange(len(d))
    ax.barh(y, d["breaches"], color=STATUS["breach"], height=0.62, edgecolor="white", lw=0.8)
    ax.barh(y, d["conditional_or_check"], left=d["breaches"], color=STATUS["conditional"], height=0.62, edgecolor="white", lw=0.8)
    for yi, (b, c, rules) in enumerate(zip(d["breaches"], d["conditional_or_check"], d["breached_rules"])):
        txt = ", ".join(RULE[RID_OF[n]] for n in names_of(rules))
        ax.text(b + c + 0.15, yi, f"{b}" + (f" (+{c})" if c else "") + (f"   {txt}" if txt else ""), va="center", color=INK2)
    ax.set_yticks(y); ax.set_yticklabels([LAB[s] for s in d.index]); ax.tick_params(axis="y", length=0)
    ax.set_xlim(0, 10); ax.set_xticks(range(0, 11)); ax.grid(axis="x", color=GRID, lw=0.5); ax.set_axisbelow(True)
    ax.set_xlabel("Number of siting rules (of 10 assessable)")
    ax.legend(handles=[Patch(color=STATUS["breach"], label="Breached"),
                       Patch(color=STATUS["conditional"], label="Conditional or to check (number in brackets)")],
              loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2)


def fig_s2():
    fig, ax = plt.subplots(figsize=(150 * MM, 95 * MM)); p_per_site(ax); fig.tight_layout(pad=0.4); save(fig, "FigS2")


# ---------------- FigS3 sites per rule ----------------
def p_per_rule(ax):
    rid = SCORED[::-1]; y = np.arange(len(rid))
    nb = [(m26[r] == "breach").sum() for r in rid]; nc = [m26[r].isin(["conditional", "check"]).sum() for r in rid]
    ax.barh(y, nb, color=STATUS["breach"], height=0.6, edgecolor="white", lw=0.8)
    ax.barh(y, nc, left=nb, color=STATUS["conditional"], height=0.6, edgecolor="white", lw=0.8)
    for yi, (b, c) in enumerate(zip(nb, nc)):
        ax.text(b + c + 0.2, yi, f"{b}" + (f" (+{c})" if c else ""), va="center", color=INK2)
    ax.set_yticks(y); ax.set_yticklabels([f"{RULE[r]} ({LIMIT[r]})" for r in rid]); ax.tick_params(axis="y", length=0)
    ax.set_xlim(0, 15); ax.set_xticks(range(0, 15, 2)); ax.grid(axis="x", color=GRID, lw=0.5); ax.set_axisbelow(True)
    ax.set_xlabel("Number of dumpsites (of 14)")
    ax.legend(handles=[Patch(color=STATUS["breach"], label="Breached"), Patch(color=STATUS["conditional"], label="Conditional or to check")],
              loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2)


def fig_s3():
    fig, ax = plt.subplots(figsize=(130 * MM, 75 * MM)); p_per_rule(ax); fig.tight_layout(pad=0.4); save(fig, "FigS3")


# ---------------- FigS4 measured value vs limit (six panels) ----------------
S4 = [("river_m", "R1", "Distance to nearest river (m)", 100, 1000), ("pond_m", "R2", "Distance to nearest pond (m)", 200, 1000),
      ("highway_m", "R3", "Distance to nearest national or\nstate highway (m)", 200, 1000),
      ("buildings_within_200m", "R4", "Residential buildings within 200 m\n(number)", 5, 400),
      ("park_m", "R5", "Distance to nearest public park (m)", 200, 1000),
      ("airport_km", "R7", "Distance to nearest airport or\nairbase reference point (km)", 20, 30)]


def p_dist(col, rid, lab, lim, cap, show_y):
    def draw(ax):
        nd = near.loc[ORDER[::-1]]; y = np.arange(len(nd)); v = nd[col].astype(float); count = col == "buildings_within_200m"
        vv = v.fillna(np.inf).clip(upper=cap)
        if count: ax.axvspan(lim, cap * 1.35, color=STATUS["breach"], alpha=0.12, lw=0)
        else: ax.axvspan(0, lim, color=STATUS["breach"], alpha=0.12, lw=0)
        if rid == "R7":
            ax.axvspan(10, 20, color=STATUS["conditional"], alpha=0.15, lw=0); ax.axvspan(0, 10, color=STATUS["breach"], alpha=0.12, lw=0)
        ax.axvline(lim, color=STATUS["breach"], lw=0.8)
        cols = [STATUS[L26.loc[(s, rid)]["verdict"]] for s in nd.index]
        ax.scatter(vv, y, s=12, c=cols, zorder=3, edgecolor="white", lw=0.4)
        for yi, (x, raw) in enumerate(zip(vv, v)):
            t = ">2500" if not np.isfinite(raw) else (f">{cap}" if raw > cap else (f"{raw:.1f}" if rid == "R7" else f"{raw:,.0f}"))
            ax.text(min(x, cap) + cap * 0.04, yi, t, va="center", color=INK2)
        ax.set_xlim(0, cap * 1.35); ax.set_ylim(-0.7, len(nd) - 0.3); ax.set_xlabel(lab)
        ax.grid(axis="x", color=GRID, lw=0.5); ax.set_axisbelow(True)
        ax.set_yticks(y); ax.set_yticklabels([LAB[s] for s in nd.index] if show_y else []); ax.tick_params(axis="y", length=0)
    return draw


def fig_s4():
    fig, axs = plt.subplots(2, 3, figsize=(180 * MM, 175 * MM)); axs = axs.ravel()
    for i, (ax, p) in enumerate(zip(axs, S4)):
        p_dist(*p, show_y=(i % 3 == 0))(ax); letter(ax, "abcdef"[i])
    fig.legend(handles=[Patch(color=STATUS["breach"], alpha=0.25, label="Breach zone (shaded) and limit (line)"),
                        Patch(color=STATUS["conditional"], alpha=0.3, label="Airport 10–20 km: allowed only with a no-objection certificate"),
                        Line2D([], [], marker="o", ls="", color=STATUS["breach"], ms=4, label="Breach"),
                        Line2D([], [], marker="o", ls="", color=STATUS["conditional"], ms=4, label="Conditional or to check"),
                        Line2D([], [], marker="o", ls="", color=STATUS["ok"], ms=4, label="Meets the rule")],
               loc="lower center", ncol=3)
    fig.tight_layout(pad=0.4, rect=(0, 0.07, 1, 1)); save(fig, "FigS4")
    for i, p in enumerate(S4): save_panel(p_dist(*p, show_y=True), f"FigS4{'abcdef'[i]}", 90, 85)


# ---------------- FigS5 site maps (landscape) ----------------
VEC = dict(outline="#1a1a1a", ring="#6e6e6e", bar="#1a1a1a", bg="#f7f7f5")
IMG = dict(outline="#fab219", ring="#ffffff", bar="#ffffff", bg="#ffffff")
STY = {  # layer: (face, edge, linewidth, alpha, zorder)
    "flood_100yr": ("#3987e5", "#3987e5", 0.0, 0.25, 2), "wetland": ("none", "#9085e9", 0.8, 1.0, 3),
    "tidal": ("none", "#e87ba4", 0.8, 1.0, 3), "coastline": ("none", "#e87ba4", 1.0, 1.0, 3),
    "park": ("#1baf7a", "#1baf7a", 0.5, 0.45, 3), "pond": ("#5ab4e6", "#5ab4e6", 0.5, 0.8, 4),
    "river": ("#2f7fc1", "#2f7fc1", 1.2, 0.9, 4), "stream_canal": ("none", "#9ec5f4", 0.5, 0.8, 3),
    "highway": ("none", "#eb6834", 1.2, 1.0, 5)}


def site_map(ax, s, imagery, tag=""):
    g = gpd.read_file(os.path.join(C.SITES_OUT, s, f"{s}_layers.geojson")).to_crs(3857)
    P = IMG if imagery else VEC
    out = g[g.layer == "outline_2026"]; x0, y0, x1, y1 = out.total_bounds
    half = max(x1 - x0, y1 - y0) / 2 + max(450, 0.25 * max(x1 - x0, y1 - y0))
    cx0, cy0 = (x0 + x1) / 2, (y0 + y1) / 2
    ax.set_xlim(cx0 - half, cx0 + half); ax.set_ylim(cy0 - half, cy0 + half); ax.set_facecolor(P["bg"])
    if imagery:
        import contextily as cx
        cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, attribution=False, zoom="auto")
    for lay in ("flood_100yr", "park", "pond", "wetland", "tidal", "coastline", "stream_canal", "river", "highway"):
        sub = g[g.layer == lay]
        if not len(sub): continue
        fc, ec, lw, a, z = STY[lay]
        poly = sub[sub.geom_type.isin(["Polygon", "MultiPolygon"])]; line = sub[sub.geom_type.isin(["LineString", "MultiLineString"])]
        if len(poly): poly.plot(ax=ax, facecolor=fc, edgecolor=ec, linewidth=min(lw, 0.5), alpha=a, zorder=z)
        if len(line): line.plot(ax=ax, color=ec, linewidth=lw, alpha=max(a, 0.9), zorder=z)
    b = g[g.layer == "building"]
    if len(b):
        ind = b.in_industrial_zone.astype(bool); near_ = b[~ind & (b.distance_m < 200)]
        far = b[~ind & (b.distance_m >= 200)]
        if len(far): far.plot(ax=ax, facecolor="none", edgecolor="#b3b3b3" if not imagery else "#fcfcfb", linewidth=0.2, zorder=5)
        if ind.any(): b[ind & (b.distance_m < 500)].plot(ax=ax, facecolor="none", edgecolor="#b07d00", linewidth=0.3, zorder=5)
        oth = near_[near_.ghsl_2018 != 1]; cnt = near_[near_.ghsl_2018 == 1]
        if len(oth): oth.plot(ax=ax, facecolor="none", edgecolor=STATUS["breach"], linewidth=0.4, zorder=6)
        if len(cnt): cnt.plot(ax=ax, facecolor=STATUS["breach"], edgecolor=STATUS["breach"], linewidth=0.3, zorder=6)
    for k, ls in ((100, (0, (4, 3))), (200, (0, (1.2, 1.8)))):
        rb = g[g.layer == f"buffer_{k}m"]
        if len(rb): rb.boundary.plot(ax=ax, color=P["ring"], linewidth=0.6, linestyle=ls, zorder=7)
    out.plot(ax=ax, facecolor="none", edgecolor=P["outline"], linewidth=1.2, zorder=8)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values(): sp.set_visible(True); sp.set_edgecolor(AXIS); sp.set_linewidth(0.5)
    b_, c_ = int(m26.loc[s, "breaches"]), int(m26.loc[s, "conditional_or_check"])
    ax.set_title((f"$\\bf{{{tag}}}$  " if tag else "") + f"{LAB[s].split(' (')[0]}\n{b_} breached" + (f", {c_} to check" if c_ else ""), loc="left", pad=2, linespacing=1.1)
    lat = float(np.mean(gpd.read_file(os.path.join(C.SITES_OUT, s, f"{s}_layers.geojson")).query("layer == 'outline_2026'").total_bounds[[1, 3]]))
    sx, sy = cx0 - half + 0.08 * half, cy0 - half + 0.1 * half
    ax.plot([sx, sx + 200 / np.cos(np.radians(lat))], [sy, sy], color=P["bar"], lw=1.5, zorder=9, solid_capstyle="butt")
    ax.text(sx, sy + 0.05 * half, "200 m", color=P["bar"], zorder=9)          # web-Mercator metres stretched by 1/cos(lat)


def map_key(imagery):
    P = IMG if imagery else VEC
    return [Line2D([], [], color=P["outline"], lw=1.2, label="Dumpsite outline, 2026"),
            Line2D([], [], color=VEC["ring"], lw=0.6, ls=(0, (4, 3)), label="100 m from outline"),
            Line2D([], [], color=VEC["ring"], lw=0.6, ls=(0, (1.2, 1.8)), label="200 m from outline"),
            Patch(color=STATUS["breach"], label="Residential building within 200 m (counted)"),
            Patch(facecolor="none", edgecolor=STATUS["breach"], label="Other building within 200 m"),
            Patch(facecolor="none", edgecolor="#b07d00", label="Building on industrial or plant land"),
            Line2D([], [], color=STY["river"][1], lw=1.2, label="River"), Patch(color=STY["pond"][0], label="Pond or lake"),
            Line2D([], [], color=STY["highway"][1], lw=1.2, label="National, state or major road"),
            Patch(color=STY["park"][0], alpha=0.6, label="Public park"),
            Patch(color=STY["flood_100yr"][0], alpha=0.35, label="100-year flood extent (JRC)")]


def fig_s5():
    imagery = IMAGERY
    sites = sorted(m26.index)
    def build(img):
        fig, axs = plt.subplots(2, 7, figsize=(210 * MM, 102 * MM)); axs = axs.ravel()
        for i, (ax, s) in enumerate(zip(axs, sites)):
            site_map(ax, s, img, tag="abcdefghijklmn"[i])
        fig.legend(handles=map_key(img), loc="lower center", ncol=4, handlelength=1.6, columnspacing=1.2)
        fig.tight_layout(pad=0.3, w_pad=0.4, h_pad=0.6, rect=(0, 0.15, 1, 1)); return fig
    try:
        fig = build(imagery)
    except Exception as e:                       # no internet / tiles blocked -> vector-only maps
        print("  imagery not available, drawing vector-only maps:", type(e).__name__); plt.close("all"); imagery = False
        fig = build(False)
    save(fig, "FigS5", maxw=215, maxh=180)
    for s in sites:
        f, ax = plt.subplots(figsize=(80 * MM, 80 * MM)); site_map(ax, s, imagery)
        f.savefig(os.path.join(OUT, "panels", f"FigS5_{s}.pdf"), bbox_inches="tight", pad_inches=0.03); plt.close(f)
    return imagery


# ---------------- FigS6 2016 vs 2026 ----------------
def p_epochs(ax):
    d = pd.DataFrame(dict(b16=m16["breaches"], b26=m26["breaches"])).loc[ORDER[::-1]]; y = np.arange(len(d))
    for yi, (a, b) in enumerate(zip(d.b16, d.b26)):
        ax.plot([a, b], [yi, yi], color=GRID, lw=2.0, zorder=1, solid_capstyle="butt")
        if a != b: ax.text(max(a, b) + 0.3, yi, f"{a} → {b}", va="center", color=INK2)
    ax.scatter(d.b16, y, s=16, color=Y16, zorder=2, edgecolor="white", lw=0.4)
    ax.scatter(d.b26, y, s=16, color=Y26, zorder=3, edgecolor="white", lw=0.4)
    ax.set_yticks(y); ax.set_yticklabels([LAB[s] for s in d.index]); ax.tick_params(axis="y", length=0)
    ax.set_xlim(-0.3, 10); ax.set_xticks(range(0, 11)); ax.grid(axis="x", color=GRID, lw=0.5); ax.set_axisbelow(True)
    ax.set_xlabel("Number of siting rules breached (of 10)")
    ax.legend(handles=[Line2D([], [], marker="o", ls="", color=Y16, ms=4, label="2016 outline"),
                       Line2D([], [], marker="o", ls="", color=Y26, ms=4, label="2026 outline")], loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2)


def fig_s6():
    fig, ax = plt.subplots(figsize=(120 * MM, 85 * MM)); p_epochs(ax); fig.tight_layout(pad=0.4); save(fig, "FigS6")


if __name__ == "__main__":
    fig_s1(); fig_s2(); fig_s3(); fig_s4()
    used = fig_s5(); fig_s6()
    open(os.path.join(OUT, "caption_notes.md"), "w", encoding="utf-8").write(f"""# Caption notes, siting figures version 2 (write the captions in your own words)

No titles inside the figures; each caption should carry:

| Figure | Content | Must mention |
|---|---|---|
| FigS1 | Verdict per site and rule, 2026 outline | SWM Rules 2026 (S.O. 388(E)), Schedule II(A)(vii); numbers = measured value in the unit under each rule; water-supply wells and land-use plan not assessable (not shown) |
| FigS2 | Rules breached per site | Amber = conditional (airport 10–20 km) or to check (habitation, eco-sensitive zone); rule names beside the bars |
| FigS3 | Sites breaching each rule | Of 14 sites |
| FigS4 a–f | Measured value vs legal limit | Shaded = breach zone; values above the axis end shown as '>'; >2500 = no feature within the 2.5 km search radius |
| FigS5 a–n | Site maps with the 100 m and 200 m rings | {'Imagery: Esri World Imagery (Maxar, Earthstar Geographics)' if used else 'Vector map (no imagery); run on a computer with internet access to add Esri World Imagery'}; OpenStreetMap contributors (ODbL); Overture Maps buildings; JRC flood hazard map |
| FigS6 | Breaches with the 2016 vs 2026 outline | Same 2026 feature data for both outlines |
""")
    print("saved caption_notes.md")
