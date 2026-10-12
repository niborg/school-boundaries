"""Redraw the three maps from data/parcels/<pair>.csv (run analyze.py first).

Usage: python scripts/make_maps.py
Writes maps/<pair>.png. The originally published images are also in maps/.
"""
import csv
import os
import statistics as st

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
from matplotlib.colors import Normalize
from shapely.geometry import box

from common import DATA, PAIRS, ROOT, TO_FEET, load_boundary, shared_border

COLORS = {"a_fill": "#FBE9DD", "b_fill": "#DCE6F2", "a_band": "#F2B48C",
          "b_band": "#9DB9DB", "a_text": "#8A2E08", "b_text": "#1B4B8A"}
SCALE = {"south_pasadena": (700_000, 2_600_000), "palos_verdes": (800_000, 2_600_000),
         "la_canada": (1_000_000, 4_000_000)}


def polys(g):
    if g.is_empty:
        return []
    return [g] if g.geom_type == "Polygon" else [p for p in g.geoms if p.geom_type == "Polygon"]


def draw(pair, cfg):
    (ka, sa, na), (kb, sb, nb) = cfg["a"], cfg["b"]
    width = cfg["map_width_ft"]
    A, B = load_boundary(sa), load_boundary(sb)
    city = load_boundary(cfg["city"]) if cfg["city"] else None
    border = shared_border(A, B, city)

    rows = [r for r in csv.DictReader(open(os.path.join(DATA, "parcels", f"{pair}.csv")))
            if r["included"] == "True" and float(r["dist_to_line_ft"]) <= width]
    pts = [(*TO_FEET(float(r["lon"]), float(r["lat"])), int(r["total"]), r["side"]) for r in rows]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    pad = 2500
    view = box(min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)
    band = border.buffer(width)
    if city is not None:
        band = band.intersection(city)
    band = band.intersection(view)

    fig, ax = plt.subplots(figsize=(10, 12), dpi=150)
    ax.set_facecolor("#EEF1F4")
    for g, c in [(A, COLORS["a_fill"]), (B, COLORS["b_fill"])]:
        for p in polys(g.intersection(view)):
            ax.fill(*p.exterior.xy, color=c, zorder=1)
    for g, c in [(band.intersection(A), COLORS["a_band"]), (band.intersection(B), COLORS["b_band"])]:
        for p in polys(g):
            ax.fill(*p.exterior.xy, color=c, alpha=.75, lw=0, zorder=2)
    if city is not None:
        cl = city.boundary.intersection(view)
        for l in getattr(cl, "geoms", [cl]):
            ax.plot(*l.xy, color="#4A5568", lw=1.5, ls=(0, (5, 4)), zorder=4)
    line = A.boundary.intersection(B.buffer(80)).intersection(view)
    for l in getattr(line, "geoms", [line]):
        if l.geom_type == "LineString":
            ax.plot(*l.xy, color="#0F1B2D", lw=3, zorder=5)
    sc = ax.scatter(xs, ys, c=[p[2] for p in pts], cmap="inferno_r",
                    norm=Normalize(*SCALE[pair]), s=70, edgecolor="#0F1B2D", lw=.8, zorder=6)

    med = {k: st.median([p[2] for p in pts if p[3] == k]) for k in (ka, kb)}
    n = {k: sum(1 for p in pts if p[3] == k) for k in (ka, kb)}
    # put each label on its own side of the map (A's centroid relative to the view)
    a_left = A.intersection(view).centroid.x < view.centroid.x
    vx0, vy0, vx1, vy1 = view.bounds
    for k, name, color, left in [(ka, na, COLORS["a_text"], a_left), (kb, nb, COLORS["b_text"], not a_left)]:
        ax.text(vx0 + 300 if left else vx1 - 300, vy1 - 300,
                f"{name.upper()}\nmedian \\${med[k] / 1e6:.2f}M\n{n[k]} homes",
                ha="left" if left else "right", va="top", fontsize=12,
                fontweight="bold", color=color, zorder=8, linespacing=1.35)
    ax.plot([vx1 - 1300, vx1 - 300], [vy0 + 500] * 2, color="#0F1B2D", lw=3, zorder=8)
    ax.text(vx1 - 800, vy0 + 700, "1,000 ft", ha="center", fontsize=9, zorder=8)
    ax.set_xlim(vx0, vx1); ax.set_ylim(vy0, vy1); ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(sc, ax=ax, orientation="horizontal", fraction=.03, pad=.02, aspect=45)
    cb.ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v / 1e6:.1f}M"))
    cb.set_label("Assessed value (land + improvements) of each single-family home reassessed since 2023")
    gap = med[ka] / med[kb] - 1
    fig.suptitle(f"{na} vs {nb}: homes within {width:,} ft of the district line\n"
                 f"Median gap: \\${(med[ka] - med[kb]) / 1e3:,.0f}K ({gap:+.0%})",
                 x=.06, ha="left", fontsize=15, fontweight="bold")
    fig.text(.06, .01, "Source: LA County Assessor parcel roll; Census TIGER 2012 school districts. "
             "Not adjusted for home or lot size. See README.", fontsize=8, color="#4A5568")
    out = os.path.join(ROOT, "maps", f"{pair}.png")
    fig.savefig(out, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(pair, "->", out, med, n)


if __name__ == "__main__":
    for pair, cfg in PAIRS.items():
        draw(pair, cfg)
