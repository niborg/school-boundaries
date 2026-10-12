"""Classify each parcel by side of the district line, then compare values.

Usage:
    python scripts/analyze.py

Reads data/county/<pair>.csv (written by fetch_parcels.py). Writes:
    data/parcels/<pair>.csv      one row per single-family parcel, with side and distance
    results/summary.csv          medians, gaps and 95% intervals by pair and strip width

Side of the line. Each home's centroid is placed in a district using the 2012
Census lines. A tax-rate area is one combination of taxing agencies, so it lies
in a single school district. Where a tax-rate area holds homes that the Census
line puts on both sides, the line is off by a few feet there, and every home in
that area is moved to the side holding most of them.

Two gaps are reported for each strip:
    gap_pct      difference between the two sides' median assessed values, with a
                 bootstrap 95% interval (homes resampled within each side)
    adj_*_pct    the side difference from a regression of log(assessed value) on
                 side plus log(home square feet) [adj_home] or plus log(home square
                 feet) and log(lot square feet) [adj_home_lot], with a 95% interval
                 from heteroskedasticity-robust (HC1) standard errors
"""
import collections
import csv
import os
import statistics as st

import numpy as np

from common import (DATA, MIN_IMPROVEMENT_VALUE, MIN_TOTAL_VALUE, PAIRS, ROOT,
                    SFR_USE_CODES, load_boundary, load_county, point_ft,
                    shared_border)

WIDTHS = [500, 600, 800, 1000, 1200, 1300]
BOOTSTRAP_REPS = 5000


def median_gap_interval(va, vb, seed):
    rng = np.random.default_rng(seed)
    va, vb = np.array(va), np.array(vb)
    ma = np.median(va[rng.integers(0, len(va), (BOOTSTRAP_REPS, len(va)))], axis=1)
    mb = np.median(vb[rng.integers(0, len(vb), (BOOTSTRAP_REPS, len(vb)))], axis=1)
    return np.percentile(ma / mb - 1, [2.5, 97.5])


def adjusted_gap(rows, side_a, controls):
    """exp(b) - 1 and its 95% interval, where b is the side-A coefficient in
    log(total) = c + b*[side A] + sum_k g_k*log(control_k)."""
    rows = [r for r in rows if all(r[c] > 0 for c in controls)]
    y = np.log([r["total"] for r in rows])
    X = np.column_stack([np.ones(len(rows)), [r["side"] == side_a for r in rows]]
                        + [np.log([r[c] for r in rows]) for c in controls]).astype(float)
    n, k = X.shape
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    resid = y - X @ beta
    xtx_inv = np.linalg.inv(X.T @ X)
    cov = xtx_inv @ (X * resid[:, None] ** 2).T @ X @ xtx_inv * n / (n - k)
    b, se = beta[1], np.sqrt(cov[1, 1])
    return np.exp([b, b - 1.96 * se, b + 1.96 * se]) - 1


def correct_sides(rows, ka, kb):
    """Move homes to the majority side of their tax-rate area (see module docstring)."""
    by_tra = collections.defaultdict(collections.Counter)
    for r in rows:
        if r["side"] in (ka, kb):
            by_tra[r["tax_rate_area"]][r["side"]] += 1
    moved = []
    for r in rows:
        counts = by_tra.get(r["tax_rate_area"])
        if r["side"] in (ka, kb) and counts and len(counts) == 2 and counts[ka] != counts[kb]:
            majority = counts.most_common(1)[0][0]
            if r["side"] != majority:
                moved.append((r["ain"], r["side"], majority))
                r["side"] = majority
    return moved


def pct(x):
    return round(100 * float(x), 1)


