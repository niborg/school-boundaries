"""Shared configuration and helpers.

All distance work is done in EPSG:2229 (NAD83 / California zone 5, US feet).
"""
import csv
import glob
import json
import os

from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.ops import transform

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOUNDARIES = os.path.join(ROOT, "boundaries")
DATA = os.path.join(ROOT, "data")

TO_FEET = Transformer.from_crs(4326, 2229, always_xy=True).transform
TO_WEBMERC = Transformer.from_crs(2229, 3857, always_xy=True).transform

# Single-family use codes in the LA County Assessor roll.
# Single-family residential codes (01xx); see the Assessor use-code list for exact meanings.
SFR_USE_CODES = {"0100", "0101", "0103", "0104"}

# Exclusion thresholds (author's judgment calls; see README).
MIN_TOTAL_VALUE = 300_000
MIN_IMPROVEMENT_VALUE = 50_000

# Each comparison: side A vs side B, the width used on the published map,
# and an optional city polygon that both sides must fall inside.
PAIRS = {
    "south_pasadena": {
        "a": ("SP", "south_pasadena_usd", "South Pasadena Unified"),
        "b": ("LA", "los_angeles_usd", "Los Angeles Unified"),
        "map_width_ft": 800,
        "query_coverage_ft": 800,
        "city": None,
    },
    "palos_verdes": {
        "a": ("PV", "palos_verdes_peninsula_usd", "Palos Verdes Peninsula Unified"),
        "b": ("LA", "los_angeles_usd", "Los Angeles Unified"),
        "map_width_ft": 800,
        "query_coverage_ft": 800,
        "city": None,
    },
    "la_canada": {
        "a": ("LC", "la_canada_usd", "La Cañada Unified"),
        "b": ("GL", "glendale_usd", "Glendale Unified"),
        "map_width_ft": 1300,
        "query_coverage_ft": 1300,
        "city": "la_canada_flintridge_city",
    },
}


def load_boundary(stem):
    with open(os.path.join(BOUNDARIES, stem + ".geojson")) as f:
        g = shape(json.load(f)["geometry"])
    return transform(TO_FEET, g).buffer(0)


def shared_border(a, b, city=None):
    """The shared district line, as a thin polygon (district polygons buffered 60 ft).

    For La Cañada the border is restricted to the stretch inside the city
    (city polygon shrunk 150 ft so the line does not run along the city limit).
    """
    border = a.buffer(60).intersection(b.buffer(60))
    if city is not None:
        border = border.intersection(city.buffer(-150))
    return border


def load_transcribed(pair):
    """Join the two transcribed query outputs for a pair on AIN.

    a*.csv: AIN,lat,lon,Roll_LandValue          (all property types)
    b*.csv: AIN,Roll_ImpValue,UseCode            (single-family codes only)
    """
    folder = os.path.join(DATA, "transcribed", pair)
    loc = {}
    for path in sorted(glob.glob(os.path.join(folder, "a*.csv"))):
        for r in csv.reader(open(path)):
            loc[r[0]] = (float(r[1]), float(r[2]), int(r[3]))
    rows = []
    for path in sorted(glob.glob(os.path.join(folder, "b*.csv"))):
        for r in csv.reader(open(path)):
            ain, imp, use = r[0], int(r[1]), r[2]
            if ain in loc:
                lat, lon, land = loc[ain]
                rows.append({"ain": ain, "lat": lat, "lon": lon, "land": land,
                             "improvements": imp, "use_code": use})
    return rows


def point_ft(lat, lon):
    return Point(*TO_FEET(lon, lat))
