"""Download the parcel records directly from the LA County Assessor's public GIS service.

This is the step the original analysis could NOT do directly (see README,
"How the published numbers were produced"). Running it lets you rebuild every
number from the county's own data, and adds square footage so you can check
whether house size explains the gap.

NOTE: this script was written but not run by its author, because the
environment it was written in could not reach the county server. Expect to
fix small things on first run.

Usage:
    python scripts/fetch_parcels.py --width 1300
    python scripts/analyze.py --source fetched
"""
import argparse
import csv
import json
import os
import time

import requests
from shapely.geometry import mapping

from common import DATA, PAIRS, load_boundary, shared_border

URL = ("https://public.gis.lacounty.gov/public/rest/services/"
       "LACounty_Cache/LACounty_Parcel/MapServer/0/query")
FIELDS = ["AIN", "LAT_LON", "UseCode", "Roll_LandValue", "Roll_ImpValue",
          "Roll_LandBaseYear", "Roll_ImpBaseYear", "SQFTmain1", "YearBuilt1",
          "Bedrooms1", "Bathrooms1"]
WHERE = ("Roll_LandBaseYear >= '2023' AND "
         "UseCode IN ('0100','0101','0103','0104')")


def esri_polygon(poly):
    """shapely polygon in EPSG:2229 -> Esri JSON polygon (simplified to keep requests small)."""
    poly = poly.simplify(50)
    geoms = [poly] if poly.geom_type == "Polygon" else list(poly.geoms)
    rings = []
    for g in geoms:
        rings.append([list(c) for c in g.exterior.coords])
        rings.extend([list(c) for c in i.coords] for i in g.interiors)
    return {"rings": rings, "spatialReference": {"wkid": 2229}}


def query(polygon):
    rows, offset = [], 0
    while True:
        params = {
            "where": WHERE,
            "geometry": json.dumps(esri_polygon(polygon)),
            "geometryType": "esriGeometryPolygon",
            "inSR": 2229,
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": ",".join(FIELDS),
            "returnGeometry": "false",
            "resultOffset": offset,
            "resultRecordCount": 1000,
            "orderByFields": "OBJECTID",
            "f": "json",
        }
        r = requests.post(URL, data=params, timeout=120)
        r.raise_for_status()
        js = r.json()
        if "error" in js:
            raise RuntimeError(js["error"])
        feats = [f["attributes"] for f in js.get("features", [])]
        rows.extend(feats)
        if not js.get("exceededTransferLimit") and len(feats) < 1000:
            return rows
        offset += len(feats)
        time.sleep(0.5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=float, default=1300,
                    help="strip width in feet on each side of the line")
    args = ap.parse_args()

    for pair, cfg in PAIRS.items():
        A, B = load_boundary(cfg["a"][1]), load_boundary(cfg["b"][1])
        city = load_boundary(cfg["city"]) if cfg["city"] else None
        band = shared_border(A, B, city).buffer(args.width)
        rows = query(band)
        out_dir = os.path.join(DATA, "fetched", pair)
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, "parcels.csv")
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
        print(f"{pair}: {len(rows)} parcels -> {path}")


if __name__ == "__main__":
    main()
