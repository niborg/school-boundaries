"""Draw the three maps from data/parcels/<pair>.csv and results/summary.csv.

Usage: python scripts/make_maps.py   (run analyze.py first)
Writes maps/<pair>.png.
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
          "b_band": "#9DB9DB", "a_text": "#8A2E08", "b_text": "#1B4B8A",
          "ink": "#0F1B2D", "muted": "#4A5568", "other": "#EEF1F4"}
SCALE = {"south_pasadena": (750_000, 2_600_000), "palos_verdes": (800_000, 2_600_000),
         "la_canada": (1_000_000, 4_000_000)}
MIN_ASPECT = 0.85  # map width / height, so the side labels have room
# Where each side's label goes, in axes fractions: (x, y, horizontal alignment),
# and the district name as printed when it needs a line break.
LABELS = {"south_pasadena": {"a": (0.97, 0.62, "right"), "b": (0.03, 0.80, "left")},
          "palos_verdes": {"a": (0.03, 0.56, "left", "Palos Verdes\nPeninsula Unified"),
                           "b": (0.97, 0.56, "right")},
          "la_canada": {"a": (0.97, 0.66, "right"), "b": (0.03, 0.27, "left")}}


def polys(g):
    if g.is_empty:
        return []
    return [g] if g.geom_type == "Polygon" else [p for p in g.geoms if p.geom_type == "Polygon"]


def money(v):
    return f"${v / 1e6:.2f}M" if v >= 1e6 else f"${v / 1e3:,.0f}K"


def summary_row(pair, cfg):
    with open(os.path.join(ROOT, "results", "summary.csv")) as f:
        for s in csv.DictReader(f):
            if s["pair"] == pair and s["on_map"] == "True":
                return s
    raise LookupError(pair)


def draw(pair, cfg):
    (ka, sa, na), (kb, sb, nb) = cfg["a"], cfg["b"]
    width = cfg["map_width_ft"]
    A, B = load_boundary(sa), load_boundary(sb)
    city = load_boundary(cfg["city"]) if cfg["city"] else None
    border = shared_border(A, B, city)
    s = summary_row(pair, cfg)
    opt_name = (cfg.get("optional_area") or (None, None, None))[2]

    with open(os.path.join(DATA, "parcels", f"{pair}.csv")) as f:
        rows = [r for r in csv.DictReader(f)
                if r["included"] == "True" and float(r["dist_to_line_ft"]) <= width]
    pts = [(*TO_FEET(float(r["lon"]), float(r["lat"])), int(r["total"]), r["side"],
            bool(r["optional_area"])) for r in rows]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    pad = 2500
    x0, y0, x1, y1 = min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad
    extra = max(0, MIN_ASPECT * (y1 - y0) - (x1 - x0)) / 2
    view = box(x0 - extra, y0, x1 + extra, y1)
    band = border.buffer(width)
    if city is not None:
        band = band.intersection(city)
    band = band.intersection(view)

    fig, ax = plt.subplots(figsize=(10, 12.5), dpi=150)
    ax.set_facecolor(COLORS["other"])
    for g, c in [(A, COLORS["a_fill"]), (B, COLORS["b_fill"])]:
        for p in polys(g.intersection(view)):
            ax.fill(*p.exterior.xy, color=c, zorder=1)
    for g, c in [(band.intersection(A), COLORS["a_band"]), (band.intersection(B), COLORS["b_band"])]:
        for p in polys(g):
            ax.fill(*p.exterior.xy, color=c, alpha=.75, lw=0, zorder=2)
    if city is not None:
        cl = city.boundary.intersection(view)
        for l in getattr(cl, "geoms", [cl]):
            ax.plot(*l.xy, color=COLORS["muted"], lw=1.5, ls=(0, (5, 4)), zorder=4)
    line = A.boundary.intersection(B.buffer(80)).intersection(view)
    for l in getattr(line, "geoms", [line]):
        if l.geom_type == "LineString":
            ax.plot(*l.xy, color=COLORS["ink"], lw=3, zorder=5)
    norm = Normalize(*SCALE[pair])
    for opt, marker, size in [(False, "o", 70), (True, "s", 52)]:
        sel = [p for p in pts if p[4] == opt]
        if sel:
            sc = ax.scatter([p[0] for p in sel], [p[1] for p in sel], c=[p[2] for p in sel],
                            cmap="inferno_r", norm=norm, marker=marker, s=size,
                            edgecolor=COLORS["ink"], lw=.8, zorder=6)

    for k, name, color in [("a", na, COLORS["a_text"]), ("b", nb, COLORS["b_text"])]:
        x, y, ha, *display = LABELS[pair][k]
        note = cfg.get("b_note") if k == "b" else None
        text = (display[0] if display else name).upper() + (f"\n{note}" if note else "")
        if k == "b" and opt_name:
            text += f"\n(not counting {opt_name})"
        text += f"\nmedian {money(int(s['median_' + k]))}\n{s['n_' + k]} homes"
        ax.text(x, y, text, transform=ax.transAxes, ha=ha, va="top", fontsize=15,
                fontweight="bold", color=color, zorder=8, linespacing=1.45)
    for x, y, text in cfg.get("places", []):
        ha = "left" if x < .4 else "right" if x > .6 else "center"
        ax.text(x, y, text, transform=ax.transAxes, ha=ha, va="top" if y > .5 else "bottom",
                fontsize=11, color=COLORS["muted"], zorder=8)
    if opt_name:
        ev = [p[2] for p in pts if p[4]]
        ax.text(.97, .36, f"Squares: {opt_name}, the part of\nRancho Palos Verdes inside LAUSD.\n"
                f"Its families may choose PVPUSD.\n"
                f"Median {money(st.median(ev))}, {len(ev)} homes.",
                transform=ax.transAxes, ha="right", va="top", fontsize=10.5,
                color=COLORS["b_text"], zorder=8, linespacing=1.4)
    vx0, vy0, vx1, vy1 = view.bounds
    ax.plot([vx1 - 1300, vx1 - 300], [vy0 + 500] * 2, color=COLORS["ink"], lw=3, zorder=8)
    ax.text(vx1 - 800, vy0 + 700, "1,000 ft", ha="center", fontsize=10, zorder=8)
    ax.set_xlim(vx0, vx1); ax.set_ylim(vy0, vy1); ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    cb = fig.colorbar(sc, ax=ax, orientation="horizontal", fraction=.03, pad=.02, aspect=45)
    cb.ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v / 1e6:.1f}M"))
    cb.set_label("Assessed value (land + improvements) of each single-family home "
                 "reassessed since 2023", fontsize=10)

    gap = float(s["gap_pct"])
    fig.suptitle(cfg["title"], x=.06, y=.995, ha="left", fontsize=19, fontweight="bold",
                 color=COLORS["ink"], linespacing=1.25)
    fig.text(.06, .925,
             f"The {na} side's median is \\${int(s['gap_dollars']) / 1e3:,.0f}K ({gap:+.0f}%) higher "
             f"(95% range {float(s['gap_pct_lo']):+.0f}% to {float(s['gap_pct_hi']):+.0f}%).\n"
             f"Compared at equal home and lot size, the gap is {float(s['adj_home_lot_pct']):+.0f}% "
             f"({float(s['adj_home_lot_pct_lo']):+.0f}% to {float(s['adj_home_lot_pct_hi']):+.0f}%).",
             ha="left", va="top", fontsize=12, color=COLORS["muted"], linespacing=1.45)
    fig.text(.06, .005,
             "Source: LA County Assessor parcel roll (public GIS service), single-family use codes "
             "0100, 0101, 0103, 0104, land base year 2023 or later\n(usually a sale in 2023 or later); "
             "value = assessed land + improvements; excludes parcels under \\$300K total or \\$50K "
             "improvements.\nBoundaries: Census TIGER 2012 school districts and places, via the L.A. "
             "Times. Differences across the line are not a measured effect of the schools. "
             "See README.",
             fontsize=8, color=COLORS["muted"], linespacing=1.4)
    out = os.path.join(ROOT, "maps", f"{pair}.png")
    fig.savefig(out, facecolor="white", bbox_inches="tight", metadata={"Software": None})
    plt.close(fig)
    print(pair, "->", out)


if __name__ == "__main__":
    for pair, cfg in PAIRS.items():
        draw(pair, cfg)
