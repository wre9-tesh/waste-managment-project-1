"""
Step 03 - figures and the results workbook (reads outputs/tables/*.csv and outputs/sites/*/<SITE>_layers.geojson
written by step 02).

Figures (figures/, 200 dpi PNG):
  figS1_compliance_matrix_2026.png   site x rule grid: verdict + measured distance / overlap, 2026 outlines
  figS2_breaches_per_site.png        number of rules breached per site (definite + conditional/check)
  figS3_sites_per_rule.png           number of sites breaching each rule
  figS4_distance_vs_limit.png        measured distance vs the legal minimum, six distance rules
  figS5_site_maps.png                14 site maps on satellite imagery (landscape, 3 x 5): outline, 100/200 m rings, features
  figS6_2016_vs_2026.png             breaches with the 2016 outline vs the 2026 outline
  outputs/sites/<SITE>/<SITE>_siting_map.png   one larger map per site
Workbook: outputs/tables/siting_results.xlsx (all tables + rules + data sources)
KML for Google Earth Pro: outputs/siting_check_layers.kml

Run:  python 03_figures_tables.py
      python 03_figures_tables.py --s5-from-site-maps   (offline: re-tile figS5 from the per-site maps)
"""
import json, os, html
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle
from matplotlib.lines import Line2D
import config as C
import outlines as O

INK, INK2, MUTED, GRID, BG = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#ffffff"
STATUS = {"breach": "#d03b3b", "conditional": "#fab219", "check": "#fab219", "ok": "#0ca30c", "not assessable": "#d9d8d2"}
STATUS_TXT = {"breach": "#ffffff", "conditional": INK, "check": INK, "ok": "#ffffff", "not assessable": INK2}
SYM = {"breach": "✘", "conditional": "?", "check": "?", "ok": "✔", "not assessable": "n/a"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK,
                     "xtick.color": INK2, "ytick.color": INK2, "figure.facecolor": BG, "axes.facecolor": BG})
SHORT = {"AHM-01": "Ahmedabad LF-1 (Pirana)", "AHM-02": "Ahmedabad LF-2", "AHM-03": "Ahmedabad LF-3", "BHJ-01": "Bhuj LF-1",
         "BHV-01": "Bhavnagar LF-1", "GNR-01": "Gandhinagar LF-1", "JAM-01": "Jamnagar LF-1", "MEH-01": "Mehsana LF-1",
         "RAJ-01": "Rajkot LF-1", "SUR-01": "Surat LF-1 (Bhatar)", "SUR-02": "Surat LF-2 (Khajod)", "VAD-01": "Vadodara LF-1",
         "VAD-02": "Vadodara LF-2 (Atladara)", "VAP-01": "Vapi LF-1"}
RSHORT = {"R1": "River\n100 m", "R2": "Pond\n200 m", "R3": "Highway\n200 m", "R4": "Habitation\n200 m", "R5": "Public park\n200 m",
          "R6": "Water-supply\nwell 200 m", "R7": "Airport /\nairbase 20 km", "R8": "Flood plain\n(100-yr)",
          "R9": "CRZ\n(screening)", "R10": "Wetland", "R11": "Critical habitat /\neco-fragile", "R12": "Land-use\nplan"}
HDR = {"R1": "River\n100 m", "R2": "Pond\n200 m", "R3": "Highway\nNH / SH\n200 m", "R4": "Habitation\n200 m",
       "R5": "Public\npark\n200 m", "R6": "Water-\nsupply\nwell 200 m", "R7": "Airport /\nairbase\n20 km",
       "R8": "Flood\nplain\n100-yr", "R9": "CRZ\n(screen-\ning)", "R10": "Wetland", "R11": "Critical\nhabitat /\neco-fragile",
       "R12": "In land-\nuse plan"}
RULE_IDS = [r["id"] for r in C.RULES]
SCORED = [r["id"] for r in C.RULES if r["kind"] != "na"]
os.makedirs(C.FIG, exist_ok=True)

