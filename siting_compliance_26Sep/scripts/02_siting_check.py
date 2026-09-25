"""
Step 02 - check every dumpsite outline against the SWM Rules 2026 landfill siting criteria.

For each site and for the 2026 outline (main) and the 2016 outline (comparison):
  distance from the outline edge to the nearest river, pond, NH/SH highway, habitation, public park, airport/airbase;
  overlap with the JRC 100-year flood extent, CRZ screening zone, wetlands, protected areas (and their eco-sensitive zone).
All distances are measured in a per-site azimuthal equidistant projection (exact distances from the site centre).

Writes to outputs/tables/:
  siting_long.csv              one row per site x epoch x rule (measured value, nearest feature, verdict, basis)
  siting_matrix_2026.csv       site x rule verdicts for the 2026 outline + counts
  siting_matrix_2016.csv       same for the 2016 outline
  siting_summary.csv           breach counts per site, 2016 and 2026
  nearest_features_2026.csv    nearest-feature distances (m) for every rule, 2026 outline
  habitation_detail.csv        building counts within 50/100/200/500 m and threshold sensitivity
  airports.csv                 aerodromes used, with distance to every site
  protected_areas.csv          wildlife protected areas within 15 km of any site
and writes outputs/sites/<SITE>/<SITE>_layers.geojson (features used, WGS84) for checking in QGIS / Google Earth.
"""
import json, os
import numpy as np
import pandas as pd
import rasterio, rasterio.features, rasterio.windows
from shapely import from_wkb
from shapely.geometry import shape, mapping, Point
from shapely.ops import transform, unary_union
from pyproj import Transformer
import config as C
import outlines as O
import geo_utils as G

os.makedirs(C.TABLES, exist_ok=True); os.makedirs(C.SITES_OUT, exist_ok=True)
by_epoch, _ = O.read_outlines(C.KML)
union = O.footprints(by_epoch)
SITES = sorted(union)
RULES = {r["id"]: r for r in C.RULES}

# ------------------------------------------------------------------ Gujarat-wide layers
pa_list, pa_other = G.classify_protected(G.load_osm(os.path.join(C.RAW, "osm", "gujarat_protected.json")))

aero = []
for e in G.load_osm(os.path.join(C.RAW, "osm", "gujarat_aerodromes.json")):
    t = e.get("tags", {})
    g = G.element_geometry(e)
    if g is None:
        continue
    if g.geom_type == "LineString" and g.is_closed:
        from shapely.geometry import Polygon
        g = Polygon(g.coords)
    closed = t.get("disused:aeroway") or t.get("abandoned:aeroway") or "disused" in t.get("aeroway", "")
    military = t.get("military") in ("airfield", "base") or t.get("aerodrome:type") == "military" \
        or t.get("landuse") == "military" or "air force" in G.name_of(t).lower()
    aero.append(dict(geom=g, name=G.name_of(t), iata=t.get("iata", ""), icao=t.get("icao", ""), military=military,
                     aerodrome_type=t.get("aerodrome:type", t.get("aerodrome", "")), osm=f"{e['type']}/{e['id']}",
                     closed=bool(closed)))
# keep every aerodrome that is not closed/abandoned (airports, airbases and airstrips); classify it with OurAirports
ourair = pd.read_csv(os.path.join(C.RAW, "ourairports_IN.csv"))
ourair = ourair[ourair["type"].isin(C.AIRPORT_TYPES)]
AIRPORTS = []
for a in aero:
    if a["closed"] or "abandon" in a["name"].lower() or "helipad" in a["name"].lower():
        continue
    c = a["geom"].centroid
    dd = ((ourair.latitude_deg - c.y) ** 2 + ((ourair.longitude_deg - c.x) * np.cos(np.radians(c.y))) ** 2) ** 0.5 * 111.2
    j = dd.idxmin() if len(dd) else None
    oa = ourair.loc[j] if j is not None and (dd[j] < 4 or (a["icao"] and a["icao"] == ourair.loc[j, "ident"])) else None
    sched = oa is not None and oa["scheduled_service"] == "yes"
    a["ourairports"] = (oa["ident"] + " " + oa["name"]) if oa is not None else ""
    a["arp"] = Point(oa["longitude_deg"], oa["latitude_deg"]) if oa is not None else a["geom"].centroid
    a["kind"] = ("airport, scheduled flights" if sched else ("airport, no scheduled flights" if (a["icao"] or a["iata"])
                                                             else "airstrip")) \
        + ("; military use" if (a["military"] or "air force" in a["name"].lower()) else "")
    AIRPORTS.append(a)

