# Home values on each side of a school district line

Three Los Angeles County comparisons of recently sold single-family homes
within a short distance of a school district boundary. Every record comes
directly from the LA County Assessor's public parcel service (pulled
October 11, 2026), and every home can be looked up by its Assessor ID.

| Comparison | Strip width | Homes (A / B) | Median A | Median B | Gap in medians (95% range) | Gap at equal home and lot size (95% range) |
|---|---|---|---|---|---|---|
| South Pasadena Unified vs Los Angeles Unified | 800 ft | 52 / 69 | $1,728,450 | $1,153,620 | **+50%** (+37% to +88%) | **+36%** (+23% to +51%) |
| Palos Verdes Peninsula Unified vs Los Angeles Unified, Eastview excluded | 800 ft | 77 / 92 | $1,759,500 | $1,222,010 | **+44%** (+30% to +61%) | **+22%** (+2% to +45%) |
| La Cañada Unified vs Glendale Unified ("Sagebrush"), both inside La Cañada Flintridge | 1,300 ft | 39 / 45 | $2,598,918 | $2,044,620 | +27% (−5% to +65%) | +13% (−2% to +32%) |

Every width from 500 to 1,300 ft, and the variants below, are in
`results/summary.csv`.

**What these numbers show:** recently sold homes on the South Pasadena and
Palos Verdes sides of the line are assessed well above comparable homes a few
blocks away in LAUSD, and the gap remains after accounting for home and lot
size. **What they do not show:** how much of that gap is caused by the
schools. The lines also separate cities, and nothing here adjusts for views,
age, condition or street. See "Limitations".

**La Cañada is not a clear result.** Its 95% ranges include zero at every
strip width, and the Sagebrush transfer (below) affects how it can be read.

### Palos Verdes and Eastview