def summarize(pair, variant, cfg, strip, width):
    (ka, _, na), (kb, _, nb) = cfg["a"], cfg["b"]
    a = [r for r in strip if r["side"] == ka]
    b = [r for r in strip if r["side"] == kb]
    va, vb = [r["total"] for r in a], [r["total"] for r in b]
    m_a, m_b = st.median(va), st.median(vb)
    lo, hi = median_gap_interval(va, vb, seed=width)
    home = adjusted_gap(strip, ka, ["home_sqft"])
    home_lot = adjusted_gap(strip, ka, ["home_sqft", "lot_sqft"])
    return {
        "pair": pair, "variant": variant, "width_ft": width, "side_a": na, "side_b": nb,
        "n_a": len(a), "n_b": len(b),
        "median_a": round(m_a), "median_b": round(m_b),
        "gap_dollars": round(m_a - m_b), "gap_pct": pct(m_a / m_b - 1),
        "gap_pct_lo": pct(lo), "gap_pct_hi": pct(hi),
        "median_home_sqft_a": round(st.median(r["home_sqft"] for r in a)),
        "median_home_sqft_b": round(st.median(r["home_sqft"] for r in b)),
        "median_lot_sqft_a": round(st.median(r["lot_sqft"] for r in a)),
        "median_lot_sqft_b": round(st.median(r["lot_sqft"] for r in b)),
        "adj_home_pct": pct(home[0]), "adj_home_pct_lo": pct(home[1]),
        "adj_home_pct_hi": pct(home[2]),
        "adj_home_lot_pct": pct(home_lot[0]), "adj_home_lot_pct_lo": pct(home_lot[1]),
        "adj_home_lot_pct_hi": pct(home_lot[2]),
        "on_map": width == cfg["map_width_ft"] and variant == cfg.get("map_variant", "all"),
    }


def main():
    os.makedirs(os.path.join(DATA, "parcels"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    summary = []

    for pair, cfg in PAIRS.items():
        (ka, sa, na), (kb, sb, nb) = cfg["a"], cfg["b"]
        A, B = load_boundary(sa), load_boundary(sb)
        city = load_boundary(cfg["city"]) if cfg["city"] else None
        border = shared_border(A, B, city)
        opt_side, opt_city, opt_name = cfg.get("optional_area") or (None, None, None)

        out = []
        for r in load_county(pair):
            if r["use_code"] not in SFR_USE_CODES:
                continue
            p = point_ft(r["lat"], r["lon"])
            side = ka if A.contains(p) else kb if B.contains(p) else "other"
            out.append({**r, "total": r["land"] + r["improvements"], "side": side,
                        "side_by_census_line": side,
                        "dist_to_line_ft": round(p.distance(border)),
                        "in_city": "" if city is None else city.contains(p)})
        for ain, old, new in correct_sides(out, ka, kb):
            print(f"{pair}: {ain} moved {old} -> {new} (tax-rate area)")
        for r in out:
            r["included"] = (r["total"] >= MIN_TOTAL_VALUE
                             and r["improvements"] >= MIN_IMPROVEMENT_VALUE
                             and r["side"] != "other" and (city is None or r["in_city"]))
            r["optional_area"] = (opt_name if r["side"] == opt_side
                                  and r["tax_rate_city"] == opt_city else "")

        fields = ["ain", "lat", "lon", "use_code", "tax_rate_city", "tax_rate_area",
                  "land_base_year", "land", "improvements", "total", "home_sqft", "lot_sqft",
                  "year_built", "side_by_census_line", "side", "optional_area",
                  "dist_to_line_ft", "in_city", "included"]
        with open(os.path.join(DATA, "parcels", f"{pair}.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(sorted(out, key=lambda r: r["ain"]))

        variants = [("all", lambda r: True)]
        if opt_name:
            variants += [(f"excluding {opt_name}", lambda r: not r["optional_area"]),
                         (f"side B = {opt_name} only", lambda r: r["side"] == ka or r["optional_area"])]
        for variant, keep in variants:
            for width in WIDTHS:
                strip = [r for r in out if r["included"] and keep(r)
                         and r["dist_to_line_ft"] <= width]
                summary.append(summarize(pair, variant, cfg, strip, width))

    with open(os.path.join(ROOT, "results", "summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0]))
        w.writeheader()
        w.writerows(summary)

    print(f"\n{'pair':34} {'width':>5} {'n_a':>4} {'n_b':>4}  {'raw gap (95% CI)':24} "
          f"{'home size adj':24} {'home+lot adj':24}")
    for s in summary:
        def fmt(k):
            return f"{s[k]:+6.1f}% ({s[k + '_lo']:+.0f} to {s[k + '_hi']:+.0f})"
        label = s["pair"] + ("" if s["variant"] == "all" else f" ({s['variant']})")
        print(f"{label:34} {s['width_ft']:5} {s['n_a']:4} {s['n_b']:4}  "
              f"{fmt('gap_pct'):24} {fmt('adj_home_pct'):24} {fmt('adj_home_lot_pct'):24}"
              f"{'  <- map' if s['on_map'] else ''}")


if __name__ == "__main__":
    main()