flood_tiles = [rasterio.open(os.path.join(C.RAW, "jrc_flood", f)) for f in C.JRC_FLOOD_CLIPS]
perm_tiles = [rasterio.open(os.path.join(C.RAW, "jrc_flood", f)) for f in C.JRC_PERM_CLIPS]


def raster_polys(tiles, geom_wgs, margin_deg, test):
    """Polygons (WGS84) of raster cells satisfying test(values) within the geometry bounds + margin."""
    x0, y0, x1, y1 = geom_wgs.bounds
    polys = []
    for r in tiles:
        b = r.bounds
        if x1 + margin_deg < b.left or x0 - margin_deg > b.right:
            continue
        win = rasterio.windows.from_bounds(max(x0 - margin_deg, b.left), max(y0 - margin_deg, b.bottom),
                                           min(x1 + margin_deg, b.right), min(y1 + margin_deg, b.top), r.transform)
        win = win.round_offsets().round_lengths()
        a = r.read(1, window=win)
        m = test(a, r.nodata).astype("uint8")
        if m.any():
            for gj, v in rasterio.features.shapes(m, mask=m.astype(bool), transform=r.window_transform(win)):
                polys.append(shape(gj))
    return unary_union(polys) if polys else None


def max_value(tiles, geom_wgs):
    vals = []
    for r in tiles:
        b = r.bounds
        if not (geom_wgs.bounds[0] <= b.right and geom_wgs.bounds[2] >= b.left):
            continue
        from rasterio.mask import mask as rmask
        try:
            a, _ = rmask(r, [mapping(geom_wgs)], crop=True, all_touched=True, nodata=r.nodata)
            a = a[0]; a = a[(a != r.nodata) & np.isfinite(a)]
            if a.size:
                vals.append(float(a.max()))
        except ValueError:
            pass
    return max(vals) if vals else 0.0


def nearest(recs, out, P, keep=None):
    """(distance m, record) of the nearest feature to the outline; keep = optional filter on projected geometry."""
    best = (np.inf, None)
    for r in recs:
        g = P(r["geom"])
        if keep is not None and not keep(g, r):
            continue
        d = out.distance(g)
        if d < best[0]:
            best = (d, dict(r, pgeom=g))
    return best


def fmt_d(d):
    return None if not np.isfinite(d) else round(float(d), 1)


rows, habit_rows, near_rows, pa_rows = [], [], [], []
layers_out = {}
airport_dist = {}