long = pd.read_csv(os.path.join(C.TABLES, "siting_long.csv"))
m26 = pd.read_csv(os.path.join(C.TABLES, "siting_matrix_2026.csv"), index_col="site")
m16 = pd.read_csv(os.path.join(C.TABLES, "siting_matrix_2016.csv"), index_col="site")
summ = pd.read_csv(os.path.join(C.TABLES, "siting_summary.csv"), index_col=0)
near = pd.read_csv(os.path.join(C.TABLES, "nearest_features_2026.csv"))
hab = pd.read_csv(os.path.join(C.TABLES, "habitation_detail.csv"))
L26 = long[long.epoch == C.MAIN_EPOCH].set_index(["site", "rule_id"])
order = m26.sort_values(["breaches", "conditional_or_check"], ascending=[False, False]).index.tolist()


def cell_text(site, rid):
    r = L26.loc[(site, rid)]
    v, u = r["value"], r["unit"]
    if r["verdict"] == "not assessable":
        return SYM[r["verdict"]]
    if pd.isna(v):
        return f"{SYM[r['verdict']]} >2.5 km"
    if u == "km":
        return f"{SYM[r['verdict']]} {v:.1f} km"
    if isinstance(u, str) and u.startswith("%"):
        return f"{SYM[r['verdict']]} {v:.0f}%"
    if rid == "R4":
        return f"{SYM[r['verdict']]} {int(r['n_within_limit'])} bldg"
    if rid in ("R9", "R10") and v > 2500:
        return f"{SYM[r['verdict']]} >2.5 km"
    return f"{SYM[r['verdict']]} {v:,.0f} m" if v < 2500 else f"{SYM[r['verdict']]} >2.5 km"


