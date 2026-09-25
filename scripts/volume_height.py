"""
Dumpsite height and volume from DEMs - all traced sites (v2, 25 Sep 2026).

Usage
  python volume_height.py                 # all sites in the KML (minus exclusions)
  python volume_height.py BHV-01 AHM-01   # only these sites

Inputs
  ../Locations of landfills in gujurat (3).kml   master outlines (same parsing rules as analysis/trend_analysis.py)
  dem/glo30/                                     Copernicus GLO-30 (per-site clips, or full tiles auto-downloaded from AWS, no login)
  dem/ (any subfolder)                           unzipped DLR tiles: TDM1_EDEM_10_<tile>... and TDM1_DCM__10_<tile>_LAST1622...

Method (per site)
  1. Footprint = union of all traced outlines of the site (all epochs): every DEM is measured over the same area.
  2. DEMs reprojected to UTM 43N (EPSG:32643), 10 m grid, bilinear.
  3. Base (original ground) from a ring 30-150 m outside the footprint, with other sites' footprints removed
     and outliers dropped (median +/- 3 MAD). Base models: least-squares plane (main), flat median, IDW.
  4. Volume = sum(DEM - base) x cell area (net sum, unbiased by noise). Heights above base reported.
  5. Uncertainty = base level (ring sd / sqrt(n 30 m cells) x area) + random noise (sd x sqrt(n) x 900 m2)
     + half the spread of the three base models, in quadrature.
  6. Change 2011-13 -> DCM date = sum of the DCM over the footprint, minus the ring median change.
     New surface = reference + DCM (reference = TanDEM-X EDEM if present, else GLO-30; the two agree
     within 0.4% at BHV-01). DCM pixels with CIM = 0 (invalid) are dropped. Date read from the DATE layer.
  7. Tonnes = volume x bulk density (low / central / high).
"""
import glob, json, math, os, re, sys
import xml.etree.ElementTree as ET
from collections import defaultdict

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.features import geometry_mask
from shapely.geometry import Polygon
from shapely.ops import unary_union, transform
from pyproj import Transformer
import matplotlib
import matplotlib.ticker
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------ CONFIG
CONFIG = dict(
    kml=os.path.join(HERE, "..", "Locations of landfills in gujurat (3).kml"),
    dem_dir=os.path.join(HERE, "dem"),
    glo30_dir=os.path.join(HERE, "dem", "glo30"),
    out=os.path.join(HERE, "outputs"),
    # exclusions (student, 25 Sep): Khajod (Surat LF-2) and all Vadodara sites; Jamnagar LF-2 ignored
    exclude_cities={"vadodara"},
    exclude_keys={("surat", "2"), ("jamnagar", "2")},
    epoch_map={2025: 2024},                 # 2025 image = 2024 epoch
    res=10.0, margin=400.0, ring_in=30.0, ring_out=150.0,
    small_ha=3.0,                           # footprints below this are flagged (30 m DEM, ~30 pixels)
    # bulk density of dumped MSW (t/m3): low / central / high. Range from MSW unit-weight
    # literature (Zekkos et al. 2006; ~10-14 kN/m3 landfilled MSW, uncompacted dumps at the low end).
    density=(0.8, 1.0, 1.2),
)
UTM = "EPSG:32643"
CITY = {"ahmedabad": "AHM", "surat": "SUR", "vadodara": "VAD", "rajkot": "RAJ", "bhavnagar": "BHV",
        "gandhinagar": "GNR", "jamnagar": "JAM", "bhuj": "BHJ", "mehsana": "MEH", "vapi": "VAP"}
NAMES = {"AHM-01": "Ahmedabad - Pirana", "AHM-02A": "Ahmedabad LF-2(a)", "AHM-02B": "Ahmedabad LF-2(b)",
         "AHM-03": "Ahmedabad LF-3", "SUR-01": "Surat - Bhatar", "RAJ-01": "Rajkot", "BHV-01": "Bhavnagar",
         "GNR-01": "Gandhinagar", "JAM-01": "Jamnagar", "BHJ-01": "Bhuj", "MEH-01": "Mehsana", "VAP-01": "Vapi"}