for s in SITES:
    osm = G.classify_osm(G.load_osm(os.path.join(C.RAW, "osm", f"{s}_local.json")))
    bdf = pd.read_parquet(os.path.join(C.RAW, "buildings", f"{s}.parquet"))
    bld_wgs = [from_wkb(bytes(g)) for g in bdf["geometry"]]
    union_wgs = transform(O.inv, union[s])
    crs, fwd, inv = G.site_projection(union_wgs)
    P = lambda g: transform(fwd, g)
    uni = P(union_wgs)
    facility = uni.buffer(C.FACILITY_BUFFER)
    # non-residential zones (OSM): industrial / commercial land, treatment plants, power plants, landfill facilities
    nonres_recs = G.nonres_zones(G.load_osm(os.path.join(C.RAW, "osm", f"{s}_nonres.json")))
    nonres = unary_union([P(r["geom"]) for r in nonres_recs + osm["industrial"]]) \
        if (nonres_recs or osm["industrial"]) else None
    ghsl_r = rasterio.open(os.path.join(C.RAW, "ghsl", f"{s}_ghsl_fun_2018.tif"))
    ghsl_a = ghsl_r.read(1)
    to_moll = Transformer.from_crs(4326, ghsl_r.crs, always_xy=True).transform

    def ghsl_class(pt):
        """GHSL 2018 functional class under a point: 0 not built, 1 residential, 2 non-residential."""
        x, y = to_moll(pt.x, pt.y)
        row, col = ghsl_r.index(x, y)
        return int(ghsl_a[row, col]) if 0 <= row < ghsl_a.shape[0] and 0 <= col < ghsl_a.shape[1] else 255

    bld, n_tank, n_class = [], 0, 0
    for g, cls, src in zip(bld_wgs, bdf["class"], bdf["source"]):
        pg = P(g)
        if pg.intersects(facility):
            continue                                    # sheds / trommels on the dumpsite itself
        if isinstance(cls, str) and cls in G.NON_RES_CLASSES:
            n_class += 1
            continue                                    # mapped as a non-residential building type
        if pg.area >= C.TANK_MIN_M2 and 4 * np.pi * pg.area / pg.length ** 2 >= C.TANK_COMPACTNESS:
            n_tank += 1
            continue                                    # circular structure = tank / clarifier / silo, not a dwelling
        in_ind = nonres is not None and nonres.contains(pg.centroid)
        bld.append(dict(pgeom=pg, cls=cls, source=src, industrial=in_ind, ghsl=ghsl_class(g.centroid)))
    flood_wgs = raster_polys(flood_tiles, union_wgs, 0.03, lambda a, nd: (a != nd) & np.isfinite(a) & (a > C.FLOOD_MIN_DEPTH))
    perm_wgs = raster_polys(perm_tiles, union_wgs, 0.03, lambda a, nd: (a != nd) & (a > 0))
    flood_p = P(flood_wgs) if flood_wgs is not None else None
    perm_p = P(perm_wgs) if perm_wgs is not None else None
    # airports: distance from the union centre to all airports (for the table)
    airport_dist[s] = {a["name"] or a["icao"]: P(transform(O.inv, by_epoch[(s, C.MAIN_EPOCH)])).distance(P(a["arp"]))
                       for a in AIRPORTS}

    for ep in (C.MAIN_EPOCH, C.COMPARE_EPOCH):
        if (s, ep) not in by_epoch:
            continue
        out = P(transform(O.inv, by_epoch[(s, ep)]))
        area_ha = out.area / 1e4
        res = {}

        def put(rid, verdict, value=None, unit="m", feature="", n_within=None, basis="", extra=None):
            res[rid] = dict(site=s, name=O.NAMES[s], epoch=ep, outline_ha=round(area_ha, 2), rule_id=rid,
                            rule=RULES[rid]["rule"], limit=RULES[rid]["limit"], value=value, unit=unit,
                            nearest_feature=feature, n_within_limit=n_within, verdict=verdict, basis=basis,
                            **(extra or {}))

        # R1 river --------------------------------------------------------------------------------
        d, r = nearest(osm["river"], out, P)
        n = sum(out.distance(P(x["geom"])) < 100 for x in osm["river"])
        rname = "none within 2.5 km"
        if r:
            rname = r["name"]
            if not rname:      # unnamed river polygon/line: borrow the name of the nearest named river line within 500 m
                named = [(r["pgeom"].distance(P(x["geom"])), x["name"]) for x in osm["river"] if x["name"]]
                named = [x for x in named if x[0] < 500]
                rname = (min(named)[1] + " (unnamed OSM part)") if named else "unnamed river (OSM)"
        put("R1", "breach" if d < 100 else "ok", fmt_d(d), feature=rname, n_within=n,
            basis="OSM waterway=river / river water areas")
        # R2 pond ---------------------------------------------------------------------------------
        def pond_ok(g, rec):
            if g.area < C.MIN_POND_M2:
                return False
            return g.intersection(uni).area < 0.5 * g.area          # water mostly inside the dump = on-site leachate/pit water
        d, r = nearest(osm["pond"], out, P, pond_ok)
        onsite = [x for x in osm["pond"] if P(x["geom"]).area >= C.MIN_POND_M2 and not pond_ok(P(x["geom"]), x)]
        n = sum(1 for x in osm["pond"] if pond_ok(P(x["geom"]), x) and out.distance(P(x["geom"])) < 200)
        put("R2", "breach" if d < 200 else "ok", fmt_d(d),
            feature=((r["name"] or ("unnamed water body (" + (r["tags"].get("water") or r["tags"].get("landuse") or "natural=water") + f", {P(r['geom']).area/1e4:.1f} ha)")) if r else "none within 2.5 km"), n_within=n,
            basis="OSM natural=water (pond/lake/reservoir/unspecified) and landuse=reservoir/basin, >= 100 m2"
                  + (f"; {len(onsite)} water body(ies) lying mostly inside the dump ignored" if onsite else ""))
        # R3 highway ------------------------------------------------------------------------------
        d, r = nearest(osm["highway"], out, P)
        d_strict, r_strict = nearest(osm["highway"], out, P, lambda g, rec: rec["nh_sh"] or
                                     rec["tags"].get("highway", "").startswith(("motorway", "trunk")))
        n = sum(out.distance(P(x["geom"])) < 200 for x in osm["highway"])
        lab = (lambda rr: (f"{rr['name']} ({rr['tags'].get('highway')}" + (f", {rr['ref']}" if rr.get("ref") else "") + ")")
               if rr else "none within 2.5 km")
        put("R3", "breach" if d < 200 else "ok", fmt_d(d), feature=lab(r), n_within=n,
            basis="OSM motorway/trunk/primary (OSM India: trunk = NH, primary = SH) or ref NH/SH",
            extra=dict(alt_value=fmt_d(d_strict), alt_verdict=("breach" if d_strict < 200 else "ok"),
                       alt_basis="strict: only motorway/trunk or roads with an NH/SH ref", alt_feature=lab(r_strict)))
        # R4 habitation ---------------------------------------------------------------------------
        dist_b = np.array([out.distance(b["pgeom"]) for b in bld]) if bld else np.array([])
        resid = np.array([not b["industrial"] for b in bld], bool) if bld else np.array([], bool)
        nb = {k: int(((dist_b < k) & resid).sum()) for k in (50, 100, 200, 500)}
        nb_all200 = int((dist_b < 200).sum()) if bld else 0
        gcls = np.array([b["ghsl"] for b in bld]) if bld else np.array([])
        nb_ghsl = {k: int(((dist_b < 200) & resid & (gcls == k)).sum()) for k in (0, 1, 2)} if bld else {0: 0, 1: 0, 2: 0}
        d_b = float(dist_b[resid].min()) if resid.any() else np.inf
        d_res, r_res = nearest(osm["residential"], out, P)
        d_place, r_place = nearest(osm["place"], out, P)
        n_res = nb_ghsl[1]                                   # residential buildings within 200 m
        auto = "breach" if n_res >= C.HAB_MIN_BUILDINGS else "ok"
        review, rnote = C.HABITATION_REVIEW.get(s, ("not reviewed", ""))
        v = "check" if (auto == "breach" and review == "uncertain") else auto
        put("R4", v, fmt_d(d_b),
            feature=f"{n_res} residential buildings within 200 m (of {nb[200]} buildings); nearest building {fmt_d(d_b)} m",
            n_within=n_res,
            basis=f"Overture buildings outside the dumpsite (+{C.FACILITY_BUFFER:.0f} m), not circular tanks, outside OSM "
                  "industrial / commercial / plant / landfill land, on a GHSL-2018 residential cell; "
                  f">= {C.HAB_MIN_BUILDINGS} = breach; imagery review 'uncertain' -> check",
            extra=dict(auto_verdict=auto, imagery_review=review, imagery_note=rnote, osm_residential_m=fmt_d(d_res)))
        habit_rows.append(dict(site=s, epoch=ep, buildings_50m=nb[50], buildings_100m=nb[100], buildings_200m=nb[200],
                               buildings_500m=nb[500], buildings_200m_incl_nonres_zones=nb_all200,
                               circular_tanks_dropped=n_tank, nonres_class_dropped=n_class,
                               bld200_on_ghsl_residential=nb_ghsl[1], bld200_on_ghsl_nonresidential=nb_ghsl[2],
                               bld200_on_ghsl_not_built_2018=nb_ghsl[0],
                               nearest_building_m=fmt_d(d_b), nearest_osm_residential_m=fmt_d(d_res),
                               osm_residential_name=(r_res["name"] if r_res else ""),
                               nearest_osm_place_m=fmt_d(d_place), osm_place=(r_place["name"] if r_place else ""),
                               residential_buildings_200m=nb_ghsl[1], imagery_review=review, imagery_note=rnote,
                               **{f"auto_if_>={k}_residential": ("breach" if nb_ghsl[1] >= k else "ok") for k in C.HAB_SENS},
                               **{f"auto_if_>={k}_any_building": ("breach" if nb[200] >= k else "ok") for k in C.HAB_SENS}))
        # R5 park ---------------------------------------------------------------------------------
        d, r = nearest(osm["park"], out, P)
        n = sum(out.distance(P(x["geom"])) < 200 for x in osm["park"])
        put("R5", "breach" if d < 200 else "ok", fmt_d(d),
            feature=((r["name"] or "unnamed " + r["tags"].get("leisure", "park")) if r else "none within 2.5 km"), n_within=n,
            basis="OSM leisure=park / recreation_ground")
        # R6 wells (not assessable) ---------------------------------------------------------------
        d, r = nearest(osm["well"], out, P)
        put("R6", "not assessable", fmt_d(d), feature=(f"OSM-mapped well at {fmt_d(d)} m (mapping incomplete)" if r else
                                                       "no public map of water-supply wells"),
            basis="no complete open dataset of water-supply wells; OSM man_made=water_well shown for information only")
        # R7 airport ------------------------------------------------------------------------------
        # main: distance to the aerodrome reference point (ARP) - the reference used by the Aircraft Rules 1937 (rule 91,
        # no garbage within 10 km of the ARP); sensitivity: distance to the aerodrome boundary (OSM polygon)
        best = (np.inf, None)
        for a in AIRPORTS:
            dd = out.distance(P(a["arp"]))
            if dd < best[0]:
                best = (dd, a)
        d, a = best
        d_bnd = min(out.distance(P(x["geom"])) for x in AIRPORTS)
        v = "breach" if d < C.AIRPORT_NOC_MIN_M else ("conditional" if d < 20000 else "ok")
        v_bnd = "breach" if d_bnd < C.AIRPORT_NOC_MIN_M else ("conditional" if d_bnd < 20000 else "ok")
        put("R7", v, round(d / 1000, 2) if np.isfinite(d) else None, unit="km",
            feature=(f"{a['name']} ({(a['icao'] or a['iata'] or 'no code')}; {a['kind']})" if a else ""),
            basis="aerodromes from OSM (airports, airbases, airstrips; not abandoned), distance to the aerodrome reference "
                  "point (OurAirports); < 10 km = breach; 10-20 km = allowed only with a NOC (conditional)",
            extra=dict(alt_value=round(d_bnd / 1000, 2), alt_verdict=v_bnd,
                       alt_basis="distance to the nearest aerodrome boundary (OSM polygon)", airport_kind=(a["kind"] if a else "")))
        # R8 flood plain --------------------------------------------------------------------------
        if flood_p is not None and not flood_p.is_empty:
            ov = out.intersection(flood_p).area
            frac = ov / out.area
            d = out.distance(flood_p)
            dmax = max_value(flood_tiles, transform(inv, out))
            v = "breach" if frac >= C.FLOOD_MIN_FRAC else ("check" if frac > 0 else "ok")
            put("R8", v, round(100 * frac, 1), unit="% of outline in 100-yr flood extent",
                feature=f"overlap {ov/1e4:.2f} ha; nearest flooded cell {fmt_d(d)} m; max depth under outline {dmax:.1f} m",
                basis="JRC/Copernicus global river flood hazard map v2.1.2, 100-year return period, 90 m; "
                      ">= 10% of outline = breach, 0-10% = edge overlap (check)",
                extra=dict(flood_overlap_ha=round(ov / 1e4, 2), flood_nearest_m=fmt_d(d), flood_max_depth_m=round(dmax, 2)))
        else:
            put("R8", "ok", 0.0, unit="% of outline in 100-yr flood extent", feature="no modelled 100-yr flooding within ~3 km",
                basis="JRC/Copernicus global river flood hazard map v2.1.2, 100-year return period, 90 m")
        # R9 CRZ (screening) ----------------------------------------------------------------------
        d_c, r_c = nearest(osm["coastline"], out, P)
        d_t, r_t = nearest(osm["tidal"], out, P)
        crz = (d_c < C.CRZ_SEA_M) or (d_t < C.CRZ_TIDAL_M)
        put("R9", "breach" if crz else "ok", fmt_d(min(d_c, d_t)),
            feature=(f"coastline {fmt_d(d_c)} m" if np.isfinite(d_c) else "no coastline within 2.5 km")
                    + "; " + (f"tidal feature {fmt_d(d_t)} m" if np.isfinite(d_t) else "no tidal feature within 2.5 km")
                    + (f" ({r_t['name']})" if r_t and r_t['name'] else ""),
            basis=f"SCREENING: within {C.CRZ_SEA_M:.0f} m of the OSM coastline or {C.CRZ_TIDAL_M:.0f} m of OSM tidal features "
                  "(CRZ Notification 2019); official CZMP High Tide Line maps not used")
        # R10 wetland -----------------------------------------------------------------------------
        d, r = nearest(osm["wetland"], out, P)
        put("R10", "breach" if d == 0 else "ok", fmt_d(d),
            feature=((r["name"] or ("wetland: " + r["tags"].get("wetland", "unspecified"))) if r else "none within 2.5 km"),
            basis="OSM natural=wetland (incl. mangrove, marsh, tidal flat, salt marsh); breach = outline overlaps it")
        # R11 critical habitat / eco-fragile ------------------------------------------------------
        d, r = nearest(pa_list, out, P)
        v = "breach" if d < C.ESZ_MIN_M else ("check" if d < C.ESZ_DEFAULT_M else "ok")
        put("R11", v, round(d / 1000, 2) if np.isfinite(d) else None, unit="km",
            feature=(f"{r['name']}" + (f" ({r['title']})" if r['title'] else "") if r else "none in Gujarat list"),
            basis="OSM protected areas (national parks, sanctuaries, reserves) in Gujarat; inside or < 1 km (minimum ESZ, "
                  "SC order 3 June 2022) = breach; 1-10 km = check the notified ESZ (10 km default, MoEFCC 2011)")
        if ep == C.MAIN_EPOCH:
            for x in pa_list:
                dd = out.distance(P(x["geom"]))
                if dd < 15000:
                    pa_rows.append(dict(site=s, protected_area=x["name"], title=x["title"], protect_class=x["protect_class"],
                                        osm=x["osm"], distance_km=round(dd / 1000, 2)))
            d_o, r_o = nearest(pa_other, out, P)
            res["R11"]["other_protected_land"] = (f"{r_o['name']} at {d_o/1000:.2f} km" if r_o and d_o < 15000 else "")
        # R12 land-use plan (not assessable) ------------------------------------------------------
        lf, rlf = nearest(osm["landfill"], out, P)
        put("R12", "not assessable", None, unit="",
            feature=("OSM marks the site as landuse=landfill" if lf == 0 else "not tagged as landfill in OSM"),
            basis="needs the town-planning Development Plan / TP scheme maps; not available as open GIS data")

        rows.extend(res.values())
        if ep == C.MAIN_EPOCH:
            near_rows.append(dict(site=s, name=O.NAMES[s], outline_2026_ha=round(area_ha, 2),
                                  river_m=res["R1"]["value"], pond_m=res["R2"]["value"], highway_m=res["R3"]["value"],
                                  highway_strict_m=res["R3"].get("alt_value"),
                                  habitation_m=res["R4"]["value"], buildings_within_200m=res["R4"]["n_within_limit"],
                                  habitation_review=res["R4"]["imagery_review"],
                                  park_m=res["R5"]["value"], airport_km=res["R7"]["value"], airport_boundary_km=res["R7"].get("alt_value"),
                                  airport=res["R7"]["nearest_feature"],
                                  flood_overlap_pct=res["R8"]["value"], crz_screen_m=res["R9"]["value"],
                                  wetland_m=res["R10"]["value"], protected_area_km=res["R11"]["value"],
                                  protected_area=res["R11"]["nearest_feature"]))
            # ---- layers for checking (WGS84)
            feats = []
            def add(g, **p):
                if g is not None and not g.is_empty:
                    feats.append(dict(type="Feature", properties=p, geometry=mapping(transform(inv, g))))
            add(out, layer="outline_2026", site=s)
            add(uni, layer="union_2016_2026", site=s)
            for k in (100, 200):
                add(out.buffer(k).difference(out), layer=f"buffer_{k}m", site=s)
            clip = out.buffer(C.LOCAL_RADIUS)
            for cls in ("river", "pond", "highway", "park", "residential", "wetland", "coastline", "tidal", "stream_canal"):
                for x in osm[cls]:
                    g = P(x["geom"])
                    if g.intersects(clip):
                        lay = cls
                        if cls == "pond" and not pond_ok(g, x):
                            lay = "pond_ignored"          # < 100 m2 or lying mostly inside the dump
                        add(g.intersection(clip), layer=lay, name=x["name"], osm=x["osm"],
                            distance_m=round(out.distance(g), 1))
            if nonres is not None:
                add(nonres.intersection(clip), layer="nonresidential_zone")
            for b in bld:
                dd = out.distance(b["pgeom"])
                if dd < 500:
                    add(b["pgeom"], layer="building", distance_m=round(dd, 1), source=b["source"],
                        in_industrial_zone=b["industrial"], ghsl_2018=b["ghsl"])
            if flood_p is not None:
                add(flood_p.intersection(clip), layer="flood_100yr")
            if perm_p is not None:
                add(perm_p.intersection(clip), layer="permanent_water_jrc")
            for x in pa_list:
                g = P(x["geom"])
                if out.distance(g) < 15000:
                    add(g, layer="protected_area", name=x["name"], distance_m=round(out.distance(g), 1))
            for a in AIRPORTS:
                g = P(a["geom"])
                if out.distance(P(a["arp"])) < 30000:
                    add(g, layer="airport", name=a["name"], icao=a["icao"], distance_m=round(out.distance(g), 1))
                    add(P(a["arp"]), layer="airport_reference_point", name=a["name"], icao=a["icao"],
                        distance_m=round(out.distance(P(a["arp"])), 1))
            os.makedirs(os.path.join(C.SITES_OUT, s), exist_ok=True)
            json.dump(dict(type="FeatureCollection", features=feats),
                      open(os.path.join(C.SITES_OUT, s, f"{s}_layers.geojson"), "w"))
    print(f"{s}: {len(bld)} buildings outside the facility ({n_tank} circular tanks dropped, "
          f"{sum(b['industrial'] for b in bld)} in non-residential zones); flood cells {'yes' if flood_p is not None else 'none'}",
          flush=True)