# ------------------------------------------------------------------ S1 compliance matrix
def fig_matrix():
    fig, ax = plt.subplots(figsize=(21, 9.4))
    nr, nc = len(order), len(RULE_IDS)
    for i, s in enumerate(order):
        for j, rid in enumerate(RULE_IDS):
            v = L26.loc[(s, rid)]["verdict"]
            ax.add_patch(Rectangle((j + 0.03, nr - i - 1 + 0.05), 0.94, 0.9, color=STATUS[v], lw=0))
            ax.text(j + 0.5, nr - i - 0.5, cell_text(s, rid), ha="center", va="center", fontsize=9.5,
                    color=STATUS_TXT[v], fontweight="bold" if v == "breach" else "normal")
        b, c = int(m26.loc[s, "breaches"]), int(m26.loc[s, "conditional_or_check"])
        ax.text(nc + 0.15, nr - i - 0.5, f"{b}", ha="left", va="center", fontsize=13, fontweight="bold", color=INK)
        ax.text(nc + 0.6, nr - i - 0.5, f"of {len(SCORED)}" + (f"  (+{c} to check)" if c else ""), ha="left",
                va="center", fontsize=9.5, color=INK2)
        ax.text(-0.1, nr - i - 0.5, f"{s}  {SHORT[s]}", ha="right", va="center", fontsize=10.5, color=INK)
    for j, rid in enumerate(RULE_IDS):
        ax.text(j + 0.5, nr + 0.12, HDR[rid], ha="center", va="bottom", fontsize=9.5, color=INK, fontweight="bold")
    ax.text(nc + 0.15, nr + 0.12, "Rules\nbreached", ha="left", va="bottom", fontsize=9.5, fontweight="bold", color=INK)
    ax.set_xlim(-3.3, nc + 2.6); ax.set_ylim(-1.3, nr + 1.6); ax.axis("off")
    ax.set_title("SWM Rules 2026, Schedule II(A)(vii)-(viii): siting criteria vs the 2026 dumpsite outlines (14 sites)",
                 loc="left", fontsize=13, color=INK, pad=4)
    handles = [Patch(color=STATUS["breach"], label="✘ breach (value = nearest distance / overlap / buildings within 200 m)"),
               Patch(color=STATUS["check"], label="? conditional (airport 10-20 km: needs NOC) or check (edge case)"),
               Patch(color=STATUS["ok"], label="✔ meets the rule"),
               Patch(color=STATUS["not assessable"], label="n/a  not assessable from open data")]
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.0, -0.02), ncol=2, frameon=False, fontsize=9.5)
    fig.savefig(os.path.join(C.FIG, "figS1_compliance_matrix_2026.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ S2 breaches per site
def fig_per_site():
    d = m26.loc[order[::-1]]
    fig, ax = plt.subplots(figsize=(10.5, 6.8))
    y = np.arange(len(d))
    ax.barh(y, d["breaches"], color=STATUS["breach"], height=0.62, label="breach", edgecolor=BG, linewidth=2)
    ax.barh(y, d["conditional_or_check"], left=d["breaches"], color=STATUS["check"], height=0.62,
            label="conditional / check", edgecolor=BG, linewidth=2)
    for yi, (b, c, rules) in enumerate(zip(d["breaches"], d["conditional_or_check"], d["breached_rules"].fillna(""))):
        ax.text(b + c + 0.12, yi, f"{b}" + (f" (+{c})" if c else "") + (f"   {rules}" if rules else ""),
                va="center", fontsize=8.8, color=INK2)
    ax.set_yticks(y); ax.set_yticklabels([f"{s}  {SHORT[s]}" for s in d.index], fontsize=9.5, color=INK)
    ax.set_xlim(0, len(SCORED)); ax.set_xticks(range(0, len(SCORED) + 1))
    ax.set_xlabel(f"Number of siting rules breached (of {len(SCORED)} assessable)")
    ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    ax.set_title("Rules breached per dumpsite, 2026 outline", loc="left", fontsize=12.5, color=INK)
    fig.savefig(os.path.join(C.FIG, "figS2_breaches_per_site.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ S3 sites per rule
def fig_per_rule():
    rid = SCORED[::-1]
    nb = [(m26[r] == "breach").sum() for r in rid]
    nc = [m26[r].isin(["conditional", "check"]).sum() for r in rid]
    fig, ax = plt.subplots(figsize=(9.5, 5.6))
    y = np.arange(len(rid))
    ax.barh(y, nb, color=STATUS["breach"], height=0.6, edgecolor=BG, linewidth=2, label="breach")
    ax.barh(y, nc, left=nb, color=STATUS["check"], height=0.6, edgecolor=BG, linewidth=2, label="conditional / check")
    for yi, (b, c) in enumerate(zip(nb, nc)):
        ax.text(b + c + 0.15, yi, f"{b}" + (f" (+{c})" if c else ""), va="center", fontsize=9.5, color=INK2)
    ax.set_yticks(y); ax.set_yticklabels([RSHORT[r].replace("\n", " ") for r in rid], color=INK)
    ax.set_xlim(0, 14.5); ax.set_xticks(range(0, 15, 2)); ax.set_xlabel("Number of dumpsites (of 14)")
    ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    ax.set_title("How many of the 14 dumpsites breach each rule (2026 outline)", loc="left", fontsize=12.5, color=INK)
    fig.savefig(os.path.join(C.FIG, "figS3_sites_per_rule.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ S4 distance vs limit
def fig_distance():
    panels = [("river_m", "Nearest river (m)", 100, 1000), ("pond_m", "Nearest pond / lake (m)", 200, 1000),
              ("highway_m", "Nearest NH / SH (m)", 200, 1000), ("buildings_within_200m", "Residential buildings within 200 m", 5, 400),
              ("park_m", "Nearest public park (m)", 200, 1000), ("airport_km", "Nearest airport / airbase (km)", 20, 30)]
    nd = near.set_index("site").loc[order[::-1]]
    fig, axes = plt.subplots(1, 6, figsize=(20, 6.8), sharey=True)
    y = np.arange(len(nd))
    for ax, (col, lab, lim, cap) in zip(axes, panels):
        v = nd[col].astype(float)
        count = col == "buildings_within_200m"
        vv = v.fillna(np.inf).clip(upper=cap)
        if count:      # breach zone = at or above the threshold
            ax.axvspan(lim, cap * 1.3, color=STATUS["breach"], alpha=0.10, lw=0)
        else:
            ax.axvspan(0, lim, color=STATUS["breach"], alpha=0.10, lw=0)
        if col == "airport_km":
            ax.axvspan(0, 10, color=STATUS["breach"], alpha=0.10, lw=0)
            ax.axvline(10, color=STATUS["breach"], lw=1, ls=":")
            ax.text(10, -1.05, "10", color=STATUS["breach"], fontsize=8.5, ha="center")
        ax.axvline(lim, color=STATUS["breach"], lw=1.4)
        verdict = {"river_m": "R1", "pond_m": "R2", "highway_m": "R3", "buildings_within_200m": "R4", "park_m": "R5",
                   "airport_km": "R7"}[col]
        cols = [STATUS[L26.loc[(s, verdict)]["verdict"]] if L26.loc[(s, verdict)]["verdict"] != "ok" else INK2
                for s in nd.index]
        ax.scatter(vv, y, s=46, c=cols, zorder=3, edgecolor=BG, linewidth=1.2)
        for yi, (x, raw) in enumerate(zip(vv, v)):
            if not np.isfinite(raw):
                t = f">{C.LOCAL_RADIUS/1000:.1f} km" if not col.endswith("km") else "none"
            elif raw > cap:
                t = f">{cap:,}"
            else:
                t = f"{raw:.1f}" if col == "airport_km" else f"{raw:,.0f}"
            ax.text(min(x, cap) + cap * 0.03, yi, t, va="center", fontsize=8, color=INK2)
        ax.set_xlim(0, cap * 1.3)
        ax.set_title(lab, fontsize=10, color=INK, loc="left")
        unit = " km" if col.endswith("km") else ("" if count else " m")
        ax.text(lim, -1.05, (f"≥ {lim} = breach" if count else f"limit {lim}{unit}"), color=STATUS["breach"],
                fontsize=8.5, ha="left" if count else "center")
        ax.set_ylim(-1.4, len(nd) - 0.4)
        ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    axes[0].set_yticks(y); axes[0].set_yticklabels([f"{s} {SHORT[s]}" for s in nd.index], fontsize=9, color=INK)
    fig.suptitle("Measured distance (or building count) vs the SWM 2026 limit, 2026 outline (shaded = breach; axes capped)",
                 x=0.01, ha="left", fontsize=12.5, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(os.path.join(C.FIG, "figS4_distance_vs_limit.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ S6 2016 vs 2026
def fig_epochs():
    d = pd.DataFrame(dict(b16=m16["breaches"], b26=m26["breaches"])).loc[order[::-1]]
    fig, ax = plt.subplots(figsize=(9, 6.4))
    y = np.arange(len(d))
    for yi, (a, b) in enumerate(zip(d.b16, d.b26)):
        ax.plot([a, b], [yi, yi], color="#c3c2b7", lw=2, zorder=1)
    ax.scatter(d.b16, y, s=60, color="#86b6ef", zorder=2, label="2016 outline", edgecolor=BG, linewidth=1.2)
    ax.scatter(d.b26, y, s=60, color="#184f95", zorder=3, label="2026 outline", edgecolor=BG, linewidth=1.2)
    for yi, (a, b) in enumerate(zip(d.b16, d.b26)):
        if a != b:
            ax.text(max(a, b) + 0.25, yi, f"{a} → {b}", va="center", fontsize=8.8, color=INK2)
    ax.set_yticks(y); ax.set_yticklabels([f"{s}  {SHORT[s]}" for s in d.index], fontsize=9.5, color=INK)
    ax.set_xlim(-0.3, len(SCORED)); ax.set_xticks(range(0, len(SCORED) + 1))
    ax.set_xlabel("Rules breached (same 2026 feature data, outline of each year)")
    ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    ax.set_title("Breaches with the 2016 vs the 2026 dumpsite outline", loc="left", fontsize=12.5, color=INK)
    fig.savefig(os.path.join(C.FIG, "figS6_2016_vs_2026.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ S5 maps
STY = {  # layer: (face, edge, linewidth, alpha, zorder, label)
    "flood_100yr": ("#3987e5", "#3987e5", 0.0, 0.28, 2, "JRC 100-yr flood extent"),
    "wetland": ("none", "#9085e9", 1.4, 1.0, 3, "Wetland (OSM)"),
    "tidal": ("none", "#e87ba4", 1.4, 1.0, 3, "Tidal creek / mangrove / mudflat (OSM)"),
    "coastline": ("none", "#e87ba4", 2.0, 1.0, 3, None),
    "park": ("#1baf7a", "#1baf7a", 1.0, 0.45, 3, "Public park (OSM)"),
    "residential": ("none", "#f0c2d4", 1.0, 0.9, 3, "Residential area (OSM)"),
    "pond": ("#5ad1ff", "#5ad1ff", 1.0, 0.65, 4, "Pond / lake (OSM)"),
    "river": ("#5ad1ff", "#5ad1ff", 2.2, 0.9, 4, "River (OSM)"),
    "stream_canal": ("none", "#9ec5f4", 0.9, 0.8, 3, None),
    "highway": ("none", "#eb6834", 2.2, 1.0, 5, "NH / SH / major road (OSM)"),
}


def site_map(ax, s, gdf, basemap=True, legend=False, small=False):
    import contextily as cx
    g = gdf.to_crs(3857)
    out = g[g.layer == "outline_2026"]
    x0, y0, x1, y1 = out.total_bounds
    pad = max(450, 0.25 * max(x1 - x0, y1 - y0))
    cx0, cy0 = (x0 + x1) / 2, (y0 + y1) / 2
    half = max(x1 - x0, y1 - y0) / 2 + pad
    ax.set_xlim(cx0 - half, cx0 + half); ax.set_ylim(cy0 - half, cy0 + half)
    if basemap:
        try:
            cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, attribution=False, zoom="auto")
        except Exception as e:
            print("  basemap failed:", s, e)
    for lay in ("flood_100yr", "residential", "park", "pond", "wetland", "tidal", "coastline", "stream_canal", "river", "highway"):
        sub = g[g.layer == lay]
        if len(sub):
            fc, ec, lw, a, z, _ = STY[lay]
            poly = sub[sub.geom_type.isin(["Polygon", "MultiPolygon"])]
            line = sub[~sub.geom_type.isin(["Polygon", "MultiPolygon", "Point", "MultiPoint"])]
            if len(poly):
                poly.plot(ax=ax, facecolor=fc, edgecolor=ec, linewidth=min(lw, 1.0), alpha=a, zorder=z)
            if len(line):       # lines get colour only: a face colour would fill the area enclosed by the line
                line.plot(ax=ax, color=ec, linewidth=lw, alpha=max(a, 0.9), zorder=z)
    b = g[g.layer == "building"]
    if len(b):
        res = b[~b.in_industrial_zone.astype(bool)]
        ind = b[b.in_industrial_zone.astype(bool)]
        res[res.distance_m >= 200].plot(ax=ax, facecolor="none", edgecolor="#fcfcfb", linewidth=0.4, alpha=0.7, zorder=5)
        if len(ind):
            ind[ind.distance_m < 500].plot(ax=ax, facecolor="none", edgecolor="#eda100", linewidth=0.6, zorder=5)
        near_ = res[res.distance_m < 200]
        counted = near_[near_.ghsl_2018 == 1]
        other = near_[near_.ghsl_2018 != 1]
        if len(other):
            other.plot(ax=ax, facecolor="none", edgecolor="#e34948", linewidth=0.8, zorder=6)
        if len(counted):
            counted.plot(ax=ax, facecolor="#e34948", edgecolor="#e34948", linewidth=0.5, zorder=6)
    for k, ls in ((100, (0, (4, 3))), (200, (0, (1.5, 2)))):
        rb = g[g.layer == f"buffer_{k}m"]
        if len(rb):
            rb.boundary.plot(ax=ax, color="#fcfcfb", linewidth=1.1, linestyle=ls, zorder=7)
    out.plot(ax=ax, facecolor="none", edgecolor="#fab219", linewidth=2.0, zorder=8)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_edgecolor("#c3c2b7")
    b_, c_ = int(m26.loc[s, "breaches"]), int(m26.loc[s, "conditional_or_check"])
    ax.set_title(f"{s} {SHORT[s]}: {b_} breach{'es' if b_ != 1 else ''}" + (f" (+{c_})" if c_ else ""),
                 fontsize=9.5 if small else 12, color=INK, loc="left")
    # scale bar 200 m
    sx, sy = cx0 - half + 0.06 * 2 * half, cy0 - half + 0.06 * 2 * half
    lat = float(np.mean(gdf[gdf.layer == "outline_2026"].to_crs(4326).total_bounds[[1, 3]]))
    ax.plot([sx, sx + 200 / np.cos(np.radians(lat))], [sy, sy], color="#fcfcfb", lw=3, zorder=9,
            solid_capstyle="butt")      # Web-Mercator metres are stretched by 1/cos(latitude)
    ax.text(sx, sy + 0.025 * 2 * half, "200 m", color="#fcfcfb", fontsize=8 if small else 9, zorder=9)


def map_legend():
    h = [Line2D([], [], color="#fab219", lw=2, label="Dumpsite outline 2026"),
         Line2D([], [], color="#52514e", lw=1.1, ls=(0, (4, 3)), label="100 m ring"),
         Line2D([], [], color="#52514e", lw=1.1, ls=(0, (1.5, 2)), label="200 m ring"),
         Patch(color="#e34948", label="Residential building within 200 m (counted)"),
         Patch(facecolor="none", edgecolor="#e34948", label="Other building within 200 m (not counted)"),
         Patch(facecolor="none", edgecolor="#898781", label="Building 200-500 m"),
         Patch(facecolor="none", edgecolor="#eda100", label="Building in industrial / plant zone (not counted)")]
    for lay in ("river", "pond", "highway", "park", "residential", "wetland", "tidal", "flood_100yr"):
        fc, ec, lw, a, z, lab = STY[lay]
        h.append(Line2D([], [], color=ec, lw=2.2, label=lab) if lay in ("river", "highway", "tidal", "wetland", "residential")
                 else Patch(facecolor=fc, edgecolor=ec, alpha=max(a, 0.5), label=lab))
    return h


S5_ROWS, S5_COLS = 3, 5          # landscape: 14 maps + one cell for the key and credits (was 4 x 4 portrait)
S5_CREDITS = ("Imagery: Esri World Imagery (Maxar, Earthstar Geographics).\n"
              "Features: OpenStreetMap contributors (ODbL), Overture Maps buildings,\n"
              "JRC / Copernicus global flood hazard map (100-yr).\n"
              "Airport and protected-area distances are in figS1 / siting_results.xlsx.")


def s5_title(s):
    b_, c_ = int(m26.loc[s, "breaches"]), int(m26.loc[s, "conditional_or_check"])
    return f"{s} {SHORT[s]}: {b_} breach{'es' if b_ != 1 else ''}" + (f" (+{c_})" if c_ else "")


def s5_layout(draw_site):
    """Landscape figS5: 3 rows x 5 columns; draw_site(ax, site) fills one map cell."""
    fig, axes = plt.subplots(S5_ROWS, S5_COLS, figsize=(30, 18.5))
    for ax, s in zip(axes.flat, sorted(m26.index)):
        draw_site(ax, s)
    key = axes.flat[len(m26.index)]; key.axis("off")
    for ax in axes.flat[len(m26.index) + 1:]: ax.axis("off")
    key.legend(handles=map_legend(), loc="upper left", bbox_to_anchor=(0.0, 1.02), frameon=False, fontsize=10.5)
    key.text(0.0, -0.02, S5_CREDITS, fontsize=9, color=INK2, va="top", transform=key.transAxes)
    fig.suptitle("Dumpsites (2026 outline) with the 100 m / 200 m siting rings and the features that set the verdicts",
                 x=0.01, ha="left", fontsize=16, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.97), w_pad=1.0, h_pad=1.6)
    fig.savefig(os.path.join(C.FIG, "figS5_site_maps.png"), dpi=110, bbox_inches="tight")
    plt.close(fig)


def fig_maps_from_site_pngs():
    """Rebuild the landscape figS5 offline from the per-site maps already in outputs/sites/ (they carry the satellite
    imagery). The map area of each per-site PNG is the axes at [0.01, 0.03, 0.62, 0.9] of the figure (see fig_maps)."""
    from PIL import Image
    def draw(ax, s):
        im = Image.open(os.path.join(C.SITES_OUT, s, f"{s}_siting_map.png")); W, H = im.size
        ax.imshow(im.crop((round(0.01 * W), round(0.07 * H), round(0.63 * W), round(0.97 * H))))
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values(): sp.set_edgecolor("#c3c2b7")
        ax.set_title(s5_title(s), fontsize=11, color=INK, loc="left")
    s5_layout(draw)


def fig_maps():
    def draw(ax, s):
        gdf = gpd.read_file(os.path.join(C.SITES_OUT, s, f"{s}_layers.geojson"))
        site_map(ax, s, gdf, small=True)
        ax.set_title(s5_title(s), fontsize=11, color=INK, loc="left")
    s5_layout(draw)
    for s in sorted(m26.index):
        gdf = gpd.read_file(os.path.join(C.SITES_OUT, s, f"{s}_layers.geojson"))
        fig = plt.figure(figsize=(13, 9))
        ax = fig.add_axes([0.01, 0.03, 0.62, 0.9])
        site_map(ax, s, gdf)
        lg = fig.add_axes([0.65, 0.35, 0.34, 0.6]); lg.axis("off")
        lg.legend(handles=map_legend(), loc="upper left", frameon=False, fontsize=9.5)
        tx = fig.add_axes([0.65, 0.03, 0.34, 0.33]); tx.axis("off")
        lines = []
        for rid in SCORED:
            r = L26.loc[(s, rid)]
            lines.append(f"{SYM[r['verdict']]:>3}  {RSHORT[rid].replace(chr(10), ' ')}: {cell_text(s, rid)[2:].strip()}")
        tx.text(0, 1, "\n".join(lines), va="top", fontsize=9, family="DejaVu Sans Mono", color=INK)
        fig.savefig(os.path.join(C.SITES_OUT, s, f"{s}_siting_map.png"), dpi=150)
        plt.close(fig)


# ------------------------------------------------------------------ KML for Google Earth Pro
def kml_export():
    col = {"outline_2026": "ff19b2fa", "buffer_100m": "ffffffff", "buffer_200m": "ffffffff", "river": "ffffd15a",
           "pond": "ffffd15a", "highway": "ff3468eb", "park": "ff7aaf1b", "building": "ff4849e3", "flood_100yr": "80e58739",
           "wetland": "ffe98590", "tidal": "ffa47be8", "residential": "ffd4c2f0", "protected_area": "ff008300", "airport": "ff00a1ed"}
    keep = set(col)
    parts = ['<?xml version="1.0" encoding="UTF-8"?>', '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
             "<name>SWM 2026 siting check - layers</name>"]
    for k, c in col.items():
        parts.append(f'<Style id="{k}"><LineStyle><color>{c}</color><width>2</width></LineStyle>'
                     f'<PolyStyle><color>{c[:0] + "40" + c[2:]}</color></PolyStyle></Style>')

    def coords(seq):
        return " ".join(f"{x:.6f},{y:.6f},0" for x, y in seq)

    def geom_kml(g):
        t = g.geom_type
        if t == "Polygon":
            s = f"<Polygon><outerBoundaryIs><LinearRing><coordinates>{coords(g.exterior.coords)}</coordinates></LinearRing></outerBoundaryIs>"
            for r in g.interiors:
                s += f"<innerBoundaryIs><LinearRing><coordinates>{coords(r.coords)}</coordinates></LinearRing></innerBoundaryIs>"
            return s + "</Polygon>"
        if t == "LineString":
            return f"<LineString><coordinates>{coords(g.coords)}</coordinates></LineString>"
        if t == "Point":
            return f"<Point><coordinates>{g.x:.6f},{g.y:.6f},0</coordinates></Point>"
        if t.startswith("Multi") or t == "GeometryCollection":
            return "<MultiGeometry>" + "".join(geom_kml(x) for x in g.geoms) + "</MultiGeometry>"
        return ""

    for s in sorted(m26.index):
        gdf = gpd.read_file(os.path.join(C.SITES_OUT, s, f"{s}_layers.geojson"))
        parts.append(f"<Folder><name>{s} {html.escape(SHORT[s])} - {int(m26.loc[s, 'breaches'])} breaches</name><open>0</open>")
        for lay in col:
            sub = gdf[gdf.layer == lay]
            if lay == "building":
                sub = sub[(sub.distance_m < 200) & (~sub.in_industrial_zone.astype(bool))].copy()
                sub["name"] = np.where(sub.ghsl_2018 == 1, "residential building (counted)", "other building (not counted)")
            if not len(sub):
                continue
            parts.append(f"<Folder><name>{lay}</name>")
            for _, r in sub.iterrows():
                nm = html.escape(str(r.get("name") or lay) if isinstance(r.get("name"), str) else lay)
                dm = r.get("distance_m")
                desc = f"distance to 2026 outline: {dm:.0f} m" if isinstance(dm, (float, int)) and np.isfinite(dm) else ""
                parts.append(f"<Placemark><name>{nm}</name><description>{desc}</description><styleUrl>#{lay}</styleUrl>"
                             f"{geom_kml(r.geometry)}</Placemark>")
            parts.append("</Folder>")
        parts.append("</Folder>")
    parts.append("</Document></kml>")
    open(os.path.join(C.OUT, "siting_check_layers.kml"), "w", encoding="utf-8").write("\n".join(parts))


# ------------------------------------------------------------------ workbook
def workbook():
    rules = pd.DataFrame([dict(id=r["id"], rule=r["rule"], limit=r["limit"], kind=r["kind"]) for r in C.RULES])
    rules["how tested here"] = [L26.xs(r, level="rule_id")["basis"].iloc[0] for r in rules.id]
    rules["confidence"] = rules.id.map({"R1": "medium-high", "R2": "medium", "R3": "medium-high", "R4": "medium",
                                        "R5": "medium", "R6": "-", "R7": "high", "R8": "low-medium (90 m global model)",
                                        "R9": "low (screening)", "R10": "low-medium", "R11": "medium", "R12": "-"})
    src = json.load(open(os.path.join(C.DATA, "sources.json")))
    srcs = pd.DataFrame([dict(item=k, detail=json.dumps(v)) for k, v in src.items()])
    params = pd.DataFrame([dict(parameter=k, value=str(getattr(C, k))) for k in dir(C) if k.isupper() and k not in ("RULES",)])
    pa = pd.read_csv(os.path.join(C.TABLES, "protected_areas.csv"))
    ap = pd.read_csv(os.path.join(C.TABLES, "airports.csv"))
    with pd.ExcelWriter(os.path.join(C.TABLES, "siting_results.xlsx"), engine="openpyxl") as xw:
        summ.to_excel(xw, sheet_name="Summary")
        m26.to_excel(xw, sheet_name="Matrix_2026")
        near.to_excel(xw, sheet_name="Distances_2026", index=False)
        long[long.epoch == C.MAIN_EPOCH].to_excel(xw, sheet_name="Detail_2026", index=False)
        m16.to_excel(xw, sheet_name="Matrix_2016")
        long[long.epoch == C.COMPARE_EPOCH].to_excel(xw, sheet_name="Detail_2016", index=False)
        hab.to_excel(xw, sheet_name="Habitation", index=False)
        ap.to_excel(xw, sheet_name="Airports", index=False)
        pa.to_excel(xw, sheet_name="Protected_areas", index=False)
        rules.to_excel(xw, sheet_name="Rules", index=False)
        srcs.to_excel(xw, sheet_name="Data_sources", index=False)
        params.to_excel(xw, sheet_name="Parameters", index=False)
    from openpyxl import load_workbook
    from openpyxl.styles import PatternFill, Font, Alignment
    wb = load_workbook(os.path.join(C.TABLES, "siting_results.xlsx"))
    fills = {k: PatternFill("solid", fgColor=v[1:]) for k, v in STATUS.items()}
    for ws in wb.worksheets:
        for c in ws[1]:
            c.font = Font(bold=True); c.alignment = Alignment(wrap_text=True, vertical="top")
        for col in ws.columns:
            w = max(len(str(c.value)) if c.value is not None else 0 for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(max(10, w + 2), 60)
        ws.freeze_panes = "B2"
        for row in ws.iter_rows(min_row=2):
            for c in row:
                if isinstance(c.value, str) and c.value in fills:
                    c.fill = fills[c.value]
                    if c.value in ("breach", "ok"):
                        c.font = Font(color="FFFFFF", bold=c.value == "breach")
    wb.save(os.path.join(C.TABLES, "siting_results.xlsx"))


if __name__ == "__main__":
    import sys
    if "--maps-only" in sys.argv:
        fig_maps(); print("maps done"); sys.exit()
    if "--s5-from-site-maps" in sys.argv:           # no internet: re-tile figS5 from outputs/sites/*/<SITE>_siting_map.png
        fig_maps_from_site_pngs(); print("figS5 rebuilt from the per-site maps"); sys.exit()
    fig_matrix(); fig_per_site(); fig_per_rule(); fig_distance(); fig_epochs()
    print("charts done")
    workbook(); print("workbook done")
    kml_export(); print("kml done")
    fig_maps(); print("maps done")
