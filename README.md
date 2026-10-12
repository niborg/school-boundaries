# Home values on each side of a school district line

Three Los Angeles County comparisons of single-family home values within a
short distance of a school district boundary:

| Comparison | Strip width | Side A median (n) | Side B median (n) | Gap |
|---|---|---|---|---|
| South Pasadena Unified vs Los Angeles Unified | 800 ft | $1,734,000 (51) | $1,154,000 (65) | +$580,000 (+50%) |
| Palos Verdes Peninsula Unified vs Los Angeles Unified | 800 ft | $1,759,500 (77) | $1,300,000 (167) | +$459,500 (+35%) |
| La Cañada Unified vs Glendale Unified (inside La Cañada Flintridge only) | 1,300 ft | $2,598,918 (37) | $2,044,620 (47) | +$554,298 (+27%) |

All widths: `results/summary.csv`. The South Pasadena and Palos Verdes gaps are
stable from 500 to 800 ft. **The La Cañada gap is not**: within 500–600 ft of
the line the two medians are about equal, and the samples are small.

These numbers show that home values differ sharply across these lines. They do
**not** isolate the effect of the schools. See "Limitations".

## What's here

```
boundaries/        District and city outlines (GeoJSON, WGS84)
data/transcribed/  Parcel records as originally retrieved (see "How the published numbers were produced")
data/parcels/      One row per single-family parcel: value, side of line, distance to line, included or not
results/           summary.csv: medians by comparison and strip width
maps/              *_boundary.png are the images originally shared; <pair>.png are redrawn by make_maps.py
scripts/           common.py, analyze.py, make_maps.py, fetch_parcels.py
```

## Method

1. **Boundaries.** Unified school district outlines and the La Cañada
   Flintridge city limit from the US Census TIGER 2012 files, as archived by
   the Los Angeles Times at https://github.com/datadesk/boundaries.latimes.com.
   District borders rarely move, but these are 2012 lines, not current ones.
2. **Strip.** The shared line between the two districts, buffered by the strip
   width on each side (EPSG:2229, feet). For La Cañada only the stretch of line
   inside the city is used, and only homes inside the city are counted, so both
   sides share the same city government; the line there separates La Cañada
   Unified from the part of the city served by Glendale Unified.
3. **Parcels.** LA County Assessor parcel layer, public service at
   `https://public.gis.lacounty.gov/public/rest/services/LACounty_Cache/LACounty_Parcel/MapServer/0`.
   Kept:
   - single-family use codes 0100, 0101, 0103, 0104;
   - land base year 2023 or later (`Roll_LandBaseYear > '2022'`). Under
     Proposition 13 a parcel is reassessed to market value mainly when it
     changes ownership, so a recent base year usually means a recent sale and
     the assessed value is close to the purchase price;
   - total assessed value (land + improvements) of at least $300,000 and
     improvements of at least $50,000, to drop vacant lots and partial transfers.
4. **Side and distance.** Each parcel's centroid is placed in a district and
   its distance to the shared line measured.
5. **Statistic.** Median total assessed value on each side.

## How the published numbers were produced (read this)

The analysis environment could not download from the county server directly.
The parcel queries were run through a web-reading tool that returned the
results as text, which was then saved to `data/transcribed/`:

- `a*.csv` = `AIN, latitude, longitude, Roll_LandValue` for every parcel with a
  2023+ base year in each query box;
- `b*.csv` = `AIN, Roll_ImpValue, UseCode`, where **the reading tool itself
  filtered to the single-family codes**.

So two steps were not under direct control: the copying of the numbers, and
the single-family filter. Counts were spot-checked but not every row was
independently verified. In Palos Verdes, query boxes over open water were
skipped, and very small slivers of the strip were not queried in any pair.

**To remove this weakness, run `fetch_parcels.py`**, which pulls the same
records straight from the county with no intermediary and also adds square
footage, bedrooms, and year built. It was written but could not be run by its
author for the same network reason, so it may need minor fixes.

## Reproduce

```
pip install -r requirements.txt
python scripts/analyze.py          # rebuild data/parcels and results/summary.csv from data/transcribed
python scripts/make_maps.py        # redraw maps/<pair>.png

python scripts/fetch_parcels.py --width 1300   # direct from the county (recommended)
python scripts/analyze.py --source fetched     # results/summary_fetched.csv
```

## Check individual homes

Every row in `data/parcels/*.csv` has an AIN (Assessor ID number). Look it up at
https://portal.assessor.lacounty.gov/ to see the assessed values and base year.
Checking a random handful on each side is the quickest way to test the data.

## Limitations

- **Assessed value is not sale price.** It is close to the purchase price after
  a sale, but base years can also reset for new construction or non-sale
  transfers, and values carry up to 2% annual increases.
- **No adjustment for house or lot size, age, or condition.** Larger homes on
  one side would produce a gap by themselves. `fetch_parcels.py` adds
  square footage so this can be checked.
- **District lines are also city lines** for South Pasadena and Palos Verdes,
  so the gap mixes schools with taxes, city services, and everything else that
  differs between the cities. La Cañada avoids this, and its gap is the least
  certain of the three.
- **Some families in the Eastview area of Rancho Palos Verdes can choose either
  district.** The Census line was used as drawn; this was not checked.
- **Small samples** (16–167 homes per side), and the strip widths and dollar
  cutoffs were the author's choices. `results/summary.csv` shows how the result
  moves with width.

The research literature finds that the part of the gap attributable to school
quality alone is much smaller than raw comparisons like these, e.g. Black
(1999, QJE) and Bayer, Ferreira and McMillan (2007, JPE).

## License and data

Parcel data: Los Angeles County Assessor, public record. Boundaries: US Census
Bureau TIGER/Line (public domain). Code: free to use and modify.
