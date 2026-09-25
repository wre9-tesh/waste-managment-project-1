"""
Helpers: OpenStreetMap JSON -> shapely geometries, per-site distance projection, feature classes.
Used by 02_siting_check.py and 03_figures_tables.py.
"""
import json, re
from collections import defaultdict
from shapely.geometry import Point, LineString, Polygon
from shapely.ops import unary_union, linemerge, polygonize
from pyproj import CRS, Transformer
import config as C

# tags whose closed ways are areas (otherwise a closed way is a line, e.g. a ring road)
AREA_KEYS = {"natural": {"water", "wetland", "mud", "bay", "beach", "sand", "scrub", "wood"},
             "landuse": None, "leisure": None, "water": None, "boundary": None, "wetland": None,
             "aeroway": {"aerodrome"}, "military": None, "man_made": {"water_works", "water_well", "wastewater_plant"}}


def is_area(tags):
    if tags.get("area") == "yes":
        return True
    if tags.get("area") == "no" or "highway" in tags or tags.get("natural") == "coastline":
        return False
    if tags.get("waterway") == "riverbank":
        return True
    if "waterway" in tags:
        return False
    return any(k in tags and (v is None or tags[k] in v) for k, v in AREA_KEYS.items())


def _line(m):
    pts = [(p["lon"], p["lat"]) for p in m.get("geometry", []) if p]
    return LineString(pts) if len(pts) >= 2 else None


def element_geometry(e):
    """WGS84 shapely geometry of one Overpass element returned with 'out geom'."""
    t = e.get("tags", {})
    if e["type"] == "node":
        return Point(e["lon"], e["lat"])
    if e["type"] == "way":
        if "geometry" not in e:
            return Point(e["center"]["lon"], e["center"]["lat"]) if "center" in e else None
        pts = [(p["lon"], p["lat"]) for p in e["geometry"]]
        if len(pts) >= 4 and pts[0] == pts[-1] and is_area(t):
            g = Polygon(pts)
            return g if g.is_valid else g.buffer(0)
        return LineString(pts) if len(pts) >= 2 else None
    if e["type"] == "relation":
        members = e.get("members", [])
        outers = [_line(m) for m in members if m["type"] == "way" and m.get("role", "") in ("outer", "", "main_stream", "side_stream")]
        inners = [_line(m) for m in members if m["type"] == "way" and m.get("role") == "inner"]
        outers = [l for l in outers if l is not None]; inners = [l for l in inners if l is not None]
        if not outers:
            return None
        if t.get("type") in ("multipolygon", "boundary") or is_area(t):
            polys = list(polygonize(unary_union(outers)))
            if not polys:            # outer ring not closed (member outside the download) -> keep as lines
                return linemerge(unary_union(outers))
            g = unary_union(polys)
            if inners:
                holes = list(polygonize(unary_union(inners)))
                if holes:
                    g = g.difference(unary_union(holes))
            return g if g.is_valid else g.buffer(0)
        return linemerge(unary_union(outers))
    return None


def site_projection(geom_wgs):
    """Azimuthal equidistant projection centred on the site: distances measured from the site are exact."""
    c = geom_wgs.centroid
    crs = CRS.from_proj4(f"+proj=aeqd +lat_0={c.y:.6f} +lon_0={c.x:.6f} +datum=WGS84 +units=m +no_defs")
    fwd = Transformer.from_crs(4326, crs, always_xy=True).transform
    inv = Transformer.from_crs(crs, 4326, always_xy=True).transform
    return crs, fwd, inv


def name_of(t):
    return (t.get("name:en") or t.get("name") or t.get("official_name") or t.get("ref") or "").strip()


NON_RES_CLASSES = {"industrial", "warehouse", "factory", "manufacture", "service", "shed", "storage_tank", "silo",
                   "transportation", "parking", "hangar", "garage", "garages", "greenhouse", "digester", "power",
                   "substation", "water_tower", "bunker", "military", "construction", "roof", "carport"}


