# October 11, 2026 King County builder view

## October 11 Buchan restoration

- Restored all 2,975 historical Buchan parcel associations from the last release
  that included them. Six parcels also match an existing builder, so the merged
  release contains 16,025 distinct parcels across nine builder collections.
- Kept Buchan as one collection. The John Buchan / William Buchan attribution
  remains unreviewed; no individual company attribution was introduced.
- Preserved Buchan's original recording evidence, review flags, and parcel
  locations while retaining the other eight builders' current records.
- Added a data-grounded Buchan research page and updated coverage wording,
  research-guide links, and the sitemap.

## October 9 launch preparation

- Added a static King County builder-research guide plus Burnstead and Quadrant
  collection pages generated from this release. No property inventory changed.
- Added canonical search routes, a sitemap, robots file, Open Graph metadata,
  and a 1200 × 630 sharing card.
- Added city entry points and restored the previously published project email
  as the primary correction route. Mail delivery has not been independently tested.
- Prepared allowlisted launch attribution and successful copy-link events.
  Analytics remains disabled until the existing GA property is accessible and
  enhanced-measurement settings and real transport are verified.
- Added the Google-issued HTML verification file for the existing owner's
  Search Console setup. Keep it to retain ownership verification.

Validation: 19 Node tests and 8 Python data/geometry checks pass. Generated
page paths, coverage counts, metadata, JSON-LD, and sitemap are also checked.

This release includes 16,025 distinct mapped homes across nine partial builder
views:

| Builder | Homes |
| --- | ---: |
| Buchan | 2,975 |
| Burnstead | 2,584 |
| Murray Franklyn | 204 |
| CamWest | 1,667 |
| Quadrant Homes | 5,569 |
| Conner Homes | 1,634 |
| Toll Brothers | 488 |
| MainVue Homes | 981 |
| Lennar | 53 |

Counts overlap when one parcel has qualifying matches for multiple builders.
The interface, search index, and map use the same 16,025-home inventory.

## Changes

- Reframed the site as a clear view of home builders across King County.
- Simplified public terminology from collections and research language to
  builders, homes, county data, and data notes.
- Shows all nine available builders, with Buchan's historical categories combined
  into one collection.
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

The independent source check for the eight expanded builders covers 13,725 public
company/recording/PIN references, 13,056 county locations, and 831 primary-address
recoveries. Buchan restoration checks compare the merged release with its
original immutable payloads. The exporter must reproduce the released index,
detail, and geometry hashes.

## Publishing and rollback

Repository: https://github.com/whobuiltmyhome/whobuiltmyhome-site

Publish the manifest and all three immutable payloads from the same tested
commit. Verify the Pages deployment and live asset hashes. A normal Git revert
restores the previous release if needed; removed files remain recoverable from
repository history.