# --------------------------------------------------------------------------

fwd = Transformer.from_crs(4326, 32643, always_xy=True).transform
loc = lambda t: t.split("}")[-1]


# ============================================================ outlines (KML)
def parse_name(name):
    low = name.lower()
    city = re.match(r"\s*([a-z]+)", low).group(1)
    m = re.search(r"lf\s*-?\s*(\d)(?!\d)\s*(?:\(\s*([ab])\s*\))?", low)
    lf, sub = (m.group(1), m.group(2)) if m else ("1", None)
    yr = re.search(r"(20\d\d)", low)
    return city, lf, sub, (int(yr.group(1)) if yr else None)


def read_all_outlines(cfg):
    """Same rules as analysis/trend_analysis.py. Returns GeoDataFrame (site_id, epoch, geometry) in UTM."""
    root = ET.parse(cfg["kml"]).getroot()
    recs = defaultdict(list); seen = defaultdict(int)
    for pm in root.iter():
        if loc(pm.tag) != "Placemark":
            continue
        name = next((c.text or "" for c in pm if loc(c.tag) == "name"), "").strip()
        city, lf, sub, yr = parse_name(name)
        if city not in CITY or yr is None:
            continue
        if city in cfg["exclude_cities"] or (city, lf) in cfg["exclude_keys"]:
            continue
        polys = [e for e in pm.iter() if loc(e.tag) == "Polygon"]
        if not polys:
            continue
        sid = f"{CITY[city]}-{int(lf):02d}{(sub or '').upper()}"
        if sid == "RAJ-01" and yr == 2018:          # duplicate name: 2nd occurrence = 2016 (student decision)
            seen[(sid, yr)] += 1
            if seen[(sid, yr)] == 2:
                yr = 2016
        ep = cfg["epoch_map"].get(yr, yr)
        for pg in polys:
            outer = next((e for e in pg.iter() if loc(e.tag) == "outerBoundaryIs"), pg)
            coords = next(e for e in outer.iter() if loc(e.tag) == "coordinates").text.split()
            p = transform(fwd, Polygon([tuple(map(float, c.split(",")[:2])) for c in coords]))
            recs[(sid, ep)].append(p if p.is_valid else p.buffer(0))
    rows = [dict(site_id=s, epoch=e, geometry=unary_union(g)) for (s, e), g in recs.items()]
    return gpd.GeoDataFrame(rows, crs=UTM).sort_values(["site_id", "epoch"]).reset_index(drop=True)


# ============================================================ DEM helpers
def tile_codes(lon, lat):
    la, lo = math.floor(lat), math.floor(lon)
    ns, ew = ("N" if la >= 0 else "S"), ("E" if lo >= 0 else "W")
    dlr = f"{ns}{abs(la):02d}{ew}{abs(lo):03d}"
    glo = f"{ns}{abs(la):02d}_00_{ew}{abs(lo):03d}_00"
    return dlr, glo


def glo30_path(cfg, sid, glo_code):
    clip = os.path.join(cfg["glo30_dir"], f"glo30_{sid}_clip.tif")
    if os.path.exists(clip):
        return clip
    name = f"Copernicus_DSM_COG_10_{glo_code}_DEM"
    path = os.path.join(cfg["glo30_dir"], name + ".tif")
    if not os.path.exists(path):
        import urllib.request
        os.makedirs(cfg["glo30_dir"], exist_ok=True)
        url = f"https://copernicus-dem-30m.s3.amazonaws.com/{name}/{name}.tif"
        print("  downloading", url)
        urllib.request.urlretrieve(url, path)
    return path