long = pd.DataFrame(rows)
long.to_csv(os.path.join(C.TABLES, "siting_long.csv"), index=False)

SCORED = [r["id"] for r in C.RULES if r["kind"] != "na"]


def matrix(ep):
    m = long[long.epoch == ep].pivot(index="site", columns="rule_id", values="verdict")[[r["id"] for r in C.RULES]]
    m.insert(0, "name", [O.NAMES[s] for s in m.index])
    sc = m[SCORED]
    m["breaches"] = (sc == "breach").sum(axis=1)
    m["conditional_or_check"] = sc.isin(["conditional", "check"]).sum(axis=1)
    m["ok"] = (sc == "ok").sum(axis=1)
    m["assessed"] = len(SCORED)
    m["breached_rules"] = sc.apply(lambda r: ", ".join(RULES[k]["rule"] for k in SCORED if r[k] == "breach"), axis=1)
    m["conditional_rules"] = sc.apply(lambda r: ", ".join(RULES[k]["rule"] for k in SCORED
                                                          if r[k] in ("conditional", "check")), axis=1)
    return m


m26, m16 = matrix(C.MAIN_EPOCH), matrix(C.COMPARE_EPOCH)
m26.to_csv(os.path.join(C.TABLES, "siting_matrix_2026.csv"))
m16.to_csv(os.path.join(C.TABLES, "siting_matrix_2016.csv"))
summ = pd.DataFrame(dict(name=m26["name"], breaches_2026=m26["breaches"], conditional_or_check_2026=m26["conditional_or_check"],
                         breaches_2016=m16["breaches"], conditional_or_check_2016=m16["conditional_or_check"],
                         breached_rules_2026=m26["breached_rules"], conditional_rules_2026=m26["conditional_rules"]))
summ["city_group"] = ["five most populous" if s[:3] in C.MAJOR else "other cities" for s in summ.index]
summ.to_csv(os.path.join(C.TABLES, "siting_summary.csv"))
pd.DataFrame(near_rows).to_csv(os.path.join(C.TABLES, "nearest_features_2026.csv"), index=False)
pd.DataFrame(habit_rows).to_csv(os.path.join(C.TABLES, "habitation_detail.csv"), index=False)
pd.DataFrame(pa_rows).sort_values(["site", "distance_km"]).to_csv(os.path.join(C.TABLES, "protected_areas.csv"), index=False)
ap = pd.DataFrame([dict(name=a["name"], icao=a["icao"], iata=a["iata"], kind=a["kind"], ourairports=a["ourairports"], osm=a["osm"],
                        **{f"dist_km_{s}": round(airport_dist[s][a["name"] or a["icao"]] / 1000, 2) for s in SITES})
                   for a in AIRPORTS])
ap.to_csv(os.path.join(C.TABLES, "airports.csv"), index=False)
print(summ[["breaches_2026", "conditional_or_check_2026", "breaches_2016", "breached_rules_2026"]].to_string())
print("rule counts 2026:", {k: int((m26[k] == "breach").sum()) for k in SCORED})
