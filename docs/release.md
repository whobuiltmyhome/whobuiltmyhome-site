# September 20, 2026 King County builder view

This release includes 13,056 distinct mapped homes across eight partial builder
views:

| Builder | Homes |
| --- | ---: |
| Burnstead | 2,584 |
| Murray Franklyn | 204 |
| CamWest | 1,667 |
| Quadrant Homes | 5,569 |
| Conner Homes | 1,634 |
| Toll Brothers | 488 |
| MainVue Homes | 981 |
| Lennar | 53 |

Counts overlap when one parcel has qualifying matches for multiple builders.
The interface, search index, and map use the same 13,056-home inventory.

## Changes

- Reframed the site as a clear view of home builders across King County.
- Simplified public terminology from collections and research language to
  builders, homes, county data, and data notes.
- Shows only the eight active builders and removes retired records and payloads
  from the current site tree.
- Opens the official King County eReal Property details table from each home;
  the parcel-map button is no longer shown.
- Treats routine sale-association and primary-address provenance separately from
  additional review notes in cards and filters.
- Keeps the strict company/date, instrument, residential-cohort, address, and
  geometry gates. Held candidates remain counted in the audit.

## Verification

Run the complete local checks before publication:

```sh
npm test
python -m unittest discover -s tests -p 'data*.py'
python scripts/check-expanded-sources.py \
  --sales /path/to/Real_Property_Sales.zip \
  --cache-dir /path/outside/repository/gis-cache
```

The independent source check covers 13,725 public company/recording/PIN
references, all 13,056 county locations, and 831 primary-address recoveries.
The cached exporter must reproduce the same index, detail, and geometry hashes.

## Publishing and rollback

Repository: https://github.com/whobuiltmyhome/whobuiltmyhome-site

Publish the manifest and all three immutable payloads from the same tested
commit. Verify the Pages deployment and live asset hashes. A normal Git revert
restores the previous release if needed; removed files remain recoverable from
repository history.