Eastview is the part of Rancho Palos Verdes inside LAUSD. State law makes it
an optional attendance area: its students may choose Palos Verdes Peninsula
Unified instead ([PVPUSD school locator](https://pvpusd.net/apps/pages/School-Locator)).
Its families are not really on the far side of the school line, so the
headline row leaves them out. With them included (77 / 171 homes), the gap is
+36% in medians (+24% to +48%) and +15% at equal home and lot size (+1% to +32%).

Eastview also allows a rough check. Compared at equal home and lot size, the
PVPUSD side is +9% above Eastview homes (−4% to +23%) but +22% above the rest
of the LAUSD side. That fits the idea that access to PVPUSD is part of the gap,
but the two ranges overlap, so it is suggestive only.

### La Cañada and the Sagebrush transfer

The Glendale Unified side of this comparison is Sagebrush, the part of La
Cañada Flintridge served by Glendale Unified. Its transfer to La Cañada Unified
has been underway throughout the period these homes sold:

- October 2, 2019: the LA County Committee on School District Organization
  approved the transfer petition.
- January 18, 2024: the State Board of Education denied Glendale Unified's
  appeals and limited the vote to Sagebrush residents.
- November 5, 2024: Sagebrush voters approved the transfer (Measure X).
- July 1, 2026: the scheduled effective date. This was not independently
  confirmed here.

All homes in this sample were reassessed in 2023–2026, after the county
approval, and most after the State Board decision. Buyers in Sagebrush may
already have paid for an expected move to La Cañada Unified, which would
shrink the gap. If the transfer has taken effect, the 2012 line used here no
longer separates the two districts. For both reasons, the La Cañada numbers
should not be read as the value of being inside La Cañada Unified.

## What's here

```
boundaries/        District and city outlines (GeoJSON, WGS84)
data/county/       Parcel records as returned by the county, and fetch_info.json (when and how)
data/parcels/      One row per single-family parcel: value, size, side of line, distance, included or not
results/           summary.csv: medians, gaps and 95% ranges by comparison and strip width
maps/              <pair>.png, drawn by make_maps.py
scripts/           common.py, fetch_parcels.py, analyze.py, make_maps.py
```

## Method

1. **Boundaries.** Unified school district outlines and the La Cañada
   Flintridge city limit from the US Census TIGER 2012 files, as archived by
   the Los Angeles Times at https://github.com/datadesk/boundaries.latimes.com.
   District borders rarely move, but these are 2012 lines, not current ones.
2. **Strip.** The shared line between the two districts, buffered by the strip
   width on each side (EPSG:2229, feet). For La Cañada only the line between
   La Cañada Unified and Sagebrush is used, and only homes inside the city are
   counted, so both sides share the same city government. The 1,300 ft strip
   covers about two-thirds of Sagebrush.
3. **Parcels.** LA County Assessor parcel layer, public service at
   `https://public.gis.lacounty.gov/public/rest/services/LACounty_Cache/LACounty_Parcel/MapServer/0`.
   Kept:
   - single-family use codes 0100, 0101, 0103, 0104 (the county labels every
     01xx code "Single"; condominiums, 010C, and the other variants are left
     out);
   - land base year 2023 or later. Under Proposition 13 a parcel is reassessed
     to market value mainly when it changes ownership, so a recent base year
     usually means a recent sale, and the assessed value is close to the
     purchase price;
   - total assessed value (land + improvements) of at least $300,000 and
     improvements of at least $50,000, to drop vacant lots and partial transfers.
4. **Side and distance.** Each parcel's centroid is placed in a district and
   its distance to the shared line measured. Sides are then checked against the
   county's tax-rate areas. A tax-rate area is one combination of taxing
   agencies, so it lies in a single school district. Where one held homes on
   both sides of the Census line, the line is slightly off there, and those
   homes were moved to the side holding most of that area's homes. This moved 2
   homes in La Cañada and none elsewhere.
5. **Statistics.**
   - *Gap in medians:* the difference between the two sides' median assessed
     values. Its 95% range comes from resampling homes within each side 5,000
     times.
   - *Gap at equal home and lot size:* from a regression of log(assessed value)
     on side, log(home square feet) and log(lot square feet), with a 95% range
     from heteroskedasticity-robust standard errors. `summary.csv` also gives
     the version adjusted for home size only.

## Checks

- **Earlier version.** The first version of this repository (commit `0436bbd`)
  was built from query output copied as text. All 444 homes in it are in the
  county's records with identical values. The direct pull adds 9 homes from
  small areas the earlier queries missed. With the earlier method, the
  published gaps move by under one percentage point.
- **Side of the line.** The tax-rate-area check above. In South Pasadena,
  every home's side also matches its city on the county roll.
- **Timing.** Homes on each side were reassessed in roughly similar
  proportions in each year from 2023 to 2026, so a market shift during that
  period does not favor one side.
- **Individual homes.** Every row in `data/parcels/*.csv` has an AIN (Assessor
  ID number). Look it up at https://portal.assessor.lacounty.gov/ to see the
  assessed values and base year. Checking a random handful on each side is the
  quickest way to test the data.

## Reproduce

```
pip install -r requirements.txt
python scripts/analyze.py          # data/county -> data/parcels and results/summary.csv
python scripts/make_maps.py        # maps/<pair>.png

python scripts/fetch_parcels.py    # optional: pull data/county again from the county
```

The county updates the roll as homes sell, so a new pull returns a slightly
different set of homes. The committed `data/county/` files are the ones the
results above use.

## Limitations

- **Assessed value is not sale price.** It is close to the purchase price after
  a sale, but base years can also reset for new construction or non-sale
  transfers, and values carry up to 2% annual increases.
- **Only home and lot size are adjusted for.** Age, condition, quality, views
  (important on the Palos Verdes Peninsula), slope and street are not.
- **District lines are also city lines in South Pasadena.** The gap there
  mixes schools with taxes, city services, and everything else that differs
  between South Pasadena and Los Angeles. In Palos Verdes, the PVPUSD side is
  Rancho Palos Verdes and Rolling Hills Estates; the LAUSD side outside
  Eastview is Lomita, the Los Angeles neighborhoods of Harbor City and San
  Pedro, and a few homes in Rolling Hills Estates. La Cañada avoids this, but has the problems described above.
- **Small samples** (39–92 homes per side in the headline rows, as few as 16
  in the narrowest La Cañada strip), and the strip widths and dollar cutoffs
  were the author's choices. `results/summary.csv` shows how the result
  moves with width.

The research literature finds that the part of the gap attributable to school
quality alone is much smaller than raw comparisons like these, e.g. Black
(1999, QJE) and Bayer, Ferreira and McMillan (2007, JPE).

## License and data

Parcel data: Los Angeles County Assessor, public record. Boundaries: US Census
Bureau TIGER/Line (public domain). Code: free to use and modify.
