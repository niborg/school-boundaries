"""Classify each parcel by side of the district line, then compute medians.

Usage:
    python scripts/analyze.py                 # uses data/transcribed (the published maps)
    python scripts/analyze.py --source fetched  # uses data/fetched from fetch_parcels.py

Writes:
    data/parcels/<pair>.csv      one row per single-family parcel, with side and distance
    results/summary.csv          medians by pair and strip width
"""
import argparse
import csv
import glob
import os
import statistics as st

from common import (DATA, MIN_IMPROVEMENT_VALUE, MIN_TOTAL_VALUE, PAIRS, ROOT,
                    SFR_USE_CODES, load_boundary, load_transcribed, point_ft,
                    shared_border)

WIDTHS = [500, 600, 800, 1000, 1200, 1300]


def load_fetched(pair):
    rows = []
    for path in glob.glob(os.path.join(DATA, "fetched", pair, "*.csv")):
        for r in csv.DictReader(open(path)):
            lat, lon = [float(x) for x in r["LAT_LON"].split(",")]
            rows.append({"ain": r["AIN"], "lat": lat, "lon": lon,
                         "land": int(r["Roll_LandValue"] or 0),
                         "improvements": int(r["Roll_ImpValue"] or 0),
                         "use_code": r["UseCode"],
                         "sqft": r.get("SQFTmain1", "")})
    # de-duplicate parcels that fell in two query tiles
    return list({r["ain"]: r for r in rows}.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["transcribed", "fetched"], default="transcribed")
    args = ap.parse_args()

    os.makedirs(os.path.join(DATA, "parcels"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    summary = []

    for pair, cfg in PAIRS.items():
        (ka, sa, na), (kb, sb, nb) = cfg["a"], cfg["b"]
        A, B = load_boundary(sa), load_boundary(sb)
        city = load_boundary(cfg["city"]) if cfg["city"] else None
        border = shared_border(A, B, city)

        rows = load_transcribed(pair) if args.source == "transcribed" else load_fetched(pair)
        out = []
        for r in rows:
            if r["use_code"] not in SFR_USE_CODES:
                continue
            p = point_ft(r["lat"], r["lon"])
            side = ka if A.contains(p) else kb if B.contains(p) else "other"
            total = r["land"] + r["improvements"]
            keep = (total >= MIN_TOTAL_VALUE and r["improvements"] >= MIN_IMPROVEMENT_VALUE
                    and side != "other" and (city is None or city.contains(p)))
            out.append({**r, "total": total, "side": side,
                        "dist_to_line_ft": round(p.distance(border)),
                        "in_city": "" if city is None else city.contains(p),
                        "included": keep})

        fields = ["ain", "lat", "lon", "use_code", "land", "improvements", "total",
                  "side", "dist_to_line_ft", "in_city", "included"]
        if args.source == "fetched":
            fields.insert(6, "sqft")
        suffix = "" if args.source == "transcribed" else "_fetched"
        with open(os.path.join(DATA, "parcels", f"{pair}{suffix}.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(sorted(out, key=lambda r: r["ain"]))

        # The transcribed queries only covered the band out to query_coverage_ft,
        # so wider strips would be incomplete. Fetched data can go wider.
        widths = [w for w in WIDTHS if args.source == "fetched" or w <= cfg["query_coverage_ft"]]
        for width in widths:
            meds = {}
            for k in (ka, kb):
                v = [r["total"] for r in out if r["included"] and r["side"] == k
                     and r["dist_to_line_ft"] <= width]
                meds[k] = (len(v), st.median(v) if v else None)
            (n_a, m_a), (n_b, m_b) = meds[ka], meds[kb]
            summary.append({
                "pair": pair, "source": args.source, "width_ft": width,
                "side_a": na, "n_a": n_a, "median_a": round(m_a) if m_a else "",
                "side_b": nb, "n_b": n_b, "median_b": round(m_b) if m_b else "",
                "gap_dollars": round(m_a - m_b) if m_a and m_b else "",
                "gap_pct": round(100 * (m_a / m_b - 1), 1) if m_a and m_b else "",
                "on_published_map": width == cfg["map_width_ft"],
            })

    path = os.path.join(ROOT, "results", f"summary{'' if args.source == 'transcribed' else '_fetched'}.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0]))
        w.writeheader()
        w.writerows(summary)
    for s in summary:
        print(s)


if __name__ == "__main__":
    main()
