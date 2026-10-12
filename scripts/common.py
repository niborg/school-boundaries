"""Shared configuration and helpers.

All distance work is done in EPSG:2229 (NAD83 / California zone 5, US feet).
"""
import csv
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

# LA County Assessor use codes kept as single-family homes. The county labels
# every 01xx code "Single"; these are the plain detached codes. Condominiums
# (010C) and the other 01xx variants are left out.
SFR_USE_CODES = {"0100", "0101", "0103", "0104"}

# Exclusion thresholds (author's judgment calls; see README).
MIN_TOTAL_VALUE = 300_000
MIN_IMPROVEMENT_VALUE = 50_000

# Each comparison: side A vs side B, the width shown on the map, an optional
# city polygon that both sides must fall inside, and map labels placed in
# axes-fraction coordinates (x, y, text).
PAIRS = {
    "south_pasadena": {
        "a": ("SP", "south_pasadena_usd", "South Pasadena Unified"),
        "b": ("LA", "los_angeles_usd", "Los Angeles Unified"),
        "map_width_ft": 800,
        "city": None,
        "title": "A few blocks apart, a different school district:\n"
                 "homes within 800 feet of the South Pasadena–LAUSD line",
        "places": [(0.03, 0.655, "Highland Park · Garvanza"),
                   (0.50, 0.035, "Hermon · El Sereno")],
    },
    "palos_verdes": {
        "a": ("PV", "palos_verdes_peninsula_usd", "Palos Verdes Peninsula Unified"),
        "b": ("LA", "los_angeles_usd", "Los Angeles Unified"),
        "map_width_ft": 800,
        "city": None,
        "title": "Across the line: homes within 800 feet of the\n"
                 "Palos Verdes Peninsula–LAUSD boundary",
        # Eastview: the part of Rancho Palos Verdes inside LAUSD. State law makes it
        # an optional attendance area whose students may choose PVPUSD instead.
        "optional_area": ("LA", "RANCHO PALOS VERDES", "Eastview"),
        "map_variant": "excluding Eastview",
        "places": [(0.97, 0.975, "Lomita · Harbor City"),
                   (0.03, 0.30, "Rancho Palos Verdes")],
    },
    "la_canada": {
        "a": ("LC", "la_canada_usd", "La Cañada Unified"),
        "b": ("GL", "glendale_usd", "Glendale Unified"),
        "map_width_ft": 1300,
        "city": "la_canada_flintridge_city",
        "title": "Same city, different school district:\n"
                 "La Cañada Flintridge homes on each side of the school line",
        "b_note": '("Sagebrush")',
        "places": [(0.03, 0.035, "Dashed line = La Cañada Flintridge city limit\n"
                                 "La Crescenta lies to the west")],
    },
}


def load_boundary(stem):
    with open(os.path.join(BOUNDARIES, stem + ".geojson")) as f:
        g = shape(json.load(f)["geometry"])
    return transform(TO_FEET, g).buffer(0)


def shared_border(a, b, city=None):
    """The shared district line, as a thin polygon (district polygons buffered 60 ft).

    With a city (La Cañada), only the line between district A and the part of
    district B inside the city is used: here, the line between La Cañada Unified
    and Sagebrush. The city polygon is shrunk 150 ft first so that stretches
    where the district line runs along the city limit drop out.
    """
    if city is not None:
        b = b.intersection(city.buffer(-150))
    return a.buffer(60).intersection(b.buffer(60))


def _int(s):
    return int(s) if s not in ("", None) else 0


def load_county(pair):
    """Parcel records written by fetch_parcels.py."""
    rows = []
    with open(os.path.join(DATA, "county", f"{pair}.csv")) as f:
        for r in csv.DictReader(f):
            rows.append({
                "ain": r["AIN"], "lat": float(r["CENTER_LAT"]), "lon": float(r["CENTER_LON"]),
                "use_code": r["UseCode"], "tax_rate_city": r["TaxRateCity"],
                "tax_rate_area": r["TaxRateArea"],
                "land_base_year": r["Roll_LandBaseYear"],
                "land": _int(r["Roll_LandValue"]), "improvements": _int(r["Roll_ImpValue"]),
                "home_sqft": _int(r["SQFTmain1"]) + _int(r["SQFTmain2"]),
                "lot_sqft": _int(r["LotAreaSqft"]),
                "year_built": r["YearBuilt1"],
            })
    return rows


def point_ft(lat, lon):
    return Point(*TO_FEET(lon, lat))