def classify_osm(elements):
    """Sort OSM elements into the feature classes used by the rules. Returns {class: [record, ...]} (WGS84)."""
    out = defaultdict(list)
    for e in elements:
        t = e.get("tags", {})
        g = element_geometry(e)
        if g is None or g.is_empty:
            continue
        rec = dict(geom=g, name=name_of(t), osm=f"{e['type']}/{e['id']}", tags=t)
        ww, nat, wat = t.get("waterway"), t.get("natural"), t.get("water", "")
        lu, le, hw = t.get("landuse"), t.get("leisure"), t.get("highway")
        area = g.geom_type in ("Polygon", "MultiPolygon")
        # R1 river: river centre-lines and river water areas
        if ww in ("river", "riverbank") or (nat == "water" and wat == "river"):
            out["river"].append(rec)
        # other flowing water (reported, not scored)
        if ww in ("stream", "canal", "drain") or (nat == "water" and wat in ("canal", "stream")):
            out["stream_canal"].append(rec)
        # R2 pond: standing water bodies
        if area and ((nat == "water" and wat not in C.NOT_POND and wat in C.POND_WATER_TYPES)
                     or (lu in ("reservoir", "basin") and wat not in C.NOT_POND)):
            out["pond"].append(rec)
        if area and nat == "water" and wat == "wastewater":
            out["wastewater"].append(rec)
        # R3 highway: motorway/trunk/primary, or any road whose ref is NH/SH
        if hw:
            ref = t.get("ref", "") + " " + t.get("name", "")
            is_nh_sh = bool(re.search(C.HIGHWAY_REF_REGEX, ref, re.I)) or "highway" in t.get("name", "").lower()
            if hw in C.HIGHWAY_CLASSES or is_nh_sh:
                rec = dict(rec, nh_sh=is_nh_sh, ref=t.get("ref", ""))
                out["highway"].append(rec)
        # R5 public park
        if area and le in C.PARK_LEISURE:
            out["park"].append(rec)
        # R4 habitation helpers
        if area and lu == "residential":
            out["residential"].append(rec)
        if area and lu == "industrial":
            out["industrial"].append(rec)
        if area and lu == "landfill":
            out["landfill"].append(rec)
        if t.get("place") and g.geom_type == "Point":
            out["place"].append(rec)
        # R10 wetland
        if area and (nat == "wetland" or "wetland" in t):
            out["wetland"].append(rec)
        # R9 coast / tidal
        if nat == "coastline":
            out["coastline"].append(rec)
        if (t.get("tidal") == "yes" or t.get("wetland") in ("mangrove", "tidalflat", "saltmarsh")
                or nat in ("mud", "bay") or ww == "tidal_channel"):
            out["tidal"].append(rec)
        # R6 wells (informative only; not scored)
        if t.get("man_made") == "water_well":
            out["well"].append(rec)
    return out


def load_osm(path):
    return json.load(open(path, encoding="utf-8"))["elements"]


PA_WORDS = re.compile(r"sanctuary|national park|conservation reserve|community reserve|marine|bird|wildlife|"
                      r"biosphere|tiger reserve|wild ass|ramsar|wetlands\b", re.I)


def classify_protected(elements):
    """Split OSM protected areas into legal wildlife PAs (Wildlife Protection Act: national parks, sanctuaries,
    conservation / community reserves) and other protected land (mostly reserved forests)."""
    pa, other = [], []
    for e in elements:
        t = e.get("tags", {})
        g = element_geometry(e)
        if g is None or g.is_empty or g.geom_type not in ("Polygon", "MultiPolygon"):
            continue
        label = " ".join([name_of(t), t.get("protection_title", ""), t.get("designation", "")])
        rec = dict(geom=g, name=name_of(t) or t.get("protection_title", "unnamed"), osm=f"{e['type']}/{e['id']}",
                   title=t.get("protection_title", ""), protect_class=t.get("protect_class", ""), tags=t)
        if (t.get("boundary") == "national_park" or PA_WORDS.search(label)
                or t.get("protect_class") in ("1", "1a", "1b", "2", "4")):
            pa.append(rec)
        else:
            other.append(rec)
    return pa, other


NONRES_LANDUSE = {"industrial", "commercial", "retail", "railway", "quarry", "construction", "brownfield", "landfill",
                  "depot", "garages"}


def nonres_zones(elements):
    """Polygons of land where buildings are not dwellings: industrial/commercial land, plants, works, landfill sites."""
    out = []
    for e in elements:
        t = e.get("tags", {})
        g = element_geometry(e)
        if g is None or g.is_empty:
            continue
        if g.geom_type == "LineString" and g.is_closed and len(g.coords) >= 4:
            g = Polygon(g.coords)
        if g.geom_type not in ("Polygon", "MultiPolygon"):
            continue
        if (t.get("landuse") in NONRES_LANDUSE or t.get("man_made") in ("wastewater_plant", "water_works", "works")
                or t.get("power") in ("plant", "substation", "generator")
                or t.get("amenity") in ("waste_transfer_station", "recycling", "fuel", "bus_station")):
            out.append(dict(geom=g if g.is_valid else g.buffer(0), name=name_of(t), osm=f"{e['type']}/{e['id']}", tags=t))
    return out
