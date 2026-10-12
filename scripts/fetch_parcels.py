"""Download the parcel records from the LA County Assessor's public GIS service.

Usage:
    python scripts/fetch_parcels.py            # strip of 1,300 ft (+100 ft margin) on each side
    python scripts/analyze.py

Writes data/county/<pair>.csv (one row per parcel, county field names) and
data/county/fetch_info.json (when and how the records were pulled). The county
updates the roll as homes sell, so a later run will return a slightly
different set of homes; the committed files are the ones the results use.
"""
import argparse
import csv
import json
import os
import time
from datetime import datetime, timezone

import requests

from common import DATA, PAIRS, SFR_USE_CODES, load_boundary, shared_border

URL = ("https://public.gis.lacounty.gov/public/rest/services/"
       "LACounty_Cache/LACounty_Parcel/MapServer/0/query")
FIELDS = ["AIN", "CENTER_LAT", "CENTER_LON", "UseCode", "TaxRateCity", "TaxRateArea",
          "Roll_Year", "Roll_LandValue", "Roll_ImpValue", "Roll_LandBaseYear", "Roll_ImpBaseYear",
          "SQFTmain1", "SQFTmain2", "YearBuilt1", "Bedrooms1", "Bathrooms1",
          "Shape.STArea()"]
# Shape.STArea() is the parcel's area in square feet (the layer is stored in
# EPSG:2229); it is written out as LotAreaSqft.
COLUMNS = [f if f != "Shape.STArea()" else "LotAreaSqft" for f in FIELDS]
WHERE = ("Roll_LandBaseYear >= '2023' AND UseCode IN ({})"
         .format(",".join(f"'{c}'" for c in sorted(SFR_USE_CODES))))
# Query a little beyond the widest strip analyzed, so that simplifying the
# query polygon cannot clip parcels near the outer edge.
MARGIN_FT = 100


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
                    help="widest strip analyzed, in feet on each side of the line")
    args = ap.parse_args()

    out_dir = os.path.join(DATA, "county")
    os.makedirs(out_dir, exist_ok=True)
    info = {"fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": URL, "where": WHERE, "band_ft": args.width + MARGIN_FT, "parcels": {}}

    for pair, cfg in PAIRS.items():
        A, B = load_boundary(cfg["a"][1]), load_boundary(cfg["b"][1])
        city = load_boundary(cfg["city"]) if cfg["city"] else None
        band = shared_border(A, B, city).buffer(args.width + MARGIN_FT)
        rows = {r["AIN"]: r for r in query(band)}  # a parcel can appear once per ring
        path = os.path.join(out_dir, f"{pair}.csv")
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(COLUMNS)
            for ain in sorted(rows):
                r = rows[ain]
                area = r["Shape.STArea()"]
                r["Shape.STArea()"] = round(area) if area else ""
                w.writerow(["" if r[k] is None else str(r[k]).strip() for k in FIELDS])
        info["parcels"][pair] = len(rows)
        print(f"{pair}: {len(rows)} parcels -> {path}")

    with open(os.path.join(out_dir, "fetch_info.json"), "w") as f:
        json.dump(info, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
