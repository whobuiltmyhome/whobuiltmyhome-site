# September 18, 2026 company-connection expansion

The release includes 2,584 Burnstead-associated, 96 Murray Franklyn-associated,
and 5,569 Quadrant-associated addresses alongside the original 2,975 Buchan
addresses: **11,219 distinct mapped properties**.
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
- Separate evidence per company connection, preserving every original Buchan
  address and its evidence. The review filter applies to any connection.
- Available collection cards show counts, scope and direct search links. Other
  brands stay visibly pending.
- Existing static hosting, vendored map libraries and tile behavior continue.
  GA4 remains disabled pending the previously required account-settings review.

## Verification

All **28 tests pass**: 12 Node analytics/search/map tests and 16 Python baseline,
expansion and geometry tests. The DOM test runs the real app and vendored map
libraries, checking both new collection filters, map counts, company evidence,
map failure/retry, clusters, pagination, empty results and the original Buchan
search behavior. Tests also reject ambiguous aliases and unsupported dates,
instruments and recordings, and enforce public-field allowlists.

A separate finished-artifact/source comparison checks every **5,845 new
parcel/company/recording reference** and every **5,742 new county location**,
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
unavailable. Evidence is an approximately 8.4 MB uncompressed lazy-loaded JSON
file; slower connections may wait when opening the first record.

## Publishing and rollback

Repository: https://github.com/whobuiltmyhome/whobuiltmyhome-site

Publish all assets and their manifest together. Verify the remote tree matches
the tested local tree, respect required checks, merge using the expected PR head,
and wait for successful Pages deployment of that exact merge commit. Then verify
live asset hashes. GitHub PR and deployment history are authoritative for status.

`CNAME` remains `whobuiltmyhome.com`. Retain prior hashed payloads for cached
readers. The preceding published commit is
`8d068a1cb158da0643a2b449cddb7171a0722d67`; reverting this expansion restores the
2,975-property Buchan search and map without recomputing evidence.
