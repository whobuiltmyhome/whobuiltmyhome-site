# September 20, 2026 company-connection expansion

The release includes 2,584 Burnstead, 1,667 CamWest, 1,634 Conner, 53 Lennar,
981 MainVue, 204 Murray Franklyn, 5,569 Quadrant, and 488 Toll Brothers
company-associated addresses alongside the original 2,975 Buchan addresses:
**16,025 distinct mapped properties**.
Five PINs have both Buchan and Burnstead company connections. Search,
collection filters and the map use the same complete inventory.

Burnstead covers three documented current LLCs plus historical Burnstead-named construction and homes sellers in 1976–2026 county transactions. Quadrant
covers five corporate-name forms through 2020. These are partial company-sale
collections; no original builder is certified. Burnstead historical names do not establish legal succession, and
unreviewed variants, successor brands and other builder collections await review.
The two Buchan attributions remain unresolved.

## Changes

- Reproducible frozen-county-source importer with exact entity/date, instrument,
  residential-cohort, address and geometry gates; rejected candidates are counted.
- MainVue and Murray Franklyn can recover a missing or stale Residential Building
  address only from one complete county-designated primary GIS address for the PIN.
- Separate evidence per company connection, preserving every original Buchan
  address and its evidence. The review filter applies to any connection.
- Available collection cards show counts, scope and direct search links. Other
  brands stay visibly pending.
- Existing static hosting, vendored map libraries and tile behavior continue.
  GA4 remains disabled pending the previously required account-settings review.

## Verification

All **29 tests pass**: 12 Node analytics/search/map tests and 17 Python baseline,
expansion and geometry tests. The DOM test runs the real app and vendored map
libraries, checking both new collection filters, map counts, company evidence,
map failure/retry, clusters, pagination, empty results and the original Buchan
search behavior. Tests also reject ambiguous aliases and unsupported dates,
instruments and recordings, and enforce public-field allowlists.

A separate finished-artifact/source comparison checks every **13,725 new
parcel/company/recording reference** and every **13,056 new county location**,
with zero mismatches. The cached rebuild reproduces the same immutable data
hashes. Source hashes, retrieval dates and terminal hold counts are published.

```sh
npm test
python -m unittest discover -s tests -p 'data*.py'
python scripts/check-expanded-sources.py \
  --sales /path/to/Real_Property_Sales.zip \
  --cache-dir /path/outside/repository/expanded-source-cache
```

DOM checks establish behavior, not mobile rendering or real-device performance.
The existing map was previously reviewed by the user; browser automation was
unavailable. Evidence is an approximately 15.5 MB uncompressed lazy-loaded JSON
file; slower connections may wait when opening the first record.

## Publishing and rollback

Repository: https://github.com/whobuiltmyhome/whobuiltmyhome-site

Publish all assets and their manifest together. Verify the remote tree matches
the tested local tree, respect required checks, merge using the expected PR head,
and wait for successful Pages deployment of that exact merge commit. Then verify
live asset hashes. GitHub PR and deployment history are authoritative for status.

`CNAME` remains `whobuiltmyhome.com`. Retain prior hashed payloads for cached
readers. The preceding published commit is `f3bb724`; reverting this expansion
restores the prior 11,219-property release without recomputing evidence.