def find_dlr(cfg, tile, layer):
    """layer: EDEM | DCM | DATE | CIM | HAI  (LAST variant for DCM layers)."""
    pats = {"EDEM": rf"_{tile}_EDEM_W84\.tif$",
            "DCM": rf"_{tile}_DCM__?LAST.*\.tif$",
            "DATE": rf"_{tile}_DATE_?_?LAST.*\.tif$",
            "CIM": rf"_{tile}_CIM__?LAST.*\.tif$",
            "HAI": rf"_{tile}_HAI__?LAST.*\.tif$"}
    f = sorted(p for p in glob.glob(os.path.join(cfg["dem_dir"], "**", "*.tif"), recursive=True)
               if re.search(pats[layer], os.path.basename(p), re.I))
    return f[0] if f else None


def warp_to_grid(path, bounds, res, resampling=Resampling.bilinear):
    x0, y0, x1, y1 = bounds
    w, h = int(round((x1 - x0) / res)), int(round((y1 - y0) / res))
    tr = rasterio.transform.from_origin(x0, y1, res, res)
    out = np.full((h, w), np.nan, dtype="float64")
    with rasterio.open(path) as src:
        scrs = "EPSG:4326" if src.crs.to_epsg() in (4326, 4979) else src.crs   # EDEM is tagged 3D (4979)
        reproject(source=rasterio.band(src, 1), destination=out, dst_transform=tr, src_crs=scrs,
                  dst_crs=UTM, src_nodata=src.nodata, dst_nodata=np.nan, resampling=resampling)
    return out, tr


