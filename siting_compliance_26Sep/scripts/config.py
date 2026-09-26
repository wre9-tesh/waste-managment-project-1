"""
Settings shared by all siting-compliance scripts (siting_compliance_26Sep, 26 Sep 2026).
Every path, data source, rule threshold and search radius is defined here.

Rules checked: Solid Waste Management Rules, 2026 (MoEFCC notification S.O. 388(E), 27 January 2026),
Schedule II 'Specifications for Sanitary Landfills', Part (A) 'Criteria for site selection', clauses (vii) and (viii).
Same list as Lecture 8, slide 39-40 ("Landfill siting rules (SWM 2026 rules)").
"""
import os

# ---------------------------------------------------------------- folders
SCRIPTS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPTS)                       # ...\Project 1\siting_compliance_26Sep
PROJECT = os.path.dirname(ROOT)                       # ...\Project 1
KML = os.path.join(PROJECT, "Locations of landfills in gujurat Completed.kml")   # master outlines
if not os.path.exists(KML):        # the GitHub copy of the same file is named '... completer.kml'
    KML = os.path.join(PROJECT, "Locations of landfills in gujurat completer.kml")
DATA = os.path.join(ROOT, "data")
RAW = os.path.join(DATA, "raw")                       # downloaded layers (step 01)
OUT = os.path.join(ROOT, "outputs")
TABLES = os.path.join(OUT, "tables")
SITES_OUT = os.path.join(OUT, "sites")
FIG = os.path.join(ROOT, "figures")
LOGS = os.path.join(ROOT, "logs")

# ---------------------------------------------------------------- outlines (same rules as the area and volume runs)
EPOCHS = [2016, 2018, 2020, 2022, 2024, 2026]
EPOCH_MAP = {2025: 2024}           # a 2025 image is used as the 2024 epoch
MAIN_EPOCH = 2026                  # "currently" = the 2026 traced outline
COMPARE_EPOCH = 2016               # comparison run on the 2016 outline (same feature data)
FACILITY_BUFFER = 20.0             # m; buildings inside the all-epoch union + 20 m are treated as dumpsite sheds, not habitation

# ---------------------------------------------------------------- search radii around each outline (download step)
LOCAL_RADIUS = 2500.0              # m; rivers, ponds, roads, parks, wetlands, coast, OSM buildings
BUILDING_RADIUS = 600.0            # m; Overture building footprints
GUJARAT_BBOX = (19.8, 68.0, 24.9, 74.6)   # south, west, north, east; protected areas and aerodromes are fetched for all of it

# ---------------------------------------------------------------- data sources
OVERPASS_URLS = ["https://maps.mail.ru/osm/tools/overpass/api/interpreter",   # public Overpass mirrors, tried in order
                 "https://overpass-api.de/api/interpreter",
                 "https://overpass.kumi.systems/api/interpreter"]
OVERTURE_RELEASE = None            # None = newest release found in the public S3 bucket (logged in data/sources.json)
OVERTURE_BUCKET = "s3://overturemaps-us-west-2/release/{rel}/theme=buildings/type=building/*"
GHSL_FUN_URL = ("https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_BUILT_C_GLOBE_R2023A/"
                "GHS_BUILT_C_FUN_E2018_GLOBE_R2023A_54009_10/V1-0/GHS_BUILT_C_FUN_E2018_GLOBE_R2023A_54009_10_V1_0/"
                "GHS_BUILT_C_FUN_E2018_GLOBE_R2023A_54009_10_V1_0.tif")
OURAIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
JRC_TILES = ("ID178_N30_E60", "ID184_N30_E70")               # JRC tiles covering the 14 sites, clipped to Gujarat by step 01
JRC_FLOOD_CLIPS = [f"{t}_RP100_depth_gujarat.tif" for t in JRC_TILES]
JRC_PERM_CLIPS = [f"{t}_permanent_water_gujarat.tif" for t in JRC_TILES]
UTM = "EPSG:32643"                 # WGS 84 / UTM 43N - used only for areas (same as area analysis);
                                   # distances use a per-site azimuthal equidistant projection (exact distances from the site)

# ---------------------------------------------------------------- the 12 siting rules
# kind: 'dist'  = breach if the nearest feature is closer than 'min_m' to the outline
#       'zone'  = breach if the outline overlaps the zone (distance 0, i.e. inside)
#       'na'    = not assessable from open data (reported, not scored)
RULES = [
    dict(id="R1",  rule="River",                       limit="100 m",  kind="dist", min_m=100),
    dict(id="R2",  rule="Pond",                        limit="200 m",  kind="dist", min_m=200),
    dict(id="R3",  rule="Highway (NH / SH)",           limit="200 m",  kind="dist", min_m=200),
    dict(id="R4",  rule="Habitation",                  limit="200 m",  kind="dist", min_m=200),
    dict(id="R5",  rule="Public park",                 limit="200 m",  kind="dist", min_m=200),
    dict(id="R6",  rule="Water-supply well",           limit="200 m",  kind="na",   min_m=200),
    dict(id="R7",  rule="Airport / airbase",           limit="20 km (10-20 km only with NOC)", kind="dist", min_m=20000),
    dict(id="R8",  rule="Flood plain (100-year)",      limit="not permitted", kind="zone", min_m=0),
    dict(id="R9",  rule="Coastal Regulation Zone",     limit="not permitted", kind="zone", min_m=0),
    dict(id="R10", rule="Wetland",                     limit="not permitted", kind="zone", min_m=0),
    dict(id="R11", rule="Critical habitat / eco-fragile area", limit="not permitted", kind="zone", min_m=0),
    dict(id="R12", rule="In town-planning land-use plan", limit="required", kind="na", min_m=0),
]

# ---------------------------------------------------------------- how each feature class is defined (OpenStreetMap tags)
HIGHWAY_CLASSES = {"motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link"}
HIGHWAY_REF_REGEX = r"(?<![A-Za-z])(NH|SH|NE)(?![A-Za-z])"   # any road also counts if its ref/name carries NH/SH (e.g. SH142, sh-219)
POND_WATER_TYPES = {"pond", "lake", "reservoir", "basin", "lagoon", "oxbow", ""}   # natural=water with these water=* values
NOT_POND = {"river", "canal", "stream", "ditch", "drain", "wastewater", "moat", "fountain", "stream_pool"}
PARK_LEISURE = {"park", "recreation_ground"}
MIN_POND_M2 = 100.0                # ignore mapped water < 100 m2 (tanks, fountains)

# ---------------------------------------------------------------- habitation decision (R4)
HAB_MIN_BUILDINGS = 5              # breach if >= 5 RESIDENTIAL building footprints lie within 200 m of the outline:
                                   # Overture footprint, outside the dumpsite (+20 m), not a circular tank, not in OSM
                                   # industrial/commercial/plant land, and standing on a GHSL 'residential' cell (2018)
HAB_SENS = (1, 5, 20)              # sensitivity: result with 1, 5 and 20 buildings as the threshold
# Imagery review of the buildings inside the 200 m ring (Esri World Imagery at zoom 17, 26 Sep 2026, by Claude; TO BE
# CONFIRMED by the student in Google Earth Pro). 'uncertain' turns an automatic breach into 'check'; 'not residential'
#                                  gives 'ok' (buildings are not dwellings). AHM-02, AHM-03, SUR-02, VAP-01 set by the student 26 Sep.
HABITATION_REVIEW = {
    "AHM-01": ("confirmed", "dense housing on the east / south-east edge; industrial units elsewhere (excluded)"),
    "AHM-02": ("not residential", "student imagery check 26 Sep: structures within 200 m are not dwellings (Pirana STP to the west, sheds north and south-east)"),
    "AHM-03": ("not residential", "student imagery check 26 Sep: structures in the walled yard just north are not dwellings (waste-handling / scrap yard)"),
    "BHJ-01": ("confirmed", "houses of the residential area to the south"),
    "BHV-01": ("none", "no buildings inside the 200 m ring"),
    "GNR-01": ("confirmed", "dense cluster of small dwellings along the west edge"),
    "JAM-01": ("confirmed", "residential plots and houses to the south and west"),
    "MEH-01": ("confirmed", "houses to the north-west"),
    "RAJ-01": ("none", "structures in the ring are the processing-plant buildings on the east side"),
    "SUR-01": ("confirmed", "most mapped structures are Bhatar STP units, but dense housing lies inside the ring to the south-west"),
    "SUR-02": ("not residential", "student imagery check 26 Sep: the cluster south of the southern cell is not residential; north side industrial"),
    "VAD-01": ("likely", "scattered houses / farm buildings to the north and west"),
    "VAD-02": ("confirmed", "apartments and houses to the west and south"),
    "VAP-01": ("confirmed", "student imagery check 26 Sep: residential buildings within 200 m to the south-east"),
}
TANK_MIN_M2 = 100.0                # footprints >= 100 m2 that are near-circular are tanks / clarifiers / silos, not dwellings
TANK_COMPACTNESS = 0.88            # 4*pi*A/P^2: circle = 1.0, octagon ~0.95, square 0.785 (houses stay in)

# ---------------------------------------------------------------- airports (R7)
AIRPORT_NOC_MIN_M = 10000          # 10-20 km: allowed only with NOC -> reported as 'conditional'
AIRPORT_TYPES = {"large_airport", "medium_airport", "small_airport"}   # OurAirports types kept (heliports, closed, seaplane bases dropped)

# ---------------------------------------------------------------- Coastal Regulation Zone screening (R9)
# CRZ Notification 2019: CRZ extends 500 m landward of the High Tide Line (HTL) on the sea front, and along tidal-influenced
# water bodies up to 50 m (or the width of the creek, if less); intertidal areas are CRZ-I B. Official HTL maps (CZMP) are not
# public in GIS form, so this is a SCREENING using OSM coastline / tidal features.
CRZ_SEA_M = 500.0                  # m from the OSM coastline
CRZ_TIDAL_M = 50.0                 # m from tidal creeks, mangroves, tidal flats, salt marsh (OSM)

# ---------------------------------------------------------------- critical habitat / eco-fragile (R11)
ESZ_MIN_M = 1000.0                 # Supreme Court, 3 June 2022 (T.N. Godavarman, IA 1000/2003): minimum 1 km Eco-Sensitive Zone
ESZ_DEFAULT_M = 10000.0            # MoEFCC 2011 guidelines: 10 km applies where no ESZ is notified -> reported as 'check'
# Review of the 1-10 km 'check' results: sites confirmed to lie inside the eco-sensitive zone -> breach (student, 26 Sep 2026)
ESZ_REVIEW = {
    "JAM-01": ("inside ESZ", "student check 26 Sep: the landfill lies in the eco-sensitive zone of Khijadiya Wildlife Sanctuary (5.4 km)"),
}

# ---------------------------------------------------------------- flood plain (R8)
FLOOD_MIN_DEPTH = 0.0              # m; any modelled water depth > 0 in the JRC 100-year map counts as flood plain
FLOOD_MIN_FRAC = 0.10              # breach if >= 10% of the outline lies in the flood extent; 0-10% = edge overlap (check)

# ---------------------------------------------------------------- reporting
MAJOR = {"AHM", "SUR", "VAD", "RAJ", "BHV"}   # five most populous cities