def base_surfaces(z, X, Y, ring):
    zr, xr, yr = z[ring], X[ring], Y[ring]
    ok = np.isfinite(zr)
    med = np.median(zr[ok]); mad = 1.4826 * np.median(np.abs(zr[ok] - med))
    ok &= np.abs(zr - med) <= 3 * max(mad, 0.05)
    zr, xr, yr = zr[ok], xr[ok], yr[ok]
    xm, ym = xr.mean(), yr.mean()
    flat = np.full(z.shape, np.median(zr))
    A = np.c_[np.ones_like(xr), xr - xm, yr - ym]
    coef, *_ = np.linalg.lstsq(A, zr, rcond=None)
    plane = coef[0] + coef[1] * (X - xm) + coef[2] * (Y - ym)
    resid_sd = float(np.std(zr - A @ coef))
    step = max(1, len(zr) // 1500)
    xs, ys, zs = xr[::step], yr[::step], zr[::step]
    idw = np.empty(z.shape)
    for i in range(z.shape[0]):
        wgt = 1.0 / ((X[i][:, None] - xs) ** 2 + (Y[i][:, None] - ys) ** 2 + 1.0)
        idw[i] = (wgt @ zs) / wgt.sum(1)
    return dict(flat=flat, plane=plane, idw=idw), dict(
        ring_n=int(ok.sum()), ring_median=float(med), ring_resid_sd=resid_sd,
        ring_mad=float(mad), plane_slope_pct=float(100 * np.hypot(coef[1], coef[2])))


def metrics(z, base, mask, cell, noise=0.0):
    """vol_m3 = net volume above base (MAIN); vol_pos_m3 = positive heights only (biased high by noise);
    vol_pos_2sd_m3 = heights above 2 x noise only (conservative)."""
    h = (z - base)[mask]
    h = h[np.isfinite(h)]
    if h.size == 0:
        return dict(vol_m3=np.nan, vol_pos_m3=np.nan, vol_pos_2sd_m3=np.nan, h_max=np.nan, h_p95=np.nan,
                    h_mean_pos=np.nan, area_above_1m_ha=np.nan)
    pos = np.clip(h, 0, None)
    return dict(vol_m3=float(h.sum() * cell), vol_pos_m3=float(pos.sum() * cell),
                vol_pos_2sd_m3=float(h[h > 2 * noise].sum() * cell),
                h_max=float(h.max()), h_p95=float(np.percentile(h, 95)),
                h_mean_pos=float(pos[pos > 0].mean()) if (pos > 0).any() else 0.0,
                area_above_1m_ha=float((h > 1).sum() * cell / 1e4))


def quality(v, s, area_ha, cfg):
    """Reliability of the absolute volume (base-surface dependent). The DCM change does not use the base."""
    if v + 2 * s < 0:
        q = "below ground (depression/pit in this DEM)"
    else:
        r = s / abs(v) if v else np.inf
        q = "good" if r <= 0.10 else "fair" if r <= 0.25 else "poor (complex terrain or urban ring)"
    if area_ha < cfg["small_ha"]:
        q += "; small site"
    return q


def counts(a):
    a = a[np.isfinite(a)]
    return {str(int(k)): int(v) for k, v in zip(*np.unique(a, return_counts=True))}


# ============================================================ one site
def run_site(cfg, sid, g, others):
    out = os.path.join(cfg["out"], sid); os.makedirs(out, exist_ok=True)
    foot = unary_union(list(g.geometry))
    c = gpd.GeoSeries([foot.centroid], crs=UTM).to_crs(4326).iloc[0]
    dlr_tile, glo_code = tile_codes(c.x, c.y)
    res = cfg["res"]; cell = res * res
    x0, y0, x1, y1 = foot.buffer(cfg["margin"]).bounds
    bounds = (math.floor(x0 / res) * res, math.floor(y0 / res) * res,
              math.ceil(x1 / res) * res, math.ceil(y1 / res) * res)

    dems = {}
    glo, tr = warp_to_grid(glo30_path(cfg, sid, glo_code), bounds, res)
    dems["GLO30_2011-15"] = glo
    H, W = glo.shape
    cols, rws = np.meshgrid(np.arange(W), np.arange(H))
    X = bounds[0] + (cols + 0.5) * res
    Y = bounds[3] - (rws + 0.5) * res
    in_foot = ~geometry_mask([foot], (H, W), tr)
    ring_geom = foot.buffer(cfg["ring_out"]).difference(foot.buffer(cfg["ring_in"]))
    if others is not None and not others.is_empty:
        ring_geom = ring_geom.difference(others.buffer(cfg["ring_in"]))   # keep other dumps out of the base
    ring = ~geometry_mask([ring_geom], (H, W), tr)

    info = dict(site_id=sid, dlr_tile=dlr_tile, footprint_ha=round(foot.area / 1e4, 2))
    edem_f, dcm_f = find_dlr(cfg, dlr_tile, "EDEM"), find_dlr(cfg, dlr_tile, "DCM")
    ref, ref_name = glo, "GLO30_2011-15"
    if edem_f:
        ref, _ = warp_to_grid(edem_f, bounds, res); ref_name = "TDX_EDEM_2011-14"; dems[ref_name] = ref
    new_name = None
    if dcm_f:
        dcm, _ = warp_to_grid(dcm_f, bounds, res)
        info.update(dcm_file=os.path.basename(dcm_f), dcm_reference=ref_name)
        new_name = "TDX_DCM_new"
        f = find_dlr(cfg, dlr_tile, "DATE")
        if f:
            dt, _ = warp_to_grid(f, bounds, res, Resampling.nearest)
            dc = counts(dt[in_foot]); info["dcm_dates_px"] = dc
            if dc:
                d = max(dc, key=dc.get); new_name = f"TDX_{d[:4]}-{d[4:6]}-{d[6:]}"
                info["dcm_date"] = f"{d[:4]}-{d[4:6]}-{d[6:]}"
        f = find_dlr(cfg, dlr_tile, "CIM")
        if f:
            cim, _ = warp_to_grid(f, bounds, res, Resampling.nearest)
            info["cim_px"] = counts(cim[in_foot])
            dcm = np.where(cim == 0, np.nan, dcm)
        f = find_dlr(cfg, dlr_tile, "HAI")
        if f:
            hai, _ = warp_to_grid(f, bounds, res)
            info["hai_median_m"] = round(float(np.nanmedian(hai[in_foot])), 3)
        dems[new_name] = ref + dcm

    rows, bases = [], {}
    lo, mid, hi = cfg["density"]
    for name, z in dems.items():
        bs, rinfo = base_surfaces(z, X, Y, ring)
        bases[name] = bs["plane"]
        m = {k: metrics(z, b, in_foot, cell, rinfo["ring_resid_sd"]) for k, b in bs.items()}
        vols = [m[k]["vol_m3"] for k in m]
        n30_ring = max(rinfo["ring_n"] * cell / 900.0, 1); n30_foot = foot.area / 900.0
        s_base = rinfo["ring_resid_sd"] / math.sqrt(n30_ring) * foot.area
        s_rand = rinfo["ring_resid_sd"] * math.sqrt(n30_foot) * 900.0
        spread = (max(vols) - min(vols)) / 2
        s_tot = math.sqrt(s_base ** 2 + s_rand ** 2 + spread ** 2)
        v = m["plane"]["vol_m3"]
        row = dict(site_id=sid, name=NAMES.get(sid, sid), dem=name,
                   date=(info.get("dcm_date") if name == new_name else name.split("_")[-1]),
                   footprint_ha=round(foot.area / 1e4, 2), n_px30=int(round(n30_foot)),
                   small_site=foot.area / 1e4 < cfg["small_ha"],
                   **{k: round(x, 2) for k, x in m["plane"].items()},
                   vol_flat_m3=round(m["flat"]["vol_m3"]), vol_idw_m3=round(m["idw"]["vol_m3"]),
                   vol_sigma_baselevel_m3=round(s_base), vol_sigma_random_m3=round(s_rand),
                   vol_sigma_models_m3=round(spread), vol_sigma_total_m3=round(s_tot),
                   vol_rel_unc_pct=round(100 * s_tot / abs(v), 1) if v else None,
                   quality=quality(v, s_tot, foot.area / 1e4, cfg),
                   tonnes_central=round(v * mid), tonnes_low=round((v - s_tot) * lo),
                   tonnes_high=round((v + s_tot) * hi),
                   **{k: round(x, 3) for k, x in rinfo.items()})
        for _, r in g.iterrows():
            mk = ~geometry_mask([r.geometry], (H, W), tr)
            mm = metrics(z, bs["plane"], mk, cell)
            row[f"vol_in_{r.epoch}_outline_m3"] = round(mm["vol_m3"]) if np.isfinite(mm["vol_m3"]) else None
        rows.append(row)

    change = []
    pairs = []
    if new_name:
        pairs.append((ref_name, new_name))
    if edem_f:
        pairs.append(("GLO30_2011-15", ref_name))
    for a, b in pairs:
        dz = dems[b] - dems[a]
        dzi = dz[in_foot]; dzi = dzi[np.isfinite(dzi)]
        dzo = dz[ring]; dzo = dzo[np.isfinite(dzo)]
        corr = float((dzi - np.median(dzo)).sum() * cell)
        # change uncertainty: ring-level error + random error over independent 30 m cells (quadrature)
        sd = float(np.std(dzo)); n30_r = max(dzo.size * cell / 900.0, 1); n30_f = foot.area / 900.0
        s_dv = math.hypot(sd / math.sqrt(n30_r) * foot.area, sd * math.sqrt(n30_f) * 900.0)
        change.append(dict(site_id=sid, name=NAMES.get(sid, sid), from_dem=a, to_dem=b,
                           dV_net_m3=round(float(dzi.sum() * cell)),
                           dV_gain_m3=round(float(np.clip(dzi, 0, None).sum() * cell)),
                           dV_loss_m3=round(float(np.clip(dzi, None, 0).sum() * cell)),
                           dz_max=round(float(dzi.max()), 2), dz_min=round(float(dzi.min()), 2),
                           ring_dz_median=round(float(np.median(dzo)), 2), ring_dz_sd=round(float(np.std(dzo)), 2),
                           dV_net_ring_corrected_m3=round(corr), dV_sigma_m3=round(s_dv),
                           dtonnes_central=round(corr * mid), dtonnes_low=round(corr * lo), dtonnes_high=round(corr * hi)))

    # ---- figures
    ext = [bounds[0], bounds[2], bounds[1], bounds[3]]
    n = len(dems) + (1 if change and new_name else 0)
    fig, axs = plt.subplots(1, n, figsize=(4.8 * n, 4.8), squeeze=False)
    hi_ = max(2, np.nanpercentile((dems[list(dems)[-1]] - bases[list(dems)[-1]])[in_foot], 99))
    for ax, (name, z) in zip(axs[0], dems.items()):
        im = ax.imshow(z - bases[name], extent=ext, cmap="viridis", vmin=-1, vmax=hi_)
        plt.colorbar(im, ax=ax, shrink=0.8, label="height above base (m)"); ax.set_title(name, fontsize=10)
    if change and new_name:
        dz = dems[new_name] - dems[ref_name]
        lim = max(1, np.nanpercentile(np.abs(dz[in_foot]), 99))
        im = axs[0][-1].imshow(dz, extent=ext, cmap="RdBu_r", vmin=-lim, vmax=lim)
        plt.colorbar(im, ax=axs[0][-1], shrink=0.8, label="elevation change (m)")
        axs[0][-1].set_title(f"{new_name} minus {ref_name}", fontsize=10)
    for k, ax in enumerate(axs[0]):
        col = "k" if (change and new_name and k == n - 1) else "w"
        for geom in g.geometry:
            for p in ([geom] if geom.geom_type == "Polygon" else list(geom.geoms)):
                ax.plot(*p.exterior.xy, lw=0.7, color=col)
        gpd.GeoSeries([ring_geom]).boundary.plot(ax=ax, color="orange", lw=0.6, ls="--")
        ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle(f"{sid} {NAMES.get(sid, '')}: outlines of all epochs (lines), base ring (orange dashed)")
    fig.tight_layout(); fig.savefig(os.path.join(out, f"{sid}_height_maps.png"), dpi=170); plt.close(fig)

    last = list(dems)[-1]
    hl = np.where(in_foot, dems[last] - bases[last], -np.inf)
    ri, ci = np.unravel_index(np.nanargmax(hl), hl.shape)
    fig, axs = plt.subplots(1, 2, figsize=(11, 3.8))
    for ax, lab in zip(axs, ["W-E", "S-N"]):
        for name, z in dems.items():
            h = (z - bases[name])
            prof = h[ri, :] if lab == "W-E" else h[::-1, ci]
            ax.plot(np.arange(prof.size) * res, prof, label=name)
        inside = in_foot[ri, :] if lab == "W-E" else in_foot[::-1, ci]
        ax.axhline(0, color="k", ls="--", lw=0.8, label="base (plane)")
        yl = ax.get_ylim()
        ax.fill_between(np.arange(inside.size) * res, yl[0], yl[1], where=inside, color="grey", alpha=0.15,
                        label="footprint")
        ax.set_ylim(yl); ax.set_xlabel(f"distance {lab} (m)"); ax.set_ylabel("height above base (m)")
        ax.set_title(f"{sid}: {lab} profile through highest point")
    axs[0].legend(fontsize=7); fig.tight_layout()
    fig.savefig(os.path.join(out, f"{sid}_profiles.png"), dpi=170); plt.close(fig)

    info["outline_area_ha"] = {int(r.epoch): round(r.geometry.area / 1e4, 2) for _, r in g.iterrows()}
    with open(os.path.join(out, f"{sid}_run_info.json"), "w") as f:
        json.dump(info, f, indent=2)
    pd.DataFrame(rows).to_csv(os.path.join(out, f"{sid}_volume_by_dem.csv"), index=False)
    if change:
        pd.DataFrame(change).to_csv(os.path.join(out, f"{sid}_volume_change.csv"), index=False)
    return rows, change, info


# ============================================================ summary chart
def summary_chart(df, path):
    """Horizontal bars, log scale (volumes span 3+ orders of magnitude). Baseline vs DCM date.
    Hatched = poor base (complex terrain / urban ring); negative volumes written as text."""
    base = df[df.dem.isin(["TDX_EDEM_2011-14"])]
    base = pd.concat([base, df[(df.dem == "GLO30_2011-15") & ~df.site_id.isin(base.site_id)]])
    new = df[df.dem.str.match(r"TDX_\d{4}")]
    order = base.sort_values("vol_m3").site_id.tolist()
    y = np.arange(len(order))
    fig, ax = plt.subplots(figsize=(10, 0.55 * len(order) + 1.8))
    fig.patch.set_facecolor("#fcfcfb"); ax.set_facecolor("#fcfcfb")
    left, right = 1000, np.nanmax(df.vol_m3) * 8
    h = 0.38
    for off, sub, col, lab in [(-h / 2 if len(new) else 0, base, "#2a78d6", "2011-15 (TanDEM-X EDEM or GLO-30)"),
                               (h / 2, new, "#eb6834", "DCM date (2019 here)")]:
        if sub.empty:
            continue
        s = sub.set_index("site_id").reindex(order)
        for yi, sid in enumerate(order):
            if sid not in sub.site_id.values:
                continue
            val, e, q = s.loc[sid, "vol_m3"], s.loc[sid, "vol_sigma_total_m3"], s.loc[sid, "quality"]
            poor = q.startswith("poor")
            if val > left:
                ax.barh(yi + off, val, height=h, color=col, hatch="////" if poor else None,
                        edgecolor="#fcfcfb", lw=0)
                txt = f"{round(val, -2):,.0f} ± {round(e, -2):,.0f}"
                ax.text(val * 1.1, yi + off, txt + ("  (poor base)" if poor else "") +
                        ("  (small)" if "small" in q else ""), va="center", fontsize=7, color="#0b0b0b")
            else:
                ax.text(left * 1.1, yi, f"below surrounding ground ({round(val, -2):,.0f} m³)",
                        va="center", fontsize=7, color="#52514e")
    from matplotlib.patches import Patch
    handles = [Patch(color="#2a78d6", label="2011-15 (TanDEM-X EDEM or GLO-30)")]
    if len(new):
        handles.append(Patch(color="#eb6834", label="DCM date (2016-22 acquisition)"))
    handles.append(Patch(facecolor="#2a78d6", hatch="////", edgecolor="#fcfcfb", label="hatched = poor base surface"))
    ax.set_yticks(y, [f"{s}  {NAMES.get(s, '')}" for s in order], fontsize=8)
    ax.set_xscale("log"); ax.set_xlim(left, right)
    ax.set_xlabel("volume above surrounding ground inside the site footprint (m³, log scale)", color="#52514e")
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.grid(axis="x", color="#e5e4e0", lw=0.6); ax.set_axisbelow(True)
    ax.set_ylim(-0.7, len(order) - 0.3)
    ax.legend(handles=handles, fontsize=8, loc="lower right", frameon=False)
    fig.tight_layout(); fig.savefig(path, dpi=200); plt.close(fig)


# ============================================================ main
def main(cfg=CONFIG, only=None):
    os.makedirs(cfg["out"], exist_ok=True)
    allg = read_all_outlines(cfg)
    feet = {s: unary_union(list(d.geometry)) for s, d in allg.groupby("site_id")}
    sites = [s for s in sorted(feet) if not only or s in only]
    all_rows, all_change = [], []
    for sid in sites:
        print(f"== {sid}")
        others = unary_union([f for s, f in feet.items() if s != sid])
        rows, change, info = run_site(cfg, sid, allg[allg.site_id == sid], others)
        all_rows += rows; all_change += change
        for r in rows:
            print(f"   {r['dem']:18s} V = {r['vol_m3']:>12,.0f} ± {r['vol_sigma_total_m3']:>9,} m3   "
                  f"hmax {r['h_max']:6.1f} m   footprint {r['footprint_ha']} ha")
    df = pd.DataFrame(all_rows)
    tag = "" if not only else "_" + "_".join(sites)
    df.to_csv(os.path.join(cfg["out"], f"all_sites_volume_by_dem{tag}.csv"), index=False)
    if all_change:
        pd.DataFrame(all_change).to_csv(os.path.join(cfg["out"], f"all_sites_volume_change{tag}.csv"), index=False)
    summary_chart(df, os.path.join(cfg["out"], f"all_sites_volume_summary{tag}.png"))
    return df, pd.DataFrame(all_change)


if __name__ == "__main__":
    main(only=set(sys.argv[1:]) or None)
